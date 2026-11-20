#!/usr/bin/env python3
"""
vocal_match.py - estimate a full vocal chain preset from a raw vocal and a mixed vocal.

Built for humans and AI agents. Results are JSON on stdout; progress goes to
stderr. Exit code 0 = success, 1 = failure ({"error": ...} on stdout).

Chain modelled (in order):
  hpf -> lpf -> gate -> de-esser -> saturation -> compressor -> EQ (8 band)
  -> modulation (chorus/flanger/phaser/vibrato/tremolo)
  -> delay + reverb (parallel) -> output gain -> limiter
Analysis only (not rendered in previews): pitch correction / transposition,
key guess, stereo width / Haas delay.

How it works
  1. Statistical first guesses (spectral EQ match, loudness curve, impulse
     response for delay/reverb, sibilance, harmonics, f0 tracks, stereo).
  2. If raw and mixed are the same take, an analysis-by-synthesis loop renders
     the chain, compares its multi-resolution spectrogram with the mix, tests
     each optional effect on/off and tunes parameters. An effect is kept only
     if it lowers the error; its confidence comes from that improvement.

Known limits (synthetic-vocal tests; real vocals are harder)
  - Flanger and constant short delays (doubler/Haas) are detected; multi-voice
    chorus, phaser, vibrato and tremolo are rendered but not reliably detected.
  - Compressor and saturator overlap (both squash peaks); reverb RT60/level are
    approximate; echoes or chorus on the mix can confuse the f0 tracker.
  - Pitch-correction retune speed is not estimated; a constant offset left by
    partial correction looks like a different tuning reference.
  - Different takes: only EQ, compressor and strongly evidenced de-esser /
    saturation are estimated; nothing time-aligned is claimed.

Commands
  analyze RAW MIXED [-o preset.json] [--render preview.wav] [--skip a,b]
          [--quality fast|normal|high|off] [--bpm 120]
  apply   RAW PRESET OUT [--target MIXED]
  export  PRESET [--format sheet|json]   plugin-style settings cheat sheet
  schema  function-calling tool definition for agent frameworks

Skippable effects: deesser, saturation, delay, reverb, gate, modulation,
limiter, hpf, lpf, pitch, stereo.

Python use
  from vocal_match import analyze, render
  preset = analyze(raw, mixed, sr)      # numpy mono arrays, same sample rate
  audio  = render(raw, sr, preset)

Requires: numpy, scipy, soundfile (soundfile optional for 16-bit WAV only).
"""
import argparse, copy, json, math, sys, time
from collections import OrderedDict
import numpy as np
from scipy import signal

EQ_BANDS = [  # name, biquad type, centre Hz, Q
    ("low_shelf", "lowshelf", 100, 0.7),
    ("low", "peaking", 220, 1.0),
    ("low_mid", "peaking", 450, 1.0),
    ("mid", "peaking", 1000, 1.0),
    ("upper_mid", "peaking", 2200, 1.0),
    ("presence", "peaking", 4200, 1.0),
    ("sibilance", "peaking", 7000, 1.0),
    ("air", "highshelf", 11000, 0.7),
]
MAX_SECONDS = 120
EFFECTS = ("deesser", "saturation", "delay", "reverb", "gate", "modulation",
           "limiter", "hpf", "lpf", "pitch", "stereo")
OFF = {"enabled": False}


def log(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------- audio io
def load(path):
    """Returns (mono, sr, channels[n, ch])."""
    try:
        import soundfile as sf
        x, sr = sf.read(path, always_2d=True)
    except ImportError:
        from scipy.io import wavfile
        sr, x = wavfile.read(path)
        if x.dtype.kind in "iu":
            x = x.astype(np.float64) / np.iinfo(x.dtype).max
        x = x.astype(np.float64)
        x = x[:, None] if x.ndim == 1 else x
    if x.size == 0 or not np.all(np.isfinite(x)):
        raise ValueError("audio is empty or contains NaN/Inf")
    if np.max(np.abs(x)) < 1e-8:
        raise ValueError("audio is silent; a vocal match requires audible input")
    return x.mean(axis=1), int(sr), x


def safe_output(x, sr, ceiling_db=-1.0):
    """Global true-peak-aware safety attenuation, no audible squashing.

    Does not increase gain on quiet signals and avoids a sample-clipping limiter.
    Resampled 4x to conservatively estimate inter-sample overshoots.
    """
    x = np.asarray(x,dtype=np.float64)
    if not np.all(np.isfinite(x)):
        raise ValueError("invalid NaN/Inf in audio")
    if x.size == 0: return x.copy(), {"attenuation_db":0.0,"true_peak_dbfs":-120.0}
    true_peak = float(np.max(np.abs(signal.resample_poly(x,4,1,axis=0))))
    allowed = 10**(ceiling_db/20)
    scale = min(1.0, allowed/(true_peak+1e-12))
    return x*scale, {"attenuation_db":round(20*math.log10(scale),2),
                      "unprotected_true_peak_dbfs":round(20*math.log10(true_peak+1e-12),2),
                      "ceiling_dbtp":float(ceiling_db)}


def save(path, x, sr):
    x, safety = safe_output(x,sr)
    log("true-peak safety: " + json.dumps(safety))
    try:
        import soundfile as sf
        sf.write(path, x, sr, subtype="PCM_24")
    except ImportError:
        from scipy.io import wavfile
        wavfile.write(path, sr, (x * 32767).astype(np.int16))


def match_rate(x, sr_from, sr_to):
    if sr_from == sr_to:
        return x
    g = math.gcd(sr_from, sr_to)
    return signal.resample_poly(x, sr_to // g, sr_from // g, axis=0)


# ---------------------------------------------------------------- spectra
def band_centres(sr, per_oct=3, f_min=40.0):
    f, out = f_min, []
    while f <= min(16000, sr * 0.45):
        out.append(f)
        f *= 2 ** (1 / per_oct)
    return np.array(out)


def _bands_from_power(freqs, p, centres):
    half = (centres[1] / centres[0]) ** 0.5
    out = []
    for fc in centres:
        m = (freqs >= fc / half) & (freqs < fc * half)
        out.append(10 * np.log10(p[m].mean() + 1e-20) if m.any() else -200.0)
    return np.array(out)


def band_spectrum_db(x, sr, centres):
    """Long-term average spectrum per band, loud frames only (gate -30 dB)."""
    freqs, _, Z = signal.stft(x, sr, nperseg=4096, noverlap=2048)
    p = np.abs(Z) ** 2
    energy = p.sum(axis=0)
    p = p[:, energy > energy.max() * 1e-3].mean(axis=1)
    return _bands_from_power(freqs, p, centres)


def levels_db(x, sr, peak=False):
    """50 ms RMS (or peak) levels in dBFS, ignoring silence (>40 dB below max)."""
    w = int(sr * 0.05)
    k = len(x) // w
    fr = x[: k * w].reshape(k, w)
    v = np.abs(fr).max(axis=1) if peak else np.sqrt((fr ** 2).mean(axis=1))
    db = 20 * np.log10(v + 1e-9)
    return db[db > db.max() - 40]


def spectral_distance(a_db, b_db, centres):
    """Mean abs dB difference after matching overall level (250-4000 Hz)."""
    ref = (centres >= 250) & (centres <= 4000)
    d = (a_db - a_db[ref].mean()) - (b_db - b_db[ref].mean())
    return float(np.abs(d).mean())


def _interp(centres, curve):
    lx = np.log2(centres)
    return lambda f: float(np.interp(np.log2(f), lx, curve))


# ---------------------------------------------------------------- dry-chain fits
def fit_eq(src_db, mix_db, c):
    """High/low-pass + 8-band EQ that moves src's average spectrum onto mix's."""
    diff = mix_db - src_db
    ref = (c >= 250) & (c <= 4000)
    diff = diff - diff[ref].mean()
    empty = src_db < src_db.max() - 45          # bands with ~no source energy: never boost
    diff[empty] = np.minimum(diff[empty], 0)
    diff = np.convolve(np.pad(diff, 1, mode="edge"), np.ones(3) / 3, mode="valid")
    at = _interp(c, diff)
    hpf = {"enabled": False, "freq_hz": 0}
    if at(60) < -6:
        for f in c[(c >= 40) & (c <= 250)]:
            if at(f) > -3:
                hpf = {"enabled": True, "freq_hz": int(round(f))}
                break
    lpf = {"enabled": False, "freq_hz": 0}
    top = min(12000, c[-1])
    if at(top) < -8:
        for f in c[(c >= 3000) & (c <= top)]:
            if at(f) <= -3:
                lpf = {"enabled": True, "freq_hz": int(round(f))}
                break
    eq = []
    for name, typ, f, q in EQ_BANDS:
        if f >= c[-1] * 1.3 and typ == "peaking":
            continue
        g = np.mean([at(min(f * 2 ** s, c[-1])) for s in (-1 / 3, 0, 1 / 3)])
        g = float(np.clip(round(g * 2) / 2, -12, 12))
        eq.append({"name": name, "type": typ, "freq_hz": f, "gain_db": g, "q": q})
    return hpf, lpf, eq


def fit_compressor(raw_db, mix_db):
    """Grid-search threshold/ratio so a static curve reproduces the mixed
    file's loudness spread (percentile gaps, level-independent)."""
    def gaps(d):
        p = np.percentile(d, [20, 60, 95])
        return np.array([p[1] - p[0], p[2] - p[1]])
    target = gaps(mix_db)
    best = (1e9, -20.0, 1.0)
    # Avoid an extreme low threshold that squashes virtually every phrase.
    # These are sane *initial* search bounds, not claims about the source plug-in.
    floor = float(np.percentile(raw_db, 30))
    for thr in np.arange(max(-36, floor - 10), -5, 1.0):
        for r in np.arange(1.0, 7.01, 0.5):
            out = np.where(raw_db > thr, thr + (raw_db - thr) / r, raw_db)
            err = np.abs(gaps(out) - target).sum() + 0.02 * r
            if err < best[0]:
                best = (err, float(thr), float(r))
    return best[1], best[2]


def fit_compressor_paired(raw, mixed, sr):
    """Same-take case: read the compression curve off a frame-by-frame scatter
    of raw vs mixed peak level. Returns None for different takes."""
    r, m = _shift(raw, mixed, _lag(raw, mixed, sr))
    w = int(sr * 0.05)
    k = len(r) // w
    if k < 40:
        return None
    pk = lambda x: 20 * np.log10(np.abs(x[: k * w].reshape(k, w)).max(axis=1) + 1e-9)
    lr, lm = pk(r), pk(m)
    g = lr > lr.max() - 40
    lr, lm = lr[g], lm[g]
    if len(lr) < 40 or np.corrcoef(lr, lm)[0, 1] < 0.5:
        return None
    ib = np.digitize(lr, np.arange(np.floor(lr.min()), lr.max() + 2, 2.0))
    xs, ys, ws = [], [], []
    for b in np.unique(ib):
        sel = ib == b
        if sel.sum() >= 5:
            xs.append(lr[sel].mean()); ys.append(np.median(lm[sel])); ws.append(sel.sum())
    xs, ys, ws = (np.array(a) for a in (xs, ys, ws))
    keep = xs >= np.percentile(lr, 30)
    if keep.sum() < 4:
        return None
    xs, ys, ws = xs[keep], ys[keep], ws[keep]
    best = (1e18, 0.0, 1.0)
    for thr in np.arange(max(-36, np.percentile(lr, 20)), lr.max(), 1.0):
        for R in np.arange(1.0, 7.01, 0.5):
            shape = np.where(xs > thr, thr + (xs - thr) / R, xs)
            off = np.average(ys - shape, weights=ws)
            err = np.average((ys - shape - off) ** 2, weights=ws) + 0.002 * R
            if err < best[0]:
                best = (err, float(thr), float(R))
    return best[1], best[2]


def fit_deesser(raw, mixed, sr, base, force=False):
    """Detect sibilance that is tamed more in the mix than the static chain
    explains. force=True returns a starting-point candidate regardless."""
    r, m = raw[: sr * 60], mixed[: sr * 60]
    ren = render(r, sr, base)
    c = band_centres(sr)
    sel = (c >= 4000) & (c <= 10000)
    if not sel.any():
        return dict(OFF)
    fc = float(c[sel][np.argmax(band_spectrum_db(ren, sr, c)[sel])])
    bp = biquad("bandpass", fc, 0, 1.5, sr)
    lr = levels_db(signal.sosfilt(bp, ren), sr)
    lm = levels_db(signal.sosfilt(bp, m), sr)
    spread = lambda d: np.percentile(d, 95) - np.percentile(d, 50)
    sr_, sm_ = spread(lr), spread(lm)
    red = sr_ - sm_
    if red < 1.5 and not force:
        return dict(OFF)
    t = np.percentile(lr, 70) - np.percentile(lr, 50)
    ratio = (sr_ - t) / (sm_ - t) if sm_ - t > 0.3 else 8.0
    ratio = float(np.clip(round(ratio * 2) / 2, 1.5, 8)) if red >= 1.5 else 3.0
    thr = float(np.percentile(levels_db(signal.sosfilt(bp, r), sr), 70))
    return {"enabled": True, "freq_hz": int(fc), "q": 1.5, "threshold_db": round(thr, 1),
            "ratio": ratio, "attack_ms": 1, "release_ms": 40,
            "max_reduction_db": round(max(red, 0), 1), "confidence": round(min(1, max(red, 0) / 6), 2)}


def fit_saturation(raw, mixed, sr, comp, deess):
    """Pick the tanh drive that lets the EQ best match the mix's fine
    (1/6-octave) spectrum, since harmonics add detail EQ cannot imitate."""
    seg, mseg = raw[: sr * 30], mixed[: sr * 30]
    c3, c6 = band_centres(sr), band_centres(sr, 6, 150.0)
    mix3, mix6 = band_spectrum_db(mseg, sr, c3), band_spectrum_db(mseg, sr, c6)
    dist = {}
    for d in (0, 1.2, 1.5, 2.0, 3.0):
        base = {"deesser": deess, "compressor": comp,
                "saturation": {"enabled": d > 0, "drive": d}}
        y = render(seg, sr, base)
        hp, lp, eq = fit_eq(band_spectrum_db(y, sr, c3), mix3, c3)
        z = render(y, sr, {"hpf": hp, "eq": eq})
        dist[d] = spectral_distance(band_spectrum_db(z, sr, c6), mix6, c6)
    best = min(dist, key=dist.get)
    gain = dist[0] - dist[best]
    if best == 0 or gain < 0.45:
        return dict(OFF)
    return {"enabled": True, "type": "tanh", "drive": float(best),
            "amount": "light" if best <= 2 else "medium" if best <= 3 else "heavy",
            "confidence": round(min(1, gain / 1.0), 2)}


# ---------------------------------------------------------------- stage functions
def biquad(typ, f, gain_db, q, sr):
    """RBJ audio-EQ-cookbook biquad as a second-order section."""
    A = 10 ** (gain_db / 40)
    w = 2 * math.pi * f / sr
    cw, sw = math.cos(w), math.sin(w)
    al = sw / (2 * q)
    if typ == "peaking":
        b = [1 + al * A, -2 * cw, 1 - al * A]
        a = [1 + al / A, -2 * cw, 1 - al / A]
    elif typ == "highpass":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + al, -2 * cw, 1 - al]
    elif typ == "lowpass":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + al, -2 * cw, 1 - al]
    elif typ == "bandpass":
        b = [al, 0, -al]
        a = [1 + al, -2 * cw, 1 - al]
    else:
        s = 2 * math.sqrt(A) * al
        if typ == "lowshelf":
            b = [A * ((A + 1) - (A - 1) * cw + s), 2 * A * ((A - 1) - (A + 1) * cw),
                 A * ((A + 1) - (A - 1) * cw - s)]
            a = [(A + 1) + (A - 1) * cw + s, -2 * ((A - 1) + (A + 1) * cw),
                 (A + 1) + (A - 1) * cw - s]
        else:  # highshelf
            b = [A * ((A + 1) + (A - 1) * cw + s), -2 * A * ((A - 1) + (A + 1) * cw),
                 A * ((A + 1) + (A - 1) * cw - s)]
            a = [(A + 1) - (A - 1) * cw + s, 2 * ((A - 1) - (A + 1) * cw),
                 (A + 1) - (A - 1) * cw - s]
    return np.array([b + a]) / a[0]


