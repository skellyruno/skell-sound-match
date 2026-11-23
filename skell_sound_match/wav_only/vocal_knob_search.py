"""Source-only, bounded stereo vocal knob search for offline Sound Match trials.

Method informed by reviewing owner-supplied vox_cloner; no third-party code
is copied (its supplied archive has no explicit reuse license). Takes ideas
from feature optimization, augments with exact-stage pairing, no-leakage
train/holdout windows, deterministic budgets, and a non-promotion quality gate.

Not real-time-safe JUCE DSP. A better score does not mean an approved sound.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

from .stereo_finish_audit import finish_stereo, estimate_true_peak_db

# Restrained search: older dry-input reconstruction remains an immutable baseline.
# FX mode is exploratory and requires the optional 'pedalboard' dependency.
KNOBS = {
    "presence_db": (-3.0, 3.0, 0.0),
    "upper_presence_db": (-3.0, 3.0, 0.0),
    "air_db": (-4.0, 4.0, 0.0),
    "side_gain": (0.65, 1.8, 1.0),
}
FX_KNOBS = {
    "comp_threshold_db": (-30.0, -10.0, -18.0),
    "comp_ratio": (1.0, 4.0, 1.0),
    "chorus_mix": (0.0, 0.35, 0.0),
    "chorus_depth": (0.0, 0.65, 0.0),
    "delay_mix": (0.0, 0.23, 0.0),
    "reverb_wet": (0.0, 0.30, 0.0),
}
BANDS = ((80, 160), (160, 350), (350, 700), (700, 1600),
         (1600, 4000), (4000, 8000), (8000, 14000))


@dataclass(frozen=True)
class Window:
    start: float
    end: float


@dataclass(frozen=True)
class Trial:
    params: dict[str, float]
    baseline_train: dict
    trial_train: dict
    baseline_holdout: dict
    trial_holdout: dict
    accepted_for_listening: bool
    evaluation_count: int
    reason: str


def _check_stereo(x: np.ndarray) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2 or not np.all(np.isfinite(a)):
        raise ValueError("Expected finite stereo audio [frames, 2]")
    return a


def _validate_pair(source: np.ndarray, target: np.ndarray, sr: int,
                   train: Window, holdout: Window, pairing: dict) -> tuple[np.ndarray, np.ndarray]:
    x, y = _check_stereo(source), _check_stereo(target)
    if not all(math.isfinite(v) for v in (train.start, train.end, holdout.start, holdout.end)):
        raise ValueError("Window bounds must be finite")
    if sr < 32000 or sr > 192000 or x.shape != y.shape:
        raise ValueError("Same sample rate and exact frame count are required")
    if not isinstance(pairing, dict) or pairing.get("same_take") is not True:
        raise ValueError("Explicit same_take=true evidence is required")
    if not pairing.get("source_stage") or not pairing.get("target_stage") or not pairing.get("take_id"):
        raise ValueError("Take and processing stages must be declared")
    if train.start < 0 or train.end > holdout.start or holdout.end > len(x) / sr:
        raise ValueError("Train and holdout must be ordered and non-overlapping")
    if train.end - train.start < .3 or holdout.end - holdout.start < .3:
        raise ValueError("Windows must be at least 300 ms")
    if (max(abs(x).max(), abs(y).max()) > 6):
        raise ValueError("Input samples suspiciously out of range")
    return x, y


def _features(audio: np.ndarray, sr: int, window: Window) -> dict:
    """Computationally cheap, differentiable-*agnostic* comparison features.

    Input should already be synchronized; no implicit time shifting or hidden
    reference audio is ever applied during rendering. RMS matching makes the
    score insensitive to overall gain, so loudness is audited separately.
    """
    lo, hi = round(window.start * sr), round(window.end * sr)
    x = audio[lo:hi]
    if len(x) < 512:
        raise ValueError("Too little audio")
    # Spectrum: Hann block average on exact same time interval. Summing power
    # before converting to dB keeps quiet bands stable.
    nperseg = min(4096, len(x))
    freqs, power = signal.welch(x, fs=sr, window="hann", nperseg=nperseg,
                                noverlap=nperseg // 2, axis=0)
    power = np.mean(power, axis=1)
    powers = []
    for low, high in BANDS:
        mask = (freqs >= low) & (freqs < min(high, sr * .49))
        powers.append(float(np.sum(power[mask]) * (freqs[1] - freqs[0]) + 1e-14))
    bands_db = 10 * np.log10(powers)
    # 25 ms RMS tracks vocal envelope, 10 ms hop for attack/release comparisons.
    win = max(128, round(sr * .025))
    hop = max(64, round(sr * .010))
    mid = (x[:, 0] + x[:, 1]) / 2
    side = (x[:, 0] - x[:, 1]) / 2
    env = []
    for s in range(0, len(mid) - win + 1, hop):
        env.append(math.sqrt(float(np.mean(mid[s:s + win] ** 2)) + 1e-14))
    env = np.asarray(env)
    rms = math.sqrt(float(np.mean(x ** 2)) + 1e-14)
    mid_rms = math.sqrt(float(np.mean(mid ** 2)) + 1e-14)
    side_rms = math.sqrt(float(np.mean(side ** 2)) + 1e-14)
    centered = x - np.mean(x, axis=0)
    norm = math.sqrt(float(np.sum(centered[:, 0] ** 2) * np.sum(centered[:, 1] ** 2)))
    correlation = float(np.sum(centered[:, 0] * centered[:, 1]) / norm) if norm > 1e-12 else 0.0
    return {"bands_db": bands_db, "env_db": 20 * np.log10(env + 1e-10),
            "rms_db": 20 * math.log10(rms), "lr_correlation": correlation,
            "side_mid_db": max(-40., 20 * math.log10(side_rms / mid_rms)),
            "crest_db": 20 * math.log10(max(float(np.max(np.abs(x))), 1e-12) / rms)}


def _score(ref: dict, candidate: dict) -> dict:
    # Match integrated loudness before comparing shape, like A/B playback.
    gain = ref["rms_db"] - candidate["rms_db"]
    band = float(np.mean(np.abs(candidate["bands_db"] + gain - ref["bands_db"])))
    env = float(np.mean(np.abs(candidate["env_db"] + gain - ref["env_db"])))
    width = abs(candidate["side_mid_db"] - ref["side_mid_db"])
    crest = abs(candidate["crest_db"] - ref["crest_db"])
    # All values in dB; width error is clamped so mono targets don't blow up.
    weighted = .42 * band + .32 * env + .18 * min(width, 20.) + .08 * crest
    return {"score": round(weighted, 6), "band_mae_db": round(band, 6),
            "envelope_mae_db": round(env, 6), "width_error_db": round(width, 6),
            "crest_error_db": round(crest, 6), "gain_to_match_db": round(gain, 6),
            "lr_correlation_error": abs(ref["lr_correlation"] - candidate["lr_correlation"])}


def render(source: np.ndarray, sr: int, params: dict[str, float], *, effects: bool = False) -> np.ndarray:
    """No target-dependent mixing; optional real Pedalboard FX chain.

    Preserves the candidate's existing stereo channel information. Mono source
    does not acquire fictional width in finishing mode.
    """
    x = _check_stereo(source)
    for name, (lo, hi, _) in (KNOBS | (FX_KNOBS if effects else {})).items():
        if name not in params or not np.isfinite(params[name]) or not lo <= params[name] <= hi:
            raise ValueError(f"Out-of-range or missing knob: {name}")
    y = finish_stereo(x, sr,
                      presence_db=params["presence_db"],
                      upper_presence_db=params["upper_presence_db"],
                      air_db=params["air_db"], side_gain=params["side_gain"])
    if effects:
        try:
            from pedalboard import Pedalboard, Compressor, Chorus, Delay, Reverb
        except ImportError as exc:
            raise RuntimeError("FX research requires optional pedalboard") from exc
        chain = Pedalboard([
            Compressor(threshold_db=params["comp_threshold_db"],
                       ratio=params["comp_ratio"], attack_ms=8, release_ms=85),
            Chorus(rate_hz=.7, depth=params["chorus_depth"],
                   mix=params["chorus_mix"]),
            Delay(delay_seconds=.24, feedback=.15, mix=params["delay_mix"]),
            Reverb(room_size=.38, damping=.55, wet_level=params["reverb_wet"],
                   dry_level=1 - params["reverb_wet"]),
        ])
        # Pedalboard expects channels by frames as [channels, frames] in this
        # installed version. Explicitly convert instead of accidental mono sum.
        y = np.asarray(chain(y.T.astype(np.float32), sr, reset=True), dtype=np.float64).T
    gain_db = float(params.get("output_gain_db", 0.))
    if not math.isfinite(gain_db) or not -36 <= gain_db <= 18:
        raise ValueError("Invalid calibrated output gain")
    y *= 10 ** (gain_db / 20)
    if y.shape != x.shape or not np.all(np.isfinite(y)):
        raise ValueError("Nonfinite or reshaped rendering")
    return y


def optimize(source: np.ndarray, target: np.ndarray, sr: int, *,
             pairing: dict, train: Window, holdout: Window, seed: int = 17,
             budget: int = 55, effects: bool = False) -> Trial:
    """Search on TRAIN only. Holdout is accessed exactly once after selection.

    The caller's previous candidate is never altered and the private target is
    never mixed into any rendered output. Uses baseline + bounded coordinate
    proposals; no third-party optimizer dependency, deterministic for a seed.
    """
    x, y = _validate_pair(source, target, sr, train, holdout, pairing)
    if not isinstance(budget, int) or not 8 <= budget <= 500 or seed < 0:
        raise ValueError("Invalid search budget or seed")
    specs = KNOBS | (FX_KNOBS if effects else {})
    keys = list(specs)
    bounds = np.array([(specs[k][0], specs[k][1]) for k in keys], dtype=float)
    values = np.array([specs[k][2] for k in keys], dtype=float)
    ref_train = _features(y, sr, train)
    baseline = _score(ref_train, _features(x, sr, train))
    # A non-neutral compressor default may transform signal. Keep *unprocessed*
    # baseline as the quality gate, never an arbitrarily effect-heavy chain.
    best = values.copy()
    best_loss = float("inf")
    rng = np.random.default_rng(seed)
    steps = (bounds[:, 1] - bounds[:, 0]) * .30
    seen: set[tuple[float, ...]] = set()
    count = 0
    # Run full prefix from time zero so reverb/compressor state is initialized.
    prefix = x[:round(train.end * sr)]
    while count < budget:
        if count == 0:
            candidate = values.copy()
        else:
            candidate = best.copy()
            chosen = rng.choice(len(keys), size=(1 if count % 3 else min(2, len(keys))), replace=False)
            candidate[chosen] += rng.normal(0., steps[chosen])
            candidate = np.clip(candidate, bounds[:, 0], bounds[:, 1])
        cachekey = tuple(np.round(candidate, 6))
        if cachekey in seen:
            steps *= .94
            continue
        seen.add(cachekey)
        params = {k: float(z) for k, z in zip(keys, candidate)}
        processed = render(prefix, sr, params, effects=effects)
        loss = _score(ref_train, _features(processed, sr, train))["score"]
        count += 1
        if loss < best_loss:
            best_loss = loss
            best = candidate.copy()
        if count % max(8, budget // 4) == 0:
            steps *= .73
    params = {k: float(z) for k, z in zip(keys, best)}
    # Match actual reference level using TRAIN ONLY; the feature loss itself is
    # RMS-normalized and cannot identify output gain. Never fit gain on holdout.
    best_train = _features(render(prefix, sr, params, effects=effects), sr, train)
    train_output_gain_db = ref_train["rms_db"] - best_train["rms_db"]
    params["output_gain_db"] = float(np.clip(train_output_gain_db, -36., 18.))
    # Evaluate on a completely separate window; never use heldout to choose knobs.
    out = render(x[:round(holdout.end * sr)], sr, params, effects=effects)
    tr = _score(ref_train, _features(out, sr, train))
    ref_holdout = _features(y, sr, holdout)
    original_holdout = _score(ref_holdout, _features(x, sr, holdout))
    trial_holdout = _score(ref_holdout, _features(out, sr, holdout))
    output_peak = estimate_true_peak_db(out)
    # No arbitrary upward gain; output may be trimmed for private listening only.
    peak_ok = math.isfinite(output_peak) and output_peak <= 1.0
    # Unlike the feature score, these are absolute sound-quality requirements:
    # loudness, stereo image and missing broad timbre are not negotiable.
    level_ok = abs(trial_holdout["gain_to_match_db"]) <= 2.0
    width_ok = trial_holdout["width_error_db"] <= 6.0
    phase_ok = trial_holdout["lr_correlation_error"] <= .2
    timbre_ok = trial_holdout["band_mae_db"] <= 4.5
    dynamics_ok = trial_holdout["envelope_mae_db"] <= 5.0
    train_ok = (tr["score"] <= baseline["score"] * .99 and
                baseline["score"] - tr["score"] >= .03)
    hold_ok = (trial_holdout["score"] <= original_holdout["score"] * .99 and
               original_holdout["score"] - trial_holdout["score"] >= .03)
    # Score improvement alone can hide severe envelope or tone damage.
    band_ok = trial_holdout["band_mae_db"] <= max(
        original_holdout["band_mae_db"] * 1.1, original_holdout["band_mae_db"] + .15)
    envelope_ok = trial_holdout["envelope_mae_db"] <= max(
        original_holdout["envelope_mae_db"] * 1.12, original_holdout["envelope_mae_db"] + .2)
    safe = bool(train_ok and hold_ok and band_ok and envelope_ok and peak_ok
                and level_ok and width_ok and phase_ok and timbre_ok and dynamics_ok)
    why = "HELDOUT_PASS_EXPERIMENTAL" if safe else (
        "REJECTED_LOUDNESS_STEREO_OR_CHARACTER" if not (
            level_ok and width_ok and phase_ok and timbre_ok and dynamics_ok) else
        "REJECTED_HELDOUT_OR_ENVELOPE" if train_ok and peak_ok else
        "REJECTED_TRAIN_OR_PEAK")
    return Trial(params, baseline, tr, original_holdout, trial_holdout,
                 safe, count, why)


def stereo_phase_profile(audio: np.ndarray, sr: int | None = None) -> dict:
    """Diagnose when a source-only chain cannot reproduce an antiphase target.

    Reports LR correlation and stereo-to-mono fold-down loss without claiming
    that a simple side-width knob could create the missing moving stereo FX.
    """
    x = _check_stereo(audio)
    a, b = x[:, 0], x[:, 1]
    a0, b0 = a - float(np.mean(a)), b - float(np.mean(b))
    norm = math.sqrt(float(np.dot(a0, a0) * np.dot(b0, b0)))
    corr = float(np.dot(a0, b0) / norm) if norm > 1e-12 else 0.
    mid = (a + b) / 2
    side = (a - b) / 2
    full_rms = math.sqrt(float(np.mean(x*x)) + 1e-18)
    mid_rms = math.sqrt(float(np.mean(mid*mid)) + 1e-18)
    side_rms = math.sqrt(float(np.mean(side*side)) + 1e-18)
    result = {"lr_correlation": round(corr, 6),
            "side_mid_db": round(20 * math.log10(side_rms / mid_rms), 4),
            "mono_fold_down_loss_db": round(20 * math.log10(mid_rms / full_rms), 4),
            "strong_antiphase": bool(corr <= -.25)}
    if sr is not None:
        if not 32000 <= sr <= 192000:
            raise ValueError("Unsupported phase-profile sample rate")
        window = round(sr * .2)
        values = []
        floor = max(float(np.mean(x * x)) * .01, 1e-10)
        for start in range(0, len(x) - window + 1, window):
            block = x[start:start + window]
            if float(np.mean(block * block)) < floor:
                continue
            block = block - np.mean(block, axis=0)
            norm = math.sqrt(float(np.sum(block[:, 0] ** 2) * np.sum(block[:, 1] ** 2)))
            if norm > 1e-12:
                values.append(float(np.sum(block[:, 0] * block[:, 1]) / norm))
        result["active_200ms_correlation"] = {
            "windows": len(values), "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "median": float(np.median(values)) if values else None,
        }
    return result


def fif_ears_signal_snapshot(audio: np.ndarray, sr: int) -> dict:
    """OPTIONAL public fif-ears signal-layer analysis, not tempo/key detection.

    Imports a separately installed fif-ears distribution, not vendored code.
    A snapshot is diagnostic only and is never used to select knob settings.
    """
    try:
        from ears.audio import AudioData
        from ears.layers.signal import analyze as signal_analyze
    except ImportError as exc:
        raise RuntimeError("Install fif-ears separately for --fif-signal") from exc
    x = _check_stereo(audio).astype(np.float32)
    mid = ((x[:, 0].astype(np.float64) + x[:, 1]) / 2).astype(np.float32)
    record = AudioData(mono=mid, left=x[:, 0].copy(), right=x[:, 1].copy(),
                       sample_rate=sr, channels=2, duration=len(x) / sr)
    result = signal_analyze(record)
    if result.get("status") != "ok":
        raise RuntimeError("fif-ears signal layer did not finish")
    # Explicitly exclude rhythm, key, harmony, lyrics and personal metadata.
    return {"tool": "fif-ears", "layer": "signal", "status": "ok",
            "signal": result}


def run_files(source_path: Path, target_path: Path, output_dir: Path, *,
              pairing: dict, train: Window, holdout: Window,
              seed: int = 17, budget: int = 55, effects: bool = False,
              fif_signal: bool = False) -> dict:
    """Private local artifacts only. Refuse overwrites and preserve input hashes."""
    source_path, target_path, output_dir = map(Path, (source_path, target_path, output_dir))
    if source_path.resolve() == target_path.resolve():
        raise ValueError("Source cannot equal reference")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError("Output directory already contains data; preserve previous trials")
    source, sr = sf.read(source_path, dtype="float64", always_2d=True)
    target, target_sr = sf.read(target_path, dtype="float64", always_2d=True)
    if sr != target_sr:
        raise ValueError("Sample rates differ")
    trial = optimize(source, target, sr, pairing=pairing, train=train, holdout=holdout,
                     seed=seed, budget=budget, effects=effects)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Render even rejected experiments for diagnostics; name makes status clear.
    render_audio = render(source, sr, trial.params, effects=effects)
    peak = estimate_true_peak_db(render_audio)
    trim = min(0., -1.5 - peak)
    render_audio *= 10 ** (trim / 20)
    path = output_dir / "experimental_candidate.wav"
    sf.write(path, render_audio, sr, subtype="PCM_24")
    emitted, emitted_sr = sf.read(path, dtype="float64", always_2d=True)
    emitted_score = _score(_features(target, sr, holdout), _features(emitted, sr, holdout))
    emitted_peak = estimate_true_peak_db(emitted)
    emitted_ok = (emitted_sr == sr and np.isfinite(emitted).all()
                  and abs(emitted_score["gain_to_match_db"]) <= 2.0
                  and emitted_peak <= -1.47)
    result = {
        "schema": "skelly.offline-knob-trial.v1", "approved": False,
        "status": trial.reason if emitted_ok else "REJECTED_EMITTED_AUDIO_SAFETY_OR_LEVEL",
        "listening_eligible": bool(trial.accepted_for_listening and emitted_ok),
        "emitted_holdout": emitted_score,
        "emitted_peak_dbtp": emitted_peak,
        "render_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "reference_sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
        "pairing": pairing, "sample_rate": sr,
        "train": vars(train), "holdout": vars(holdout),
        "seed": seed, "budget": budget, "effects": effects,
        "params": trial.params, "baseline_train": trial.baseline_train,
        "trial_train": trial.trial_train,
        "baseline_holdout": trial.baseline_holdout,
        "trial_holdout": trial.trial_holdout,
        "output_peak_pre_trim_dbtp": peak, "output_trim_db": trim,
        "render_name": path.name,
        "third_party_model_used": False,
        "validation_scope": "same_take_holdout_not_independent_performance",
        "stereo_phase": {
            "source": stereo_phase_profile(source, sr),
            "reference": stereo_phase_profile(target, sr),
            "candidate": stereo_phase_profile(render_audio, sr),
        },
    }
    result["requires_antiphase_reconstruction"] = bool(
        result["stereo_phase"]["reference"]["strong_antiphase"] and not
        result["stereo_phase"]["candidate"]["strong_antiphase"])
    if fif_signal:
        # Same-take comparison diagnostic. No key/tempo code is called.
        snapshots = {
            "source": fif_ears_signal_snapshot(source, sr),
            "reference": fif_ears_signal_snapshot(target, sr),
            "candidate": fif_ears_signal_snapshot(render_audio, sr),
        }
        (output_dir / "fif_ears_signal_only.json").write_text(
            json.dumps(snapshots, indent=2), encoding="utf-8")
        result["fif_ears_signal_snapshot"] = "fif_ears_signal_only.json"
    (output_dir / "trial_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline safe feature-guided vocal knob research")
    parser.add_argument("source", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--take-id", required=True)
    parser.add_argument("--source-stage", required=True)
    parser.add_argument("--target-stage", required=True)
    parser.add_argument("--train", nargs=2, type=float, required=True)
    parser.add_argument("--holdout", nargs=2, type=float, required=True)
    parser.add_argument("--budget", type=int, default=55)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--effects", action="store_true")
    parser.add_argument("--fif-signal", action="store_true",
                        help="Use only separately installed fif-ears signal layer; skip tempo/key")
    args = parser.parse_args()
    result = run_files(args.source, args.reference, args.output_dir,
        pairing={"take_id": args.take_id, "same_take": True,
                 "source_stage": args.source_stage, "target_stage": args.target_stage},
        train=Window(*args.train), holdout=Window(*args.holdout),
        budget=args.budget, seed=args.seed, effects=args.effects,
        fif_signal=args.fif_signal)
    print(json.dumps({k: v for k, v in result.items() if k != "params"}, indent=2))


if __name__ == "__main__":
    main()
