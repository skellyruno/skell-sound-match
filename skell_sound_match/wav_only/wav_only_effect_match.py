#!/usr/bin/env python3
"""Offline, source-only effect reconstruction from SAME-TAKE stage WAV exports.

Fits a causal linear wet-only transfer model for (A) stereo feedback delay
and (B) time-invariant reverb. No plugin settings or private waveforms are
embedded in the code. Uses a disjoint holdout for evaluation, not fitting.

IMPORTANT: NOT a chorus, Flangus, full plugin chain, native VST3, or a
certified true-peak limiter. Learned FIRs are audio-specific experiments.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import fft, linalg, signal

DEFAULT_DELAY_OFFSETS = tuple(range(-64, 97, 8))


def file_hash(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def read_audio(p: Path):
    x, sr = sf.read(p, always_2d=True, dtype='float64')
    if sr < 32000 or sr > 192000 or x.shape[1] not in (1, 2) or len(x) < 2 * sr:
        raise ValueError('Expected 2+ seconds of 32–192 kHz mono/stereo audio')
    if not np.isfinite(x).all():
        raise ValueError('Input contains nonfinite audio')
    return x, sr


def check_mono_compatible(x: np.ndarray) -> np.ndarray:
    if x.ndim != 2 or x.shape[1] not in (1, 2):
        raise ValueError('Expected [frames, 1 or 2 channels]')
    mono = x.mean(axis=1)
    if x.shape[1] == 2:
        ratio = math.sqrt(float(np.mean((x[:, 0] - x[:, 1]) ** 2))) / max(
            math.sqrt(float(np.mean(mono ** 2))), 1e-12)
        if ratio > 0.0178:  # -35 dB: avoid silently discarding stereo input
            raise ValueError('Source is not effectively mono; multi-input fitting required')
    return mono


def windows_ok(train, hold, sr, length):
    a, b = [int(round(float(v) * sr)) for v in train]
    c, d = [int(round(float(v) * sr)) for v in hold]
    if not (0 <= a < b <= c < d <= length) or b - a < sr or d - c < sr:
        raise ValueError('Need ordered, separate >=1s train/holdout within recording')
    return (a, b), (c, d)


def delayed_basis(x: np.ndarray, idx: np.ndarray, delays, offsets):
    cols = []
    n = len(x)
    for delay in delays:
        for offset in offsets:
            j = idx - delay - offset
            cols.append(np.where((j >= 0) & (j < n), x[j.clip(0, n-1)], 0.0))
    return np.stack(cols, axis=1)


def learn_delay(main: np.ndarray, wet: np.ndarray, sr: int, train,
                delay_range=(0.30, 1.25), repeats=3):
    mono = check_mono_compatible(main)
    a, b = train
    if a < 0 or b > len(main):
        raise ValueError('Bad delay training range')
    # Whole-training-window cross correlation only; holdout is never consulted.
    x = mono[a:b]
    z = wet[a:b]
    low = int(round(delay_range[0] * sr))
    high = int(round(delay_range[1] * sr))
    if low <= 0 or high <= low or high >= len(x):
        raise ValueError('Delay search longer than training window')
    c = [signal.fftconvolve(z[:, ch], x[::-1], mode='full')[len(x)-1:] for ch in range(z.shape[1])]
    # Which channel carries the stronger first echo is learned, not assumed.
    magnitudes = np.stack([np.abs(y[low:high]) for y in c])
    which, at = np.unravel_index(np.argmax(magnitudes), magnitudes.shape)
    first = low + int(at)
    delays = [first * k for k in range(1, repeats + 1)]
    offsets = DEFAULT_DELAY_OFFSETS
    samples = np.arange(a, b, 8, dtype=np.int64)
    X = delayed_basis(mono, samples, delays, offsets)
    Y = wet[samples]
    gram = X.T @ X
    ridge = .0005 * float(np.trace(gram)) / len(gram)
    co = linalg.solve(gram + ridge * np.eye(len(gram)), X.T @ Y, assume_a='pos')
    impulse = np.zeros((delays[-1] + max(offsets) + 1, wet.shape[1]), dtype=np.float64)
    for j, delay in enumerate(delays):
        for k, offset in enumerate(offsets):
            impulse[delay + offset] += co[j * len(offsets) + k]
    meta = {'method': 'causal_echo_tap_fir_ridge', 'first_delay_samples': first,
            'first_delay_ms': 1000 * first / sr, 'echo_delays_ms': [1000*d/sr for d in delays],
            'strongest_echo_channel': int(which), 'taps_per_repeat': len(offsets),
            'repeats': repeats, 'ridge_relative': .0005,
            'stereo_echo_peak_coefficients': [
                [float(v) for v in co[j * len(offsets):(j+1) * len(offsets)].sum(axis=0)]
                for j in range(repeats)]}
    return impulse, meta


def _fit_fir_prefix(mono, wet, end, response_samples, ridge_relative, power_mode):
    """Fit causal wet-only FIR from a PREFIX, never from validation/holdout."""
    X = mono[:end]
    Y = wet[:end]
    nfft = fft.next_fast_len(len(X) + response_samples + 1)
    xf = fft.rfft(X, nfft)
    power = np.abs(xf) ** 2
    # q99.5 is robust to strong tonal bins; max more strongly suppresses noise.
    reference = float(np.percentile(power, 99.5)) if power_mode == 'q99.5' else float(power.max())
    denom = power + ridge_relative * max(reference, 1e-18)
    impulse = np.empty((response_samples, wet.shape[1]), dtype=np.float64)
    for ch in range(wet.shape[1]):
        yf = fft.rfft(Y[:, ch], nfft)
        impulse[:, ch] = fft.irfft(np.conj(xf) * yf / denom, nfft)[:response_samples]
    return impulse


def learn_reverb(main: np.ndarray, wet: np.ndarray, sr: int, train,
                 tail_seconds=1., ridge_relative=.0005):
    mono = check_mono_compatible(main)
    a, b = train
    if a != 0:
        raise ValueError('FIR fitting must train from start t=0 to retain causal context')
    length = int(round(tail_seconds * sr))
    if not 0.05 <= tail_seconds <= 3 or length >= b:
        raise ValueError('Invalid FIR response duration')
    # Inner validation is held WITHIN training. The outer holdout is untouched.
    inner_end = int(round(.70*b))
    inner_val = (int(round(.76*b)), b)
    if inner_val[1]-inner_val[0] < sr//2 or inner_end <= length:
        raise ValueError('Not enough source training for causal inner-validation')
    decisions=[]
    for mode in ('max','q99.5'):
        h=_fit_fir_prefix(mono,wet,inner_end,length,ridge_relative,mode)
        pred=render_wet(main,h)
        m=wet_metrics(wet,pred,inner_val)
        decisions.append((m['wet_relative_rms_error'], mode))
    score, selected=min(decisions)
    impulse=_fit_fir_prefix(mono,wet,b,length,ridge_relative,selected)
    return impulse, {'method': 'causal_regularized_fir_system_identification',
                     'tail_seconds': tail_seconds, 'impulse_samples': length,
                     'ridge_relative': ridge_relative,
                     'selected_spectral_regularizer': selected,
                     'within_training_validation_errors': {mode: float(err) for err,mode in decisions},
                     'inner_validation_range_s': [inner_val[0]/sr,inner_val[1]/sr],
                     'limitation': 'LTI impulse approximation; modulation and nonlinear effects not identified'}


def render_wet(main: np.ndarray, impulse: np.ndarray):
    mono = check_mono_compatible(main)
    if impulse.ndim != 2 or impulse.shape[1] != main.shape[1] or not np.isfinite(impulse).all():
        raise ValueError('Bad impulse shape or nonfinite coefficients')
    return np.stack([signal.fftconvolve(mono, impulse[:, ch], mode='full')[:len(main)]
                     for ch in range(main.shape[1])], axis=1)


def wet_metrics(wet, predicted, interval):
    a, b = interval
    r, p = wet[a:b], predicted[a:b]
    denom = math.sqrt(float(np.mean(r*r)))
    if denom <= 1e-10:
        raise ValueError('Wet target too quiet to score')
    err = math.sqrt(float(np.mean((r-p)**2))) / denom
    corr = float(np.corrcoef(r.reshape(-1), p.reshape(-1))[0, 1]) if np.std(p) > 1e-12 else None
    return {'wet_relative_rms_error': err, 'improvement_over_zero_wet_pct': 100*(1-err),
            'wet_rms_dbfs': 20*math.log10(max(denom, 1e-12)),
            'wet_correlation': corr}


def true_peak_estimate(x: np.ndarray):
    # Estimate only: 4x polyphase reconstruction, chunked to cap memory.
    peak = 0.
    span = 220500
    pad = 256
    for i in range(0, len(x), span):
        left, right = max(0, i-pad), min(len(x), i+span+pad)
        hi = signal.resample_poly(x[left:right], 4, 1, axis=0)
        lo = (i-left)*4
        up = (min(i+span,len(x))-left)*4
        peak = max(peak,float(np.max(np.abs(hi[lo:up]))))
    return 20*math.log10(max(peak,1e-12))


def safe_preview(y: np.ndarray, target_dbtp=-1.2):
    before = true_peak_estimate(y)
    trim = min(0., target_dbtp - before)
    out = y * (10**(trim/20))
    if not np.isfinite(out).all() or np.max(np.abs(out)) >= 1:
        raise ValueError('Unsafe preview')
    return out, {'estimated_true_peak_pretrim_dbtp': before, 'safety_trim_db': trim,
                 'estimated_true_peak_posttrim_dbtp': true_peak_estimate(out)}


def train_effect(main_path: Path, effect_path: Path, method, train, holdout,
                 response_seconds=1., delay_range=(.30, 1.25)):
    main,sr=read_audio(main_path)
    target,sr2=read_audio(effect_path)
    if sr != sr2 or main.shape != target.shape:
        raise ValueError('Same-take stage exports must match sample rate, length, channels')
    t, h = windows_ok(train, holdout, sr, len(main))
    wet = target - main
    if method == 'delay':
        impulse, method_data = learn_delay(main, wet, sr, t, delay_range)
    elif method in ('reverb', 'linear_fir'):
        impulse, method_data = learn_reverb(main, wet, sr, t, response_seconds)
        if method == 'linear_fir':
            method_data['limitation'] = 'Static linear approximation only; cannot recreate the changing LFO/modulation or dynamic convolution behavior'
    else:
        raise ValueError('Only delay and linear time-invariant FIR stages supported')
    predicted_wet = render_wet(main, impulse)
    scores = {'train': wet_metrics(wet,predicted_wet,t),
              'holdout': wet_metrics(wet,predicted_wet,h)}
    return impulse, {'schema':'skelly.wav-only.fx-identification.v1','status':'experimental_offline_only',
                     'source_main':main_path.name, 'effect_print':effect_path.name,
                     'source_sha256':file_hash(main_path),'effect_sha256':file_hash(effect_path),
                     'sample_rate':sr,'frame_count':len(main),'channels':main.shape[1],
                     'fit_range_s':train,'unseen_holdout_range_s':holdout,
                     'kind':method,'parameters':method_data,'scores':scores,
                     'audio_origin':'named same-take stage renders; original FL plugin identity not verified',
                     'holdout_better_than_no_wet':bool(scores['holdout']['wet_relative_rms_error']<1.0),
                     'limitations':['No original plugin/preset state','Same-take temporal holdout only, not new-performance proof',
                                    'Not native realtime DSP or verified FL Studio state','Impulse responses are trial models, not proprietary impulse captures']}


def write_model_and_preview(main_path, effect_path, method, train, holdout, model_path,
                            report_path, output_path, response_seconds=1., delay_range=(.30,1.25)):
    paths=[Path(x).resolve() for x in (main_path,effect_path,model_path,report_path,output_path)]
    if len(set(paths))!=len(paths):
        raise ValueError('Input/output file collision')
    if any(Path(x).exists() for x in (model_path,report_path,output_path)):
        raise FileExistsError('Refusing to overwrite model, report or output')
    impulse, report = train_effect(Path(main_path),Path(effect_path),method,train,holdout,response_seconds,delay_range)
    main,sr=read_audio(Path(main_path))
    trial=main + render_wet(main,impulse)
    audition, safety = safe_preview(trial)
    report['preview_safety'] = safety
    report['preview_name'] = Path(output_path).name
    for path in (model_path,report_path,output_path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
    # npz contains ONLY learned filter coefficients, not raw source/target audio.
    np.savez_compressed(model_path,impulse=impulse,sample_rate=np.array(sr))
    sf.write(output_path,audition,sr,subtype='PCM_24')
    report_path=Path(report_path)
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return report


def apply_model(main_path, model_path, output_path):
    if Path(output_path).exists() or Path(main_path).resolve()==Path(output_path).resolve():
        raise FileExistsError('Refusing to replace source or output')
    main,sr=read_audio(Path(main_path))
    with np.load(model_path) as mod:
        coeffs=np.array(mod['impulse'])
        expected_sr=int(mod['sample_rate'])
    if sr!=expected_sr:
        raise ValueError('Model sample rate mismatch')
    audio,safety = safe_preview(main+render_wet(main,coeffs))
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    sf.write(output_path,audio,sr,subtype='PCM_24')
    return safety


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    fit=sub.add_parser('fit',help='fit WAV-only wet effect and print holdout error')
    fit.add_argument('dry_main',type=Path);fit.add_argument('effect_print',type=Path)
    fit.add_argument('--kind',choices=('delay','reverb','linear_fir'),required=True)
    fit.add_argument('--train',type=float,nargs=2,required=True)
    fit.add_argument('--holdout',type=float,nargs=2,required=True)
    fit.add_argument('--tail-seconds',type=float,default=1.)
    fit.add_argument('--search-delay',type=float,nargs=2,default=(.3,1.25))
    fit.add_argument('--model',type=Path,required=True)
    fit.add_argument('--report',type=Path,required=True)
    fit.add_argument('--preview',type=Path,required=True)
    apply=sub.add_parser('apply',help='re-render the learned effect on fresh dry-main audio')
    apply.add_argument('dry_main',type=Path);apply.add_argument('model',type=Path)
    apply.add_argument('--preview',type=Path,required=True)
    args=p.parse_args()
    if args.command=='fit':
        result=write_model_and_preview(args.dry_main,args.effect_print,args.kind,
                    tuple(args.train),tuple(args.holdout),args.model,args.report,args.preview,
                    args.tail_seconds,tuple(args.search_delay))
        print(json.dumps({'kind':result['kind'],'parameters':result['parameters'],
                          'scores':result['scores'],'preview_safety':result['preview_safety']},indent=2))
    else:
        print(json.dumps(apply_model(args.dry_main,args.model,args.preview),indent=2))
if __name__=='__main__':main()