def _peaks_db(x, sr):
    hop = max(int(sr / 1000), 1)  # 1 ms control rate
    k = len(x) // hop
    peak = np.abs(x[: k * hop]).reshape(k, hop).max(axis=1)
    return 20 * np.log10(peak + 1e-9), hop, k


def _smooth_gr(target, up_ms, down_ms):
    """One-pole smoothing of a gain-reduction curve (dB) with separate time
    constants for rising and falling targets."""
    up = math.exp(-1 / max(up_ms, 0.1))
    dn = math.exp(-1 / max(down_ms, 1))
    gr, cur, i = np.empty(len(target)), 0.0, 0
    for t in target.tolist():
        co = up if t > cur else dn
        cur = co * cur + (1 - co) * t
        gr[i] = cur
        i += 1
    return gr


def _apply_gr(x, gr, hop, k):
    pos = np.arange(k) * hop + hop / 2
    return x * 10 ** (-np.interp(np.arange(len(x)), pos, gr) / 20)


def compress(x, sr, p):
    lvl, hop, k = _peaks_db(x, sr)
    target = np.maximum(lvl - p["threshold_db"], 0) * (1 - 1 / max(p["ratio"], 1))
    return _apply_gr(x, _smooth_gr(target, p["attack_ms"], p["release_ms"]), hop, k)


def gate(x, sr, p):
    """Downward expander/gate: closes slowly (release), opens fast (attack)."""
    lvl, hop, k = _peaks_db(x, sr)
    target = np.minimum(np.maximum(p["threshold_db"] - lvl, 0) * (p.get("ratio", 4) - 1),
                        p.get("range_db", 20))
    gr = _smooth_gr(target, p.get("release_ms", 80), p.get("attack_ms", 3))
    return _apply_gr(x, gr, hop, k)


def saturate(x, drive):
    """Level-compensated light/medium tanh saturator.

    Old version crushed RMS at high drive and required +20 dB or more of makeup.
    Default dry blend 45% preserves much of the original vocal's consonants.
    This is a safe *model*, not a claim of identical proprietary saturation.
    """
    drive = float(np.clip(drive, 0.7, 3.0))
    if drive <= 1.0:
        return x.copy()
    ref = float(np.percentile(np.abs(x), 99)) + 1e-10
    shaped = ref * np.tanh(drive * x / ref) / drive
    rms_in = np.sqrt(np.mean(x*x)) + 1e-12
    rms_out = np.sqrt(np.mean(shaped*shaped)) + 1e-12
    # Keep gain in check; dry and wet shouldn't drift wildly in volume.
    compensate = np.clip(rms_in/rms_out, 1.0, 10**(6/20))
    wet = shaped * compensate
    return 0.55 * x + 0.45 * wet


def deess(x, sr, p):
    band = signal.sosfilt(biquad("bandpass", p["freq_hz"], 0, p.get("q", 1.5), sr), x)
    red = compress(band, sr, {"threshold_db": p["threshold_db"], "ratio": p["ratio"],
                              "attack_ms": p.get("attack_ms", 1),
                              "release_ms": p.get("release_ms", 40)})
    return x - band + red


def _moddelay(y, sr, base_ms, depth_ms, rate_hz, phase=0.0, t0=0.0):
    n = len(y)
    t = np.arange(n) / sr + t0
    d = (base_ms + depth_ms * np.sin(2 * np.pi * rate_hz * t + phase)) * sr / 1000
    pos = np.arange(n) - d
    i0 = np.floor(pos).astype(int)
    fr = pos - i0
    out = y[np.clip(i0, 0, n - 1)] * (1 - fr) + y[np.clip(i0 + 1, 0, n - 1)] * fr
    # Don't repeat the first sample before the delay line has any data.
    out[(pos < 0) | (pos >= n - 1)] = 0.0
    return out


