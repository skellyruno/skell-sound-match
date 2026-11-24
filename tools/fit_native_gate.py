"""Train-prefix-only optimizer for the shared native Club Gate renderer."""
import argparse
import hashlib
import json
import pathlib
import numpy as np
from scipy.optimize import differential_evolution
from scipy.signal import resample_poly
from native_gate_common import NativeRenderer, audio_snapshot, digest, training_trim

ENGINE_REVISION = '92b03b753c59583b6b6063228c2d630ef94daf59'


def fit(renderer, raw, target, report, maxiter=6):
    report = pathlib.Path(report)
    if report.exists():
        raise FileExistsError(report)
    if type(maxiter) is not int or not 0 <= maxiter <= 100:
        raise ValueError('maxiter outside 0..100')
    engine = NativeRenderer(renderer)
    x, sr, raw_hash = audio_snapshot(raw)
    y, yr, target_hash = audio_snapshot(target)
    if x.shape != y.shape or sr != yr:
        raise ValueError('Aligned source and target geometry required')
    n = int(len(x) * .6)
    if min(n, len(x) - n) < sr:
        raise ValueError('Need at least one second per section')

    def score(z, t, s):
        mask = np.max(abs(s), axis=1) >= .005
        return sum(float(np.mean((z[m].astype(np.float64) - t[m]) ** 2) /
                         max(np.mean(s[m].astype(np.float64) ** 2), 1e-10))
                   for m in (mask, ~mask) if m.any())

    trim = training_trim(x[:n], y[:n])
    results = []
    base = [-46, 2, 25, 40, 4]
    for finish in (False, True):
        before, _ = engine.render(x, sr, base, finish, output_db=trim)

        def objective(p):
            return score(engine.render(x[:n], sr, p, finish, output_db=trim)[0], y[:n], x[:n])

        opt = differential_evolution(objective, [(-65, -30), (.5, 10), (0, 80), (20, 160), (0, 8)],
                                     seed=23, popsize=4, maxiter=maxiter, polish=False, x0=base)
        p = opt.x if opt.fun < objective(base) else base
        z, meta = engine.render(x, sr, p, finish, output_db=trim)
        train, later = score(z[:n], y[:n], x[:n]), score(z[n:], y[n:], x[n:])
        before_train, before_later = score(before[:n], y[:n], x[:n]), score(before[n:], y[n:], x[n:])
        block_exact = all(np.array_equal(z, engine.render(x, sr, p, finish, output_db=trim, block=b)[0])
                          for b in (1, 64, 511, 1024))
        peak = float(20 * np.log10(max(np.max(abs(resample_poly(z, 4, 1, axis=0))), 1e-12)))
        eligible = block_exact and peak <= -1 and train <= before_train and later <= before_later
        results.append(dict(finish=finish, parameters=dict(zip(('threshold_db', 'attack_ms', 'hold_ms', 'release_ms', 'hysteresis_db'), map(float, p))),
                            output_db=trim, baseline_train=before_train, baseline_later=before_later,
                            train=train, later=later, block_exact=block_exact, peak_dbtp_estimate=peak,
                            processing_seconds=meta['processing_seconds'], latency_samples=meta['latency_samples'],
                            render_sha256=hashlib.sha256(z.tobytes()).hexdigest(), listening_eligible=eligible,
                            status='EXPERIMENTAL_NATIVE_CHECK_PASS' if eligible else 'REJECTED_VALIDATION'))
    selected = int(np.argmin([r['train'] for r in results]))
    engine.check_identity()
    if digest(raw) != raw_hash or digest(target) != target_hash:
        raise ValueError('Source or target changed during fitting')
    out = dict(schema='skell.native-gate-fit.v1', fit_revision='quiet-trim-and-render-integrity-v2',
               expected_core_revision=ENGINE_REVISION, renderer_version='club-gate-v1', input_db=0,
               block_size=256, raw_sha256=raw_hash, target_sha256=target_hash, renderer_sha256=engine.sha256,
               sample_rate=sr, frames=len(x), train_frames=n, selection='train prefix only; later same-take diagnostic',
               results=results, selected_index=selected, listening_eligible=results[selected]['listening_eligible'])
    with report.open('x') as f:
        json.dump(out, f, indent=2, allow_nan=False)
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('renderer'); p.add_argument('raw'); p.add_argument('target'); p.add_argument('report'); p.add_argument('--maxiter', type=int, default=6)
    a = p.parse_args(); print(json.dumps(fit(a.renderer, a.raw, a.target, a.report, a.maxiter), indent=2))
