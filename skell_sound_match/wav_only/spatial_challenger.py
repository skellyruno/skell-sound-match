"""Causal moving-delay spatial trials fitted on training audio only.

Model weights derived from recordings belong in a private workspace.
"""
import numpy as np
from scipy import optimize, signal
from .vocal_knob_search import Window, _features, _score


def qualifies_against_anchor(candidate, anchor):
    """Screen a composed challenger against the original starting baseline."""
    required = ('score', 'band_mae_db', 'envelope_mae_db', 'width_error_db',
                'lr_correlation_error', 'gain_to_match_db')
    if not all(np.isfinite(candidate[k]) and np.isfinite(anchor[k]) for k in required):
        return False
    return bool(candidate['score'] < anchor['score'] * .98
                and candidate['band_mae_db'] <= min(4.5, anchor['band_mae_db'] + .15)
                and candidate['envelope_mae_db'] <= min(5., anchor['envelope_mae_db'] + .2)
                and candidate['width_error_db'] <= 6.
                and candidate['lr_correlation_error'] <= .2
                and abs(candidate['gain_to_match_db']) <= 2.)


def basis(audio, sr, indices, rate, base, depth):
    mono = audio.mean(axis=1)
    clock = indices / sr
    grid = np.arange(len(audio))
    voices = []
    for phase in (0., np.pi / 2, np.pi):
        delay = sr * (base + depth * np.sin(2 * np.pi * rate * clock + phase))
        voices.append(np.interp(indices - delay, grid, mono, left=0., right=0.))
    return np.column_stack(voices)


def render(audio, sr, model):
    if sr != model['sample_rate'] or not np.isfinite(audio).all():
        raise ValueError('Invalid spatial replay format')
    result = np.empty_like(audio)
    for start in range(0, len(audio), 32768):
        indices = np.arange(start, min(len(audio), start + 32768))
        wet = basis(audio, sr, indices, model['rate'], model['base'], model['depth'])
        for channel in range(2):
            design = np.column_stack((audio[indices, channel], wet))
            result[indices, channel] = design @ np.asarray(model['weights'])[:, channel]
    mid = result.mean(axis=1) * model.get('mid_gain', 1.)
    side = (result[:, 0] - result[:, 1]) * .5 * model.get('side_gain', 1.)
    return np.column_stack((mid + side, mid - side))


def calibrate_energy(audio, target, sr, model, train_end):
    """Calibrate existing moving-path energy using only the training prefix."""
    calibrated = {k: v for k, v in model.items() if k not in ('mid_gain', 'side_gain')}
    prediction = render(audio[:train_end], sr, calibrated)
    reference = target[:train_end]
    def rms(values):
        return float(np.sqrt(np.mean(values * values)))
    for name, a, b, limits in (
        ('mid_gain', prediction.mean(axis=1), reference.mean(axis=1), (.5, 2.)),
        ('side_gain', prediction[:, 0]-prediction[:, 1], reference[:, 0]-reference[:, 1], (.25, 4.)),
    ):
        calibrated[name] = float(np.clip(rms(b) / max(rms(a), 1e-10), *limits))
    return calibrated


def fit(audio, target, sr, train_end, rates=(.2, .45, .8, 1.2)):
    if audio.shape != target.shape or audio.ndim != 2 or audio.shape[1] != 2:
        raise ValueError('Expected same-format stereo pair')
    if not np.isfinite(audio).all() or not np.isfinite(target).all() or train_end < 3 * sr:
        raise ValueError('Invalid spatial training input')
    fit_end = round(train_end * .68)
    indices = np.arange(0, fit_end, 8)
    validation = Window(train_end * .76 / sr, train_end / sr)
    reference = _features(target, sr, validation)
    best = None
    for rate in rates:
        for base in (.008, .018):
            for depth in (.002, .006):
                wet = basis(audio, sr, indices, rate, base, depth)
                weights = []
                for channel in range(2):
                    design = np.column_stack((audio[indices, channel], wet))
                    result = optimize.lsq_linear(design, target[indices, channel], bounds=([0., -2., -2., -2.], [2., 2., 2., 2.]))
                    weights.append(result.x)
                model = dict(sample_rate=sr, rate=rate, base=base, depth=depth, weights=np.column_stack(weights).tolist())
                prediction = render(audio[:train_end], sr, model)
                score = _score(reference, _features(prediction, sr, validation))
                loss = score['score'] + 2 * score['lr_correlation_error']
                if best is None or loss < best[0]:
                    best = loss, model
    return best[1], {'inner_validation_loss': best[0], 'selection': 'training_prefix_only', 'lookahead_samples': 0}
