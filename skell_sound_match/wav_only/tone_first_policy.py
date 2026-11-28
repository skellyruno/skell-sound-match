"""Tone-first native candidate ranking; preserve the historical composite metric.
These are engineering heuristics, not a validated perceptual similarity model.
Headroom, latency and reference identity remain independent mandatory gates.
"""
from math import isfinite

REQUIRED = ('score', 'tone', 'env', 'wave_db', 'side')
TARGET = 1.0

def _validate(m):
    if not all(k in m and isfinite(m[k]) for k in REQUIRED):
        raise ValueError('missing or nonfinite measurements')
    if any(m[k] < 0 for k in ('score', 'tone', 'env', 'side')):
        raise ValueError('negative error measurement')

def audible_proxy(m):
    """Existing tone/envelope/side terms without the phase-sensitive residual."""
    _validate(m)
    return m['tone'] + .35*m['env'] + .08*min(m['side'],40.)

def quality(m, old):
    """No hard waveform-difference veto; unchanged composite must improve."""
    return (audible_proxy(m) < audible_proxy(old)-.025
            and m['tone'] <= old['tone']+.15
            and m['env'] <= old['env']+.65
            and m['side'] <= old['side']+1.5
            and m['score'] < old['score']*.995)

def assess(m, old):
    """Keep tone wins in research even when they aren't ready to deploy."""
    p, b = audible_proxy(m), audible_proxy(old)
    return {'tone_improved': m['tone'] < old['tone'],
            'audible_proxy_improved': p < b,
            'waveform_worse': m['wave_db'] > old['wave_db'],
            'quality_pass': quality(m, old),
            'retain_for_repair': m['tone'] < old['tone'] or p < b,
            'target_met': m['score'] <= TARGET}

def ready(m,old,*,peak44,peak48,stress,latency,previous_latency):
    """Final independent safety checks, not release or listening approval."""
    values=(peak44,peak48,stress,latency,previous_latency)
    return (all(isfinite(v) for v in values) and quality(m,old)
            and peak44<=-1 and peak48<=-1 and stress<=0
            and 0<=latency<=previous_latency)