def _phaser(y, sr, p):
    n, blk, stages = len(y), 128, int(p.get("stages", 4))
    out, zi = np.empty(n), np.zeros((stages, 2))
    for s in range(0, n, blk):
        t = (s + blk / 2) / sr + p.get("t0_s", 0.0)
        f = p["center_hz"] * 2 ** (p.get("depth_oct", 1.5) * math.sin(2 * math.pi * p["rate_hz"] * t + p.get("phase", 0.0)))
        tn = math.tan(math.pi * min(f, sr * 0.45) / sr)
        a = (tn - 1) / (tn + 1)
        sos = np.tile([a, 1.0, 0.0, 1.0, a, 0.0], (stages, 1))
        out[s:s + blk], zi = signal.sosfilt(sos, y[s:s + blk], zi=zi)
    return y + p.get("mix", 0.7) * out


def modulate(y, sr, p):
    t, mix = p["type"], p.get("mix", 0.5)
    t0, ph = p.get("t0_s", 0.0), p.get("phase", 0.0)
    if t == "chorus":
        v = int(p.get("voices", 1))
        wet = sum(_moddelay(y, sr, p["base_ms"], p["depth_ms"], p["rate_hz"], ph + 2 * math.pi * k / v, t0)
                  for k in range(v)) / v
        return y + mix * wet
    if t == "flanger":
        w1 = _moddelay(y, sr, p["base_ms"], p["depth_ms"], p["rate_hz"], ph, t0)
        w2 = _moddelay(w1, sr, p["base_ms"], p["depth_ms"], p["rate_hz"], ph, t0)
        w3 = _moddelay(w2, sr, p["base_ms"], p["depth_ms"], p["rate_hz"], ph, t0)
        fb = p.get("feedback", 0.3)
        return y + mix * (w1 + fb * w2 + fb * fb * w3)
    if t == "vibrato":
        return _moddelay(y, sr, p["base_ms"], p["depth_ms"], p["rate_hz"], ph, t0)
    if t == "tremolo":
        return y * (1 - p["depth"] * (0.5 + 0.5 * np.sin(2 * np.pi * p["rate_hz"] * (np.arange(len(y)) / sr + t0) + ph)))
    if t == "phaser":
        return _phaser(y, sr, p)
    return y


_IR_CACHE = {}


def add_space(y, sr, p, seed=1):
    out = y.copy()
    d = p.get("delay")
    if d and d.get("enabled"):
        g1, fb, t = 10 ** (d["mix_db"] / 20), d.get("feedback", 0), int(d["time_ms"] * sr / 1000)
        if t < 1:
            raise ValueError("delay time must be at least one sample")
        if not (0 <= fb < 1):
            raise ValueError("delay feedback must be between 0 and 1 (exclusive)")
        for k in range(1, 25):
            a = g1 * fb ** (k - 1)
            if a < 1e-3 or k * t >= len(y):
                break
            out[k * t:] += a * y[: len(y) - k * t]
    r = p.get("reverb")
    if r and r.get("enabled"):
        key = (sr, round(r["rt60_s"], 3), round(r["wet_db"], 2), r.get("predelay_ms", 0), r.get("damping_hz"), seed)
        ir = _IR_CACHE.get(key)
        if ir is None:
            rng = np.random.default_rng(seed)
            pre = int(r.get("predelay_ms", 0) * sr / 1000)
            n = pre + int(min(r["rt60_s"] * 1.1, 4.0) * sr)
            t = np.arange(n - pre) / sr
            ir = np.zeros(n)
            ir[pre:] = rng.standard_normal(n - pre) * np.exp(-6.908 * t / r["rt60_s"])
            if r.get("damping_hz"):
                ir = signal.sosfilt(signal.butter(1, min(r["damping_hz"], sr * 0.45), "low",
                                                  fs=sr, output="sos"), ir)
            ir *= math.sqrt(10 ** (r["wet_db"] / 10) / (np.sum(ir ** 2) + 1e-30))
            if len(_IR_CACHE) > 64:
                _IR_CACHE.clear()
            _IR_CACHE[key] = ir
        out += signal.fftconvolve(y, ir)[: len(y)]
    return out


def _active(p):
    return bool(p) and (not isinstance(p, dict) or p.get("enabled", True))


def _stage_hpf(y, sr, pr):
    p = pr["hpf"]
    return signal.sosfilt(biquad("highpass", p["freq_hz"], 0, 0.707, sr), y)


def _stage_lpf(y, sr, pr):
    return signal.sosfilt(biquad("lowpass", pr["lpf"]["freq_hz"], 0, 0.707, sr), y)


def _stage_eq(y, sr, pr):
    for b in pr["eq"]:
        if abs(b["gain_db"]) > 0.05 and b["freq_hz"] < sr * 0.45:
            y = signal.sosfilt(biquad(b["type"], b["freq_hz"], b["gain_db"], b["q"], sr), y)
    return y


def _stage_limiter(y, sr, pr):
    c = 10 ** (pr["limiter"]["ceiling_db"] / 20)
    y = compress(y, sr, {"threshold_db": pr["limiter"]["ceiling_db"] - 0.5, "ratio": 50,
                         "attack_ms": 0.3, "release_ms": 50})
    return np.clip(y, -c, c)


# name -> (is_active(preset), function(y, sr, preset), cache-key payload(preset))
STAGES = [
    ("hpf", lambda p: _active(p.get("hpf")), _stage_hpf),
    ("lpf", lambda p: _active(p.get("lpf")), _stage_lpf),
    ("gate", lambda p: _active(p.get("gate")), lambda y, sr, p: gate(y, sr, p["gate"])),
    ("deesser", lambda p: _active(p.get("deesser")), lambda y, sr, p: deess(y, sr, p["deesser"])),
    ("saturation", lambda p: _active(p.get("saturation")),
     lambda y, sr, p: saturate(y, p["saturation"]["drive"])),
    ("compressor", lambda p: bool(p.get("compressor")), lambda y, sr, p: compress(y, sr, p["compressor"])),
    ("eq", lambda p: bool(p.get("eq")), _stage_eq),
    ("modulation", lambda p: _active(p.get("modulation")), lambda y, sr, p: modulate(y, sr, p["modulation"])),
    ("space", lambda p: _active(p.get("delay")) or _active(p.get("reverb")), lambda y, sr, p: add_space(y, sr, p)),
    ("gain", lambda p: abs((p.get("gain") or {}).get("gain_db", 0)) > 0.01,
     lambda y, sr, p: y * 10 ** (p["gain"]["gain_db"] / 20)),
    ("limiter", lambda p: _active(p.get("limiter")), _stage_limiter),
]
_KEYS = {"space": ("delay", "reverb")}


def render(x, sr, preset, cache=None):
    """Render audio through a preset. `cache` (a dict) memoises every stage so
    an optimiser that changes one parameter only recomputes what follows it."""
    y = np.asarray(x, dtype=np.float64)
    key = ""
    for name, active, fn in STAGES:
        if not active(preset):
            continue
        payload = [preset.get(k) for k in _KEYS.get(name, (name,))]
        key += "|" + name + json.dumps(payload, sort_keys=True, default=float)
        if cache is not None and key in cache:
            y = cache[key]
            continue
        y = fn(y, sr, preset)
        if cache is not None:
            cache[key] = y
            if len(cache) > 160:
                cache.pop(next(iter(cache)))
    return y


def render_stereo(raw, sr, preset):
    """Heuristic stereo rendering for mono dry inputs, centered dry and distinct L/R ambience.

    This removes the v0.2 mono-only preview limitation for synthetic stereo ambience.
    It is NOT a stereo reconstruction of a proprietary effect from a reference.
    """
    pre = copy.deepcopy(preset)
    for name in ('delay', 'reverb', 'gain', 'limiter'):
        pre[name] = {'enabled':False}
    core = render(np.asarray(raw,dtype=np.float64),sr,pre)
    if _active(preset.get('reverb')):
        left = add_space(core,sr,preset,seed=1)
        right = add_space(core,sr,preset,seed=2)
    else:
        left = add_space(core,sr,preset,seed=1)
        right = left.copy()
    out = np.column_stack((left,right))
    gain=preset.get('gain',{})
    if gain.get('enabled') and abs(gain.get('gain_db',0))>1e-6:
        out *= 10**(gain['gain_db']/20)
    lim=preset.get('limiter',{})
    if lim.get('enabled'):
        out = np.column_stack([_stage_limiter(out[:,i],sr,preset) for i in range(2)])
    return out


# ---------------------------------------------------------------- alignment helpers
def _lag(dry, mixed, sr):
    """Bulk latency (samples, +/-1 s) of mixed relative to dry."""
    n = min(len(dry), len(mixed))
    cc = signal.correlate(mixed[:n], dry[:n], mode="full", method="fft")
    lags = np.arange(-(n - 1), n)
    ok = np.abs(lags) <= sr
    return int(lags[ok][np.argmax(np.abs(cc[ok]))])


def _lag_env_corr(dry, mixed, sr, block_ms=5):
    """Latency (samples) and peak normalised correlation of loudness envelopes
    (+/-1 s, ~5 ms precision). Unlike waveform correlation it survives pitch
    shifting and heavy processing."""
    b = max(int(sr * block_ms / 1000), 1)
    n = min(len(dry), len(mixed)) // b * b
    env = lambda x: np.abs(x[:n]).reshape(-1, b).mean(axis=1)
    a, c = env(dry), env(mixed)
    a, c = a - a.mean(), c - c.mean()
    cc = signal.correlate(c, a, mode="full", method="fft")
    lags = np.arange(-(len(a) - 1), len(a))
    ok = np.abs(lags) <= int(sr / b)
    i = int(np.argmax(cc[ok]))
    return int(lags[ok][i]) * b, float(cc[ok][i] / (np.linalg.norm(a) * np.linalg.norm(c) + 1e-12))


def _lag_env(dry, mixed, sr, block_ms=5):
    return _lag_env_corr(dry, mixed, sr, block_ms)[0]


def _shift(dry, mixed, lag):
    n = min(len(dry), len(mixed))
    dry, mixed = dry[:n], mixed[:n]
    if lag > 0:
        return dry[: n - lag], mixed[lag:]
    if lag < 0:
        return dry[-lag:], mixed[: n + lag]
    return dry, mixed


def _window(n):
    return min(1 << int(math.log2(max(n // 4, 1))), 1 << 17)


def _welch(dry, mixed, L):
    win, hop = np.hanning(L), L // 2
    Sdd = Sdm = Smm = 0
    for s in range(0, len(dry) - L + 1, hop):
        D, M = np.fft.rfft(dry[s:s + L] * win), np.fft.rfft(mixed[s:s + L] * win)
        Sdd = Sdd + np.abs(D) ** 2
        Sdm = Sdm + np.conj(D) * M
        Smm = Smm + np.abs(M) ** 2
    return Sdd, Sdm, Smm


def same_take_score(raw, mixed, sr):
    """0..1 similarity of the time-varying spectral *pattern* (level- and
    EQ-independent) of raw vs mixed after alignment. Same take ~0.8+,
    different takes of the same song ~0.1-0.4."""
    r, m = _shift(raw[: sr * 40], mixed[: sr * 40], _lag_env(raw[: sr * 40], mixed[: sr * 40], sr))
    c = band_centres(sr)
    c = c[(c >= 200) & (c <= 8000)]
    feats = []
    for x in (r, m):
        f, _, Z = signal.stft(x, sr, nperseg=2048, noverlap=1024)
        p = np.abs(Z) ** 2
        feats.append(np.array([10 * np.log10(p[(f >= fc / 1.122) & (f < fc * 1.122)].mean(axis=0) + 1e-12)
                               for fc in c]))
    a, b = feats
    loud = (a.mean(axis=0) > a.mean(axis=0).max() - 30) & (b.mean(axis=0) > b.mean(axis=0).max() - 30)
    if loud.sum() < 20:
        return 0.0
    a, b = a[:, loud], b[:, loud]
    a = a - a.mean(axis=0) - a.mean(axis=1, keepdims=True) + a.mean()
    b = b - b.mean(axis=0) - b.mean(axis=1, keepdims=True) + b.mean()
    a, b = a.ravel(), b.ravel()
    return float(max(np.corrcoef(a, b)[0, 1], 0))


# ---------------------------------------------------------------- reverb + delay (impulse response)
def estimate_space(dry, mixed, sr):
    """Deconvolve mixed by the processed dry signal, then read echoes (delay)
    and the diffuse decaying tail (reverb) out of the impulse response."""
    none = dict(OFF)
    lag = _lag(dry, mixed, sr)
    dry, mixed = _shift(dry, mixed, lag)
    n = len(dry)
    L = _window(n)
    if L < (1 << 14):
        return none, none, {"status": "audio too short for reverb/delay analysis (need ~2 s+)"}
    Sdd, Sdm, Smm = _welch(dry, mixed, L)
    freqs = np.fft.rfftfreq(L, 1 / sr)
    coh = np.abs(Sdm) ** 2 / (Sdd * Smm + 1e-30)
    mid = (freqs >= 300) & (freqs <= 4000)
    coh_mid = float(coh[mid].mean())
    diag = {"coherence": round(coh_mid, 2), "alignment_lag_ms": round(lag * 1000 / sr, 1),
            "ir_window_s": round(L / 2 / sr, 2)}
    if coh_mid < 0.35:
        diag["status"] = ("low coherence: raw and mixed look like different takes, or the "
                          "chain is very nonlinear; reverb/delay not estimated")
        return none, none, diag
    H = Sdm / (Sdd + 1e-3 * Sdd.mean()) * np.clip(coh, 0, 1)
    h = np.fft.irfft(H, L)[: L // 2]
    k0 = int(np.argmax(np.abs(h[: int(0.02 * sr)])))
    h = h[k0:]
    e = h ** 2
    dt = max(int(0.003 * sr), 2)
    E0 = e[:dt].sum()
    if E0 <= 0:
        diag["status"] = "no direct path found"
        return none, none, diag
    sm = max(int(0.002 * sr), 1)
    es = np.convolve(e, np.ones(sm) / sm, "same")
    env_db = 10 * np.log10(es / es[:dt].max() + 1e-12)
    nf = float(e[-int(0.15 * len(e)):].mean())

    # ---- delay: distinct echoes standing above the diffuse tail
    s0 = int(0.03 * sr)
    pk, _ = signal.find_peaks(env_db[s0:], height=-28, prominence=9, distance=int(0.04 * sr))
    pk = np.array([p + s0 for p in pk if es[p + s0] > 30 * nf], dtype=int)
    w = int(0.004 * sr)
    tap_e = lambda p: float(e[max(p - w, 0): p + w].sum())
    delay = none
    if len(pk):
        t1 = pk[0]
        taps = {}
        for p in pk:
            k = int(round(p / t1))
            if k >= 1 and abs(p - k * t1) <= 0.08 * k * t1 and k not in taps:
                taps[k] = int(p)
        t_ms = float(np.median([p / k for k, p in taps.items()])) * 1000 / sr
        E = {k: tap_e(p) for k, p in taps.items()}
        ratios = [math.sqrt(E[k + 1] / E[k]) for k in E if k + 1 in E and E[k] > 0]
        fb = float(np.clip(np.median(ratios), 0, 0.9)) if ratios else 0.0
        mix_db = 10 * math.log10(E[1] / E0 + 1e-12)
        if mix_db > -30:
            snr = 10 * math.log10(es[t1] / nf)
            delay = {"enabled": True, "time_ms": round(t_ms), "feedback": round(fb, 2),
                     "mix_db": round(mix_db, 1), "taps_found": len(taps),
                     "confidence": round(min(1, snr / 30) * min(1, coh_mid + 0.2), 2)}

    # ---- reverb: log-linear fit of the tail energy (echo windows removed)
    bl = int(0.005 * sr)
    nb = len(e) // bl
    Eb = e[: nb * bl].reshape(nb, bl).sum(axis=1)
    for p in pk:
        Eb[max((p - int(0.01 * sr)) // bl, 2): (p + int(0.01 * sr)) // bl + 1] = np.nan
    idx = np.arange(nb)
    good = ~np.isnan(Eb)
    Eb = np.interp(idx, idx[good], Eb[good])
    floor = nf * bl

    def tail_fit(start):
        ok = Eb[start:] > 2.5 * floor
        run = len(ok) if ok.all() else int(np.argmin(ok))
        if run < 8:
            return None
        tt = (np.arange(start, start + run) + 0.5) * 0.005
        return np.polyfit(tt, 10 * np.log10(Eb[start:start + run] - floor), 1)

    fit = tail_fit(50)
    if fit is None:
        fit = tail_fit(12)
    reverb = none
    if fit is None or fit[0] > -5:
        diag["status"] = "ok (no measurable reverb decay)"
        return delay, reverb, diag
    slope, icpt = fit
    rt60 = float(np.clip(-60 / slope, 0.1, 6.0))
    Eb2 = np.maximum(Eb - floor, 0)
    head = Eb2[2: 2 + 50]
    first = int(np.argmax(head >= head.max() * 0.25))
    pre = (first + 2) * 5
    pre = 0 if pre <= 15 else int(round(pre / 5) * 5)
    t_on = max(pre / 1000, 0.01)
    k = -slope * math.log(10) / 10
    Et = 10 ** ((icpt + slope * t_on) / 10) / 0.005 / k
    wet_db = 10 * math.log10(Et / E0 + 1e-12)
    if wet_db < -32 or rt60 < 0.15:
        diag["status"] = "ok"
        return delay, reverb, diag
    damping = None
    seg = h[int(0.01 * sr): int(0.6 * sr)]
    if len(seg) > 1024 and coh[(freqs >= 6000) & (freqs <= 10000)].mean() > 0.3:
        c3 = band_centres(sr)
        f, P = signal.welch(seg, sr, nperseg=min(len(seg), 4096))
        db = _bands_from_power(f, P, c3)
        ref = db[(c3 >= 500) & (c3 <= 1000)].mean()
        hi = np.where((c3 >= 1000) & (db - ref <= -6))[0]
        damping = int(round(c3[hi[0]])) if len(hi) else None
    snr = 10 * math.log10(10 ** ((icpt + slope * t_on) / 10) / floor + 1e-12)
    tm = (np.arange(max(int(t_on / 0.005), 2), 12) + 0.5) * 0.005
    excess = 10 * math.log10(Eb[max(int(t_on / 0.005), 2): 12].mean() /
                             (10 ** ((icpt + slope * tm) / 10)).mean() + 1e-12) if len(tm) else 0.0
    conf = min(1, max(snr, 0) / 25) * min(1, coh_mid + 0.2) * (0.25 if excess > 6 else 1.0)
    if rt60 >= 5.5:
        conf *= 0.5
    diag["reverb_model_mismatch_db"] = round(excess, 1)
    reverb = {"enabled": True, "predelay_ms": pre, "rt60_s": round(rt60, 2),
              "wet_db": round(wet_db, 1), "damping_hz": damping, "confidence": round(conf, 2)}
    if rt60 >= 5.5 or reverb["confidence"] < 0.3:
        diag["reverb_candidate_rejected"] = reverb
        reverb = none
    diag["status"] = "ok"
    return delay, reverb, diag


# ---------------------------------------------------------------- new-effect detectors
def gate_candidates(raw, sr):
    """Starting points for a noise gate/expander (the optimiser decides)."""
    w = int(sr * 0.05)
    k = len(raw) // w
    pk = 20 * np.log10(np.abs(raw[: k * w].reshape(k, w)).max(axis=1) + 1e-9)
    floor, speech = np.percentile(pk, 10), np.percentile(pk, 80)
    base = float(floor + 0.3 * (speech - floor))
    return [{"enabled": True, "threshold_db": round(base + o, 1), "range_db": r, "ratio": 4.0,
             "attack_ms": 3, "release_ms": 80} for o in (-10, -4, 2) for r in (12.0, 25.0)]


def track_short_delay(dry, mixed, sr, win_s=0.15, hop_s=0.05):
    """Per-window (~0.15 s) deconvolution of mixed by dry; follows the strongest
    secondary delay (0.5-45 ms). A chorus/flanger shows up as a delay whose
    lag oscillates; a doubler/short slap as a constant lag."""
    d, m = _shift(dry, mixed, _lag(dry, mixed, sr))
    W, hop = int(win_s * sr), int(hop_s * sr)
    Nf = 1 << int(math.ceil(math.log2(2 * W)))
    win = np.hanning(W)
    lo, hi, guard = int(0.0005 * sr), int(0.045 * sr), max(int(0.0004 * sr), 2)
    ref = np.sqrt(np.mean(d ** 2))
    rows = []
    for s in range(0, len(d) - W, hop):
        dw = d[s:s + W] * win
        if np.sqrt(np.mean(dw ** 2)) < 0.5 * ref * 0.6:
            continue
        D, M = np.fft.rfft(dw, Nf), np.fft.rfft(m[s:s + W] * win, Nf)
        Pd = np.abs(D) ** 2
        h = np.fft.irfft(np.conj(D) * M / (Pd + 0.02 * Pd.mean()), Nf)
        h0 = max(np.abs(h[:guard]).max(), np.abs(h[-guard:]).max())
        seg = np.abs(h[lo:hi])
        j = int(np.argmax(seg))
        rows.append(((s + W / 2) / sr, (lo + j) * 1000 / sr, seg[j] / (h0 + 1e-12),
                     seg[j] / (np.median(seg) + 1e-12)))
    return np.array(rows)


def modulation_from_tracking(rows):
    """Turn the lag track into chorus/flanger candidates (rate and LFO phase
    come from a sine fit to the lag series). Returns (candidates, info)."""
    info = {"windows": int(len(rows))}
    if len(rows) < 12:
        return [], info
    hit = (rows[:, 3] > 5) & (rows[:, 2] > 0.08)
    info["hit_fraction"] = round(float(hit.mean()), 2)
    if hit.mean() < 0.5 or hit.sum() < 10:
        return [], info
    t, lag, amp = rows[hit, 0], rows[hit, 1], rows[hit, 2]
    mean_lag, amp_med = float(np.median(lag)), float(np.median(amp))
    info.update({"median_lag_ms": round(mean_lag, 2), "median_rel_amp": round(amp_med, 2),
                 "lag_std_ms": round(float(lag.std()), 2)})
    kind = "flanger" if mean_lag < 7 else "chorus"
    base = {"enabled": True, "type": kind, "mix": round(min(amp_med, 1.0), 2), "voices": 1,
            "feedback": 0.3}
    if lag.std() < 0.25:                      # constant lag: doubler / short slap
        info["interpretation"] = "static short delay (doubler / comb)"
        return [{**base, "type": "chorus", "rate_hz": 0.5, "base_ms": round(mean_lag, 2),
                 "depth_ms": 0.0, "phase": 0.0}], info
    best = (1e18, None)
    sst = float(np.sum((lag - lag.mean()) ** 2))
    for r in np.arange(0.1, 6.0, 0.01):
        A = np.stack([np.ones_like(t), np.sin(2 * np.pi * r * t), np.cos(2 * np.pi * r * t)], axis=1)
        coef, res, *_ = np.linalg.lstsq(A, lag, rcond=None)
        sse = float(np.sum((A @ coef - lag) ** 2))
        if sse < best[0]:
            best = (sse, (r, coef))
    r2 = 1 - best[0] / (sst + 1e-12)
    info["sine_fit_r2"] = round(r2, 2)
    if r2 < 0.35:
        # two symmetric voices (base +/- depth*sin): the strongest tap flips sides, so the
        # deviation |lag - base| is a rectified sine, whose fundamental is at twice the LFO rate
        dev = np.abs(lag - mean_lag)
        sstd = float(np.sum((dev - dev.mean()) ** 2))
        bf = (1e18, None)
        for f in np.arange(0.2, 12.0, 0.02):
            A = np.stack([np.ones_like(t), np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t)], axis=1)
            coef, *_ = np.linalg.lstsq(A, dev, rcond=None)
            sse = float(np.sum((A @ coef - dev) ** 2))
            if sse < bf[0]:
                bf = (sse, (f, coef))
        r2b = 1 - bf[0] / (sstd + 1e-12)
        info["rectified_fit_r2"] = round(r2b, 2)
        if r2b < 0.25:
            info["interpretation"] = "delay present but lag not periodic; not modelled"
            return [], info
        f, (c1, a1, b1) = bf[1]
        delta = math.atan2(a1, b1)
        info["interpretation"] = f"two-voice chorus, rate {f / 2:.2f} Hz"
        return [{**base, "type": "chorus", "voices": 2, "mix": round(min(2 * amp_med, 1.0), 2),
                 "rate_hz": round(f / 2, 3), "base_ms": round(mean_lag, 2),
                 "depth_ms": round(float(dev.mean()) * math.pi / 2, 2),
                 "phase": round((-delta - math.pi) / 2, 3)}], info
    r, (c0, a, b) = best[1]
    depth, phase = math.hypot(a, b), math.atan2(b, a)
    info["interpretation"] = f"{kind}-style modulated delay, rate {r:.2f} Hz"
    cand = {**base, "rate_hz": round(float(r), 3), "base_ms": round(float(c0), 2),
            "depth_ms": round(float(depth), 2), "phase": round(float(phase), 3)}
    return [cand], info


def limiter_candidate(mixed, rendered):
    """Many samples sitting flat at one ceiling (limiter/clipper); an unlimited
    vocal has a handful of peak samples, a limited one has hundreds."""
    mx = float(np.abs(mixed).max())
    frac = float(np.mean(np.abs(mixed) >= 0.97 * mx))
    if frac > 8e-5:
        return {"enabled": True, "ceiling_db": round(20 * math.log10(mx), 1),
                "confidence": round(min(1.0, frac / 4e-4), 2)}
    return dict(OFF)


# ---- pitch
def track_f0(x, sr, fmin=70, fmax=800):
    N, hop = 2048, 512
    if len(x) < 3 * N:
        return np.array([])
    idx = np.arange(0, len(x) - N, hop)
    w = np.hanning(N)
    frames = np.stack([x[i:i + N] for i in idx]) * w
    F = np.fft.rfft(frames, 2 * N, axis=1)
    acf = np.fft.irfft(F * np.conj(F), axis=1)[:, :N]
    wa = np.fft.irfft(np.abs(np.fft.rfft(w, 2 * N)) ** 2)[:N]
    acf = acf / (wa + 1e-9)
    acf = acf / (acf[:, :1] + 1e-12)
    lmin, lmax = int(sr / fmax), int(sr / fmin)
    energy = (frames ** 2).sum(axis=1)
    f0 = np.full(len(idx), np.nan)
    for t in range(len(idx)):
        if energy[t] < energy.max() * 1e-3:
            continue
        s = acf[t, lmin:lmax]
        pks, _ = signal.find_peaks(s)
        if not len(pks):
            continue
        top = s[pks].max()
        if top < 0.7:
            continue
        p = lmin + int(pks[np.argmax(s[pks] >= 0.9 * top)])
        y0, y1, y2 = acf[t, p - 1], acf[t, p], acf[t, p + 1]
        den = y0 - 2 * y1 + y2
        f0[t] = sr / (p + (0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0))
    return f0


_NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def analyze_pitch(raw, mixed, sr):
    """Compare f0 tracks: auto-tune style correction strength, global
    transposition and a key guess. Analysis only, not rendered."""
    r, m = _shift(raw[: sr * 60], mixed[: sr * 60], _lag_env(raw[: sr * 60], mixed[: sr * 60], sr))
    fr, fm = track_f0(r, sr), track_f0(m, sr)
    if not len(fr) or not len(fm):
        return {"status": "audio too short for pitch analysis"}
    n = min(len(fr), len(fm))
    fr, fm = fr[:n], fm[:n]
    ok = ~np.isnan(fr) & ~np.isnan(fm)
    if ok.sum() < 40:
        return {"status": "too few voiced frames for pitch analysis"}
    cr, cm = 1200 * np.log2(fr[ok] / 440), 1200 * np.log2(fm[ok] / 440)
    diff = ((cm - cr + 600) % 1200) - 600          # wrap: octave tracking errors vanish
    dev = lambda c, t: ((c - t + 50) % 100) - 50
    ref = min(range(-50, 50, 5), key=lambda t: np.mean(np.abs(dev(cm, t))))
    dm, dr = dev(cm, ref), dev(cr, ref)
    big = np.abs(dr) > 8
    slope = float(np.sum(dm[big] * dr[big]) / np.sum(dr[big] ** 2)) if big.sum() > 20 else 1.0
    strength = float(np.clip(1 - slope, 0, 1))
    mad_r, mad_m = float(np.mean(np.abs(dr))), float(np.mean(np.abs(dm)))
    detected = strength > 0.35 and mad_r > 8
    unreliable = bool(np.std(diff) > 60)             # tracks disagree: echoes/comb effects confuse f0
    if unreliable:
        detected = False
    out = {"correction": {"detected": bool(detected), "strength": round(strength, 2),
                          "reference_hz": round(440 * 2 ** (ref / 1200), 1),
                          "reference_offset_cents": int(ref),
                          "mean_abs_deviation_cents": {"raw": round(mad_r, 1), "mixed": round(mad_m, 1)},
                          "style": ("hard/robotic" if strength > 0.85 and mad_m < 8 else "natural")
                          if detected else None},
           "transpose_semitones": 0.0, "voiced_frames": int(len(cr)),
           "confidence": round(float(min(1, big.sum() / 150) * min(1, mad_r / 15)), 2),
           "rendered_in_preview": False}
    if strength < 0.3 and abs(np.median(diff)) > 40 and np.std(diff) < 40:
        out["transpose_semitones"] = round(float(np.median(diff)) / 100, 2)
    if detected and abs(ref) >= 10:
        out["correction"]["note"] = ("mixed pitch clusters away from A=440; a constant flat/sharp offset "
                                     "left after partial correction looks the same as a different tuning "
                                     "reference, so strength may be overestimated")
    pcs = np.round((cm - ref) / 100).astype(int) % 12
    hist = np.bincount(pcs, minlength=12).astype(float)
    best = (-2, "")
    for k in range(12):
        h = np.roll(hist, -k)
        for prof, nm in ((_MAJ, "major"), (_MIN, "minor")):
            cc = np.corrcoef(h, prof)[0, 1]
            if cc > best[0]:
                best = (cc, f"{_NOTES[k]} {nm}")
    out["key_guess"] = best[1]
    out["key_confidence"] = round(float(max(best[0], 0)), 2)
    return out


# ---- stereo
def analyze_stereo(ch, sr):
    if ch is None or ch.shape[1] < 2:
        return {"is_stereo": False}
    L, R = ch[:, 0], ch[:, 1]
    M, S = (L + R) / 2, (L - R) / 2
    rm, rs = np.sqrt(np.mean(M ** 2)) + 1e-12, np.sqrt(np.mean(S ** 2)) + 1e-12
    s2m = 20 * math.log10(rs / rm)
    if s2m < -60:
        return {"is_stereo": True, "side_to_mid_db": round(s2m, 1), "lr_correlation": 1.0,
                "haas_delay_ms": None, "notes": ["essentially mono (identical channels)"],
                "rendered_in_preview": False}
    corr = float(np.corrcoef(L, R)[0, 1]) if L.std() > 0 and R.std() > 0 else 1.0
    n = min(len(L), sr * 30)
    cc = signal.correlate(R[:n], L[:n], mode="full", method="fft")
    lags = np.arange(-(n - 1), n)
    okl = np.abs(lags) <= int(0.04 * sr)
    cc = cc / (np.sqrt(np.sum(L[:n] ** 2) * np.sum(R[:n] ** 2)) + 1e-12)
    i = int(np.argmax(np.abs(cc[okl])))
    lag_ms = float(lags[okl][i]) * 1000 / sr
    c0 = float(cc[np.where(lags == 0)[0][0]])
    haas = abs(lag_ms) > 0.4 and abs(cc[okl][i]) > 0.3 and abs(cc[okl][i]) > abs(c0) + 0.05
    c3 = band_centres(sr)
    sm, ss = band_spectrum_db(M, sr, c3), band_spectrum_db(S, sr, c3)
    side_hi = float(np.mean((ss - sm)[c3 > 3000]))
    side_lo = float(np.mean((ss - sm)[c3 < 300]))
    notes = []
    if s2m < -30:
        notes.append("essentially mono")
    elif s2m > -8:
        notes.append("very wide: widener, stereo doubler or wide stereo reverb likely")
    if haas:
        notes.append(f"Haas-style delay between channels (~{abs(lag_ms):.1f} ms, "
                     f"{'right' if lag_ms > 0 else 'left'} later)")
    if side_hi - side_lo > 8:
        notes.append("width concentrated in highs (stereo reverb/exciter-style widening)")
    return {"is_stereo": True, "side_to_mid_db": round(s2m, 1), "lr_correlation": round(corr, 2),
            "haas_delay_ms": round(abs(lag_ms), 1) if haas else None,
            "side_minus_mid_db": {"low": round(side_lo, 1), "high": round(side_hi, 1)},
            "notes": notes, "rendered_in_preview": False}


# ---------------------------------------------------------------- analysis-by-synthesis
SAME_TAKE_MIN = 0.45     # same_take_score threshold for refinement / pitch / modulation
MIN_GAIN = 0.01          # an optional effect must lower the spectrogram loss by >= 1 %
OPTIONAL = ("hpf", "lpf", "gate", "deesser", "saturation", "modulation", "delay", "reverb")


class Target:
    """Multi-resolution log-spectrogram distance to the mixed excerpt."""
    RES = (512, 2048)

    def __init__(self, m, sr):
        self.sr = sr
        self.m = m / (np.sqrt(np.mean(m ** 2)) + 1e-12)
        self.B = [self._spec(self.m, n) for n in self.RES]
        self.ref = [b.max() for b in self.B]
        self.LB = [self._db(b, r) for b, r in zip(self.B, self.ref)]

    def _spec(self, x, n):
        f, _, Z = signal.stft(x, self.sr, nperseg=n, noverlap=n * 3 // 4, boundary=None, padded=False)
        return np.abs(Z)[f <= 16000]

    @staticmethod
    def _db(a, ref):
        return 20 * np.log10(np.maximum(a / ref, 10 ** (-70 / 20)))

    def loss(self, y):
        y = y / (np.sqrt(np.mean(y ** 2)) + 1e-12)
        return float(np.mean([np.mean(np.abs(self._db(self._spec(y, n), r) - lb))
                              for n, r, lb in zip(self.RES, self.ref, self.LB)]))


def _on(p, k):
    return isinstance(p.get(k), dict) and p[k].get("enabled")


def _specs(p):
    s = [(("compressor", "threshold_db"), -36, -3, 2.0, "add"), (("compressor", "ratio"), 1, 5, 1.3, "mul"),
         (("compressor", "attack_ms"), 5, 40, 1.8, "mul"), (("compressor", "release_ms"), 20, 500, 1.6, "mul")]
    s += [(("eq", i, "gain_db"), -15, 15, 1.5, "add") for i in range(len(p["eq"]))]
    if _on(p, "hpf"):
        s.append((("hpf", "freq_hz"), 30, 500, 1.25, "mul"))
    if _on(p, "lpf"):
        s.append((("lpf", "freq_hz"), 3000, 16000, 1.25, "mul"))
    if _on(p, "saturation"):
        s.append((("saturation", "drive"), 1.0, 3.0, 0.35, "add"))
    if _on(p, "deesser"):
        s += [(("deesser", "ratio"), 1.2, 10, 1.4, "mul"), (("deesser", "threshold_db"), -70, -5, 3.0, "add")]
    if _on(p, "gate"):
        s += [(("gate", "threshold_db"), -70, -10, 3.0, "add"), (("gate", "range_db"), 3, 40, 4.0, "add")]
    if _on(p, "delay"):
        s += [(("delay", "time_ms"), 20, 1500, 1.03, "mul"), (("delay", "mix_db"), -30, 0, 1.5, "add"),
              (("delay", "feedback"), 0, 0.9, 0.08, "add")]
    if _on(p, "reverb"):
        s += [(("reverb", "wet_db"), -35, 0, 2.0, "add"), (("reverb", "rt60_s"), 0.15, 6, 1.3, "mul"),
              (("reverb", "predelay_ms"), 0, 120, 10, "add")]
        if p["reverb"].get("damping_hz"):
            s.append((("reverb", "damping_hz"), 1500, 16000, 1.4, "mul"))
    if _on(p, "modulation"):
        t = p["modulation"]["type"]
        if t in ("chorus", "flanger", "vibrato"):
            s += [(("modulation", "depth_ms"), 0.2, 15, 1.4, "mul"), (("modulation", "base_ms"), 0.3, 40, 1.25, "mul")]
        if t in ("chorus", "flanger", "phaser"):
            s.append((("modulation", "mix"), 0, 1.2, 0.1, "add"))
        if t == "flanger":
            s.append((("modulation", "feedback"), 0, 0.85, 0.1, "add"))
        if t == "tremolo":
            s.append((("modulation", "depth"), 0, 1, 0.1, "add"))
        if t == "phaser":
            s += [(("modulation", "center_hz"), 200, 5000, 1.3, "mul"), (("modulation", "depth_oct"), 0.3, 3, 0.5, "add")]
    return s


def _get(p, path):
    for k in path:
        p = p[k]
    return p


def _with(p, path, val):
    q = copy.deepcopy(p)
    cur = q
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = round(float(val), 4)
    return q


def refine(raw, mixed, sr, preset, cands, skip, quality):
    """Tune the preset by rendering it and minimising spectrogram distance to
    the mix; test optional effects on/off. Returns (preset, info)."""
    seconds, passes, max_evals = {"fast": (8, 1, 140), "normal": (14, 2, 300), "high": (24, 3, 600)}[quality]
    p = copy.deepcopy(preset)
    p.pop("gain", None)
    p.pop("limiter", None)
    for path, lo_, hi_, _, _ in _specs(p):              # clamp starting values into range
        p = _with(p, path, min(max(_get(p, path), lo_), hi_))
    lag = _lag(render(raw[: sr * 60], sr, p), mixed[: sr * 60], sr)
    N = int(min(seconds * sr, len(raw) - abs(lag) - 2, len(mixed) - abs(lag) - 2))
    cs = np.concatenate([[0], np.cumsum(raw ** 2)])
    lo, hi = max(0, -lag), len(raw) - N - max(lag, 0)
    starts = np.arange(lo, max(hi, lo + 1), max(sr // 2, 1))
    s0 = int(starts[np.argmax(cs[starts + N] - cs[starts])])
    r_ex, m_ex = raw[s0: s0 + N], mixed[s0 + lag: s0 + lag + N]
    tgt, cache, evals = Target(m_ex, sr), {}, [0]

    def E(q):
        evals[0] += 1
        if _on(q, "modulation"):
            q["modulation"]["t0_s"] = s0 / sr
        y = render(r_ex, sr, q, cache)
        # The original loss was scale invariant. It could reward crushed audio
        # that only resembled the target once a massive gain was added.
        spectral = tgt.loss(y)
        w = max(int(sr * 0.05), 1)
        k = min(len(y),len(m_ex)) // w
        ye = np.sqrt(np.mean(y[:k*w].reshape(k,w)**2,axis=1)+1e-12)
        me = np.sqrt(np.mean(m_ex[:k*w].reshape(k,w)**2,axis=1)+1e-12)
        ye_db, me_db = 20*np.log10(ye), 20*np.log10(me)
        env = float(np.mean(np.abs((ye_db-np.median(ye_db))-(me_db-np.median(me_db)))))
        # Extreme dynamics and saturation incur a modest explicit penalty.
        sat = max(0.0, q.get("saturation",{}).get("drive",0)-2.0) if _on(q,"saturation") else 0.0
        return spectral + 0.22*env + 0.5*sat

    def descend(p, base, npass):
        shrink = 1.0
        for _ in range(npass):
            for path, lo_, hi_, step, mode in _specs(p):
                for direction in (1, -1):
                    moved = False
                    for _ in range(3):
                        if evals[0] > max_evals:
                            return p, base
                        cur = _get(p, path)
                        new = cur + direction * step * shrink if mode == "add" \
                            else cur * (1 + (step - 1) * shrink) ** direction
                        new = min(max(new, lo_), hi_)
                        if abs(new - cur) < 1e-9:
                            break
                        q = _with(p, path, new)
                        L = E(q)
                        if L < base - 1e-4:
                            p, base, moved = q, L, True
                        else:
                            break
                    if moved:
                        break
            shrink *= 0.5
        return p, base

    tried = {}

    def toggle(p, base, name):
        if name in skip or _on(p, name) or not cands.get(name):
            return p, base
        best = (base, None)
        for c in cands[name]:
            q = copy.deepcopy(p)
            q[name] = c
            L = E(q)
            if L < best[0]:
                best = (L, c)
        tried[name] = round(100 * (base - best[0]) / base, 2)
        if best[1] is not None and (base - best[0]) / base >= MIN_GAIN:
            p[name], base = best[1], best[0]
        return p, base

    base0 = base = E(p)
    p, base = descend(p, base, 1)                       # settle compressor + EQ
    for name in ("gate", "deesser", "saturation", "delay", "reverb", "modulation", "hpf", "lpf"):
        p, base = toggle(p, base, name)                 # filters last: judged with the other effects present
    p, base = descend(p, base, passes)
    gains = {}
    for name in OPTIONAL:                               # ablation -> confidence, prune
        if not _on(p, name):
            continue
        q = copy.deepcopy(p)
        q[name] = dict(OFF)
        Lw = E(q)
        rel = (Lw - base) / Lw
        gains[name] = round(100 * rel, 2)
        p[name]["confidence"] = round(float(np.clip(rel / 0.04, 0, 1)), 2)
        weak = ((name == "hpf" and p[name]["freq_hz"] <= 40) or (name == "lpf" and p[name]["freq_hz"] >= 15000)
                or (name == "deesser" and p[name]["ratio"] < 1.8))
        if rel < MIN_GAIN * 0.6 or weak:
            p[name] = dict(OFF)
            gains[name] = f"pruned ({round(100 * rel, 2)}%{', weak setting' if weak else ''})"
    base = E(p)
    if _on(p, "modulation"):
        p["modulation"].pop("t0_s", None)
    return p, {"loss_before": round(base0, 3), "loss_after": round(base, 3), "evaluations": evals[0],
               "excerpt_s": round(N / sr, 1), "effect_loss_reduction_pct": gains,
               "candidate_loss_reduction_pct": tried}


# ---------------------------------------------------------------- analyze
def loud_rms(x, sr):
    w = int(sr * 0.05)
    k = len(x) // w
    fr = x[: k * w].reshape(k, w)
    rms = np.sqrt((fr ** 2).mean(axis=1))
    return float(np.sqrt(np.mean(fr[rms > rms.max() * 0.1] ** 2)))


def _note_value(ms, bpm):
    beat = 60000.0 / bpm
    names = {"1/2": 2, "1/4 dotted": 1.5, "1/4": 1, "1/4 triplet": 2 / 3, "1/8 dotted": 0.75,
             "1/8": 0.5, "1/8 triplet": 1 / 3, "1/16 dotted": 0.375, "1/16": 0.25}
    n = min(names, key=lambda k: abs(ms / beat - names[k]))
    return n, round(100 * (ms / (beat * names[n]) - 1), 1)


def analyze(raw, mixed, sr, skip=(), quality="normal", bpm=None, mixed_channels=None):
    skip = set(skip)
    t_start = time.time()
    raw, mixed = raw[: sr * MAX_SECONDS], mixed[: sr * MAX_SECONDS]
    c = band_centres(sr)
    raw_db, mix_db = band_spectrum_db(raw, sr, c), band_spectrum_db(mixed, sr, c)
    same = same_take_score(raw, mixed, sr)
    is_same = same >= SAME_TAKE_MIN
    log(f"same-take score {same:.2f} -> {'same take' if is_same else 'different takes (no time-aligned analysis)'}")

    log("fitting compressor and EQ ...")
    paired = fit_compressor_paired(raw, mixed, sr) if is_same else None
    thr, ratio = paired or fit_compressor(levels_db(raw, sr, True), levels_db(mixed, sr, True))
    comp = {"threshold_db": round(thr, 1), "ratio": ratio, "attack_ms": 8, "release_ms": 120, "knee_db": 0}
    hpf0, lpf0, eq0 = fit_eq(raw_db, mix_db, c)
    base0 = {"hpf": hpf0, "compressor": comp, "eq": eq0}
    log("checking de-essing and saturation ...")
    deess = dict(OFF) if "deesser" in skip else fit_deesser(raw, mixed, sr, base0)
    sat = dict(OFF) if "saturation" in skip else fit_saturation(raw, mixed, sr, comp, deess)
    if not is_same:                       # statistics alone are weak evidence: demand more
        if deess.get("enabled") and deess.get("confidence", 0) < 0.8:
            deess = dict(OFF)
        if sat.get("enabled") and sat.get("confidence", 0) < 0.8:
            sat = dict(OFF)
    pre = {"deesser": deess, "saturation": sat, "compressor": comp}
    hpf, lpf, eq = fit_eq(band_spectrum_db(render(raw, sr, pre), sr, c), mix_db, c)
    if "lpf" in skip:
        lpf = dict(OFF)
    if "hpf" in skip:
        hpf = dict(OFF)
    dry = {**pre, "hpf": hpf, "lpf": lpf, "eq": eq}

    delay = reverb = dict(OFF)
    space = {"status": "skipped (different takes)" if not is_same else "skipped"}
    cand_reverb = None
    if is_same and not ({"delay", "reverb"} <= skip):
        log("checking delay and reverb ...")
        d, r, space = estimate_space(render(raw, sr, dry), mixed, sr)
        delay = dict(OFF) if "delay" in skip else d
        reverb = dict(OFF) if "reverb" in skip else r
        cand_reverb = space.get("reverb_candidate_rejected")

    preset = {"version": 3, "sample_rate": sr,
              "chain": "hpf -> lpf -> gate -> deesser -> saturation -> compressor -> eq -> modulation "
                       "-> delay + reverb (parallel) -> gain -> limiter",
              "hpf": hpf, "lpf": lpf, "gate": dict(OFF), "deesser": deess, "saturation": sat,
              "compressor": comp, "eq": eq, "modulation": dict(OFF), "delay": delay, "reverb": reverb,
              "gain": {"enabled": False, "gain_db": 0.0}, "limiter": dict(OFF)}

    refine_info = {"status": "not run"}
    if is_same and quality != "off":
        cands = {"hpf": [{"enabled": True, "freq_hz": f} for f in (70, 100, 150, 220)],
                 "lpf": [{"enabled": True, "freq_hz": f} for f in (6000, 9000, 13000)]}
        if "gate" not in skip:
            cands["gate"] = gate_candidates(raw, sr)
        if "deesser" not in skip and not _on(preset, "deesser"):
            d0 = fit_deesser(raw, mixed, sr, dry, force=True)
            cands["deesser"] = [{**d0, "threshold_db": round(d0["threshold_db"] + off_, 1), "ratio": r_}
                                for off_ in (-4, 0, 4) for r_ in (3.0, 6.0)] if d0.get("enabled") else []
        if "saturation" not in skip and not _on(preset, "saturation"):
            cands["saturation"] = [{"enabled": True, "type": "tanh", "drive": d} for d in (1.25, 1.75, 2.5)]
        if "reverb" not in skip and not _on(preset, "reverb"):
            cands["reverb"] = [{"enabled": True, "predelay_ms": 0, "rt60_s": rt, "wet_db": w, "damping_hz": 8000}
                               for rt in (0.5, 1.2, 2.5) for w in (-20, -14, -9)]
            if cand_reverb:
                cands["reverb"].append({**cand_reverb, "enabled": True})
        refine_info_mod = {}
        if "modulation" not in skip:
            log("checking modulation (chorus/flanger/doubler) ...")
            try:
                rows = track_short_delay(render(raw[: sr * 40], sr, {**preset, "modulation": dict(OFF)}),
                                         mixed[: sr * 40], sr)
                mc, refine_info_mod = modulation_from_tracking(rows)
                if mc:                          # estimated wet level is biased low: try a few
                    cands["modulation"] = [{**c0, "mix": mx} for c0 in mc for mx in
                                           sorted({c0["mix"], 0.4, 0.7, 1.0})]
            except Exception as ex:
                refine_info_mod = {"error": str(ex)}
        log("refining against the mix (analysis-by-synthesis) ...")
        preset, refine_info = refine(raw, mixed, sr, preset, cands, skip, quality)
        refine_info["modulation_tracking"] = refine_info_mod
        for k in OPTIONAL:                      # drop helper-only keys of disabled effects
            if not _on(preset, k):
                preset[k] = dict(OFF)

    # Safe automatic makeup: never hide wildly wrong gain staging with +22 dB.
    y = render(raw, sr, preset)
    requested_gain = 20 * math.log10(loud_rms(mixed, sr) / (loud_rms(y, sr) + 1e-12))
    g = float(np.clip(requested_gain, -12, 8))
    preset["gain"] = {"enabled": True, "gain_db": round(g, 1)}
    preset["gain_staging"] = {"requested_gain_db": round(requested_gain, 1),
                               "applied_gain_db": round(g,1),
                               "limited": bool(abs(g-requested_gain)>0.05),
                               "note": "Output rendering always includes -1 dBTP safety scaling; no loudness forcing."}
    y = render(raw, sr, preset)
    if "limiter" not in skip:
        # A collection of sample peaks near full scale is not enough evidence
        # that the original used a limiter. Don't introduce unnecessary clipping.
        preset["limiter"] = dict(OFF)

    if delay.get("enabled") or _on(preset, "delay"):
        d = preset["delay"]
        if bpm and d.get("enabled"):
            d["note_value"], d["note_error_pct"] = _note_value(d["time_ms"], bpm)

    env_corr = _lag_env_corr(raw[: sr * 40], mixed[: sr * 40], sr)[1]
    pitch = analyze_pitch(raw, mixed, sr) if ((is_same or env_corr >= 0.6) and "pitch" not in skip) else \
        {"status": "skipped" if "pitch" in skip else "skipped (different takes)"}
    stereo = analyze_stereo(mixed_channels, sr) if "stereo" not in skip else {"status": "skipped"}
    preset["pitch"], preset["stereo"] = pitch, stereo

    final = render(raw, sr, preset)
    fin_db = band_spectrum_db(final, sr, c)
    rng = lambda d: round(float(np.ptp(np.percentile(d, [20, 95]))), 1)
    preset["diagnostics"] = {
        "same_take_score": round(same, 2),
        "compressor_fit": "paired-frames (same take)" if paired else "statistics",
        "loudness_range_db": {"raw": rng(levels_db(raw, sr)), "mixed": rng(levels_db(mixed, sr))},
        "spectral_distance_db": {"before": round(spectral_distance(raw_db, mix_db, c), 2),
                                 "after": round(spectral_distance(fin_db, mix_db, c), 2)},
        "refinement": refine_info, "space": space,
        "seconds": round(time.time() - t_start, 1),
        "notes": ["Pitch correction and stereo are reported but not rendered in previews.",
                  "Check each effect's confidence; low values mean treat as a hint only."],
    }
    return preset


# ---------------------------------------------------------------- export (settings sheet)
def settings_sheet(p):
    s = []
    add = lambda eff, plug, params, note="": s.append({"effect": eff, "plugin_type": plug, "params": params, "note": note})
    if _on(p, "hpf"):
        add("High-pass", "EQ high-pass band", {"freq_hz": p["hpf"]["freq_hz"], "slope_db_oct": 12})
    if _on(p, "lpf"):
        add("Low-pass", "EQ low-pass band", {"freq_hz": p["lpf"]["freq_hz"], "slope_db_oct": 12})
    if _on(p, "gate"):
        g = p["gate"]
        add("Gate / expander", "gate (e.g. Pro-G, ReaGate)", {k: g[k] for k in ("threshold_db", "range_db", "ratio", "attack_ms", "release_ms")},
            "threshold is a peak level in dBFS before compression")
    if _on(p, "deesser"):
        d = p["deesser"]
        add("De-esser", "split-band de-esser (e.g. Pro-DS)", {k: d[k] for k in ("freq_hz", "threshold_db", "ratio")},
            "threshold is the band level in dBFS; set so it only bites on S sounds")
    if _on(p, "saturation"):
        a = p["saturation"]
        add("Saturation", "tube/tape/soft-clip saturator", {"drive": a["drive"], "amount": a.get("amount")},
            "tanh soft clipper; drive 1-2 light, 3 medium, 5+ heavy; keep output level matched")
    if p.get("compressor"):
        k = p["compressor"]
        add("Compressor", "peak-detecting compressor", {x: k[x] for x in ("threshold_db", "ratio", "attack_ms", "release_ms")}, "hard knee")
    for b in p.get("eq", []):
        if abs(b["gain_db"]) >= 0.5:
            add("EQ band " + b["name"], {"lowshelf": "low shelf", "highshelf": "high shelf", "peaking": "bell"}[b["type"]],
                {"freq_hz": b["freq_hz"], "gain_db": b["gain_db"], "q": b["q"]})
    if _on(p, "modulation"):
        m = p["modulation"]
        add("Modulation: " + m["type"], m["type"] + " plugin", {k: v for k, v in m.items() if k not in ("enabled", "type")},
            "mix is a linear wet amount added to the dry signal")
    if _on(p, "delay"):
        d = p["delay"]
        prm = {"time_ms": d["time_ms"], "feedback": d["feedback"], "level_db": d["mix_db"]}
        if d.get("note_value"):
            prm["tempo_sync_note"] = d["note_value"]
        add("Delay", "delay (e.g. EchoBoy, ValhallaDelay)", prm, "level is the first echo relative to the dry vocal")
    if _on(p, "reverb"):
        r = p["reverb"]
        add("Reverb", "reverb (e.g. ValhallaVintageVerb, Pro-R)",
            {"decay_s": r["rt60_s"], "predelay_ms": r["predelay_ms"], "wet_level_db": r["wet_db"], "high_cut_hz": r.get("damping_hz")},
            "wet level is the energy of the reverb relative to the dry vocal; use as a send or 100% wet on an aux")
    g = p.get("gain") or {}
    if g.get("enabled") and abs(g["gain_db"]) >= 0.1:
        add("Output gain", "utility", {"gain_db": g["gain_db"]}, "level-matches the preview to the mix")
    if _on(p, "limiter"):
        add("Limiter", "brickwall limiter", {"ceiling_db": p["limiter"]["ceiling_db"]})
    pi = p.get("pitch") or {}
    cr = pi.get("correction") or {}
    if cr.get("detected"):
        add("Pitch correction", "Auto-Tune / Melodyne / Waves Tune",
            {"retune_amount_pct": round(100 * cr["strength"]), "style": cr["style"], "key": pi.get("key_guess"),
             "reference_hz": cr["reference_hz"]}, "retune speed is not estimated; hard style suggests a fast setting")
    elif pi.get("transpose_semitones"):
        add("Pitch shift", "pitch shifter", {"semitones": pi["transpose_semitones"]})
    st = p.get("stereo") or {}
    if st.get("is_stereo") and st.get("notes"):
        add("Stereo image", "widener / Haas / stereo effects",
            {"side_to_mid_db": st["side_to_mid_db"], "haas_delay_ms": st.get("haas_delay_ms")}, "; ".join(st["notes"]))
    return s


def sheet_text(p):
    out = []
    for e in settings_sheet(p):
        prm = ", ".join(f"{k} {v}" for k, v in e["params"].items() if v is not None)
        out.append(f"- {e['effect']} [{e['plugin_type']}]: {prm}" + (f"  ({e['note']})" if e["note"] else ""))
    return "\n".join(out)


# ---------------------------------------------------------------- agent spec
TOOL_SPEC = {
    "name": "vocal_match",
    "description": ("Compare a raw vocal with a mixed (processed) vocal and return a preset that makes the "
                    "raw vocal sound similar: high/low-pass, gate, de-esser, saturation, compressor, 8-band EQ, "
                    "chorus/flanger/phaser/vibrato/tremolo, delay, reverb, output gain, limiter, plus analysis of "
                    "pitch correction, key and stereo width. Effects report enabled + confidence. Time-aligned "
                    "effects need both files to be the same performance."),
    "input_schema": {
        "type": "object",
        "properties": {
            "raw_path": {"type": "string", "description": "Unprocessed vocal (wav/flac)."},
            "mixed_path": {"type": "string", "description": "Processed target vocal."},
            "preset_out": {"type": "string", "description": "Optional path to save preset JSON."},
            "render_out": {"type": "string", "description": "Optional WAV preview of raw with the preset."},
            "skip": {"type": "array", "items": {"enum": list(EFFECTS)}, "description": "Effects not to estimate."},
            "quality": {"enum": ["off", "fast", "normal", "high"], "description": "Refinement effort (default normal)."},
            "bpm": {"type": "number", "description": "Optional tempo; adds note values to delay time."},
        },
        "required": ["raw_path", "mixed_path"],
    },
    "cli": "python vocal_match.py analyze {raw_path} {mixed_path} [-o {preset_out}] [--render {render_out}] "
           "[--skip a,b] [--quality normal] [--bpm 120]",
}




def apply_guide(preset, guide):
    """Apply manually known settings. Guide JSON is {"overrides": {"compressor": {...}}}.
    Only supported plugin-mappable processing keys are allowed.
    """
    supported = {"hpf","lpf","gate","deesser","saturation","compressor","eq",
                 "modulation","delay","reverb","gain","limiter"}
    overrides = guide.get("overrides",guide)
    unknown = set(overrides)-supported
    if unknown:
        raise ValueError("unknown guide keys: " + ",".join(sorted(unknown)))
    out = copy.deepcopy(preset)
    for key, val in overrides.items():
        if key=="eq":
            if not isinstance(val,list): raise ValueError("guide eq must be a list")
            lookup={b["name"]:b for b in out.get("eq",[])}
            for band in val:
                if band.get("name") not in lookup: raise ValueError("unknown EQ band: "+str(band.get("name")))
                lookup[band["name"]].update({k:v for k,v in band.items() if k!="name"})
        else:
            if not isinstance(val,dict): raise ValueError("guide keys must contain dict settings")
            out.setdefault(key,{})
            out[key].update(val)
    out.setdefault("diagnostics",{}).setdefault("notes",[]).append("Known screenshot / preset settings are human-supplied; never auto-inferred.")
    return out

# ---------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("raw"); a.add_argument("mixed")
    a.add_argument("-o", "--out"); a.add_argument("--render")
    a.add_argument("--skip", default="", help="comma list: " + ",".join(EFFECTS))
    a.add_argument("--quality", default="normal", choices=["off", "fast", "normal", "high"])
    a.add_argument("--bpm", type=float)
    a.add_argument("--guide", help="JSON guide of verified preset settings to override auto-estimates")
    a.add_argument("--render-stereo", action="store_true", help="render modeled L/R reverb, not exact stereo reconstruction")
    p = sub.add_parser("apply")
    p.add_argument("raw"); p.add_argument("preset"); p.add_argument("out")
    p.add_argument("--target", help="mixed file; reports spectral distance")
    p.add_argument("--stereo", action="store_true", help="render modeled L/R reverb, not exact stereo reconstruction")
    e = sub.add_parser("export")
    e.add_argument("preset"); e.add_argument("--format", default="json", choices=["json", "text"])
    sub.add_parser("schema")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "schema":
            print(json.dumps(TOOL_SPEC, indent=2))
        elif args.cmd == "analyze":
            skip = {s.strip() for s in args.skip.split(",") if s.strip()}
            bad = skip - set(EFFECTS)
            if bad:
                raise ValueError(f"unknown effect(s) in --skip: {sorted(bad)}")
            raw, sr, _ = load(args.raw)
            mixed, sr2, mch = load(args.mixed)
            mixed, mch = match_rate(mixed, sr2, sr), match_rate(mch, sr2, sr)
            preset = analyze(raw, mixed, sr, skip, args.quality, args.bpm, mch)
            if args.guide:
                with open(args.guide,encoding="utf-8") as fh:
                    preset = apply_guide(preset,json.load(fh))
            if args.out:
                json.dump(preset, open(args.out, "w"), indent=2)
            if args.render:
                save(args.render, render_stereo(raw, sr, preset) if args.render_stereo else render(raw, sr, preset), sr)
            print(json.dumps(preset, indent=2, default=float))
        elif args.cmd == "apply":
            raw, sr, _ = load(args.raw)
            preset = json.load(open(args.preset))
            out = render_stereo(raw, sr, preset) if args.stereo else render(raw, sr, preset)
            save(args.out, out, sr)
            res = {"rendered": args.out}
            if args.target:
                mixed, sr2, _ = load(args.target)
                mixed = match_rate(mixed, sr2, sr)
                c = band_centres(sr)
                res["spectral_distance_db"] = round(spectral_distance(
                    band_spectrum_db(out.mean(axis=1) if out.ndim == 2 else out, sr, c), band_spectrum_db(mixed, sr, c), c), 2)
            print(json.dumps(res, indent=2))
        elif args.cmd == "export":
            pr = json.load(open(args.preset))
            print(json.dumps({"settings": settings_sheet(pr)}, indent=2, default=float)
                  if args.format == "json" else sheet_text(pr))
    except Exception as ex:
        print(json.dumps({"error": f"{type(ex).__name__}: {ex}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
