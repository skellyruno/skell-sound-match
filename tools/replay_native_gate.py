"""Reproduce a selected native fit on the same input, checking recorded identities."""
import argparse
import hashlib
import json
import pathlib
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from native_gate_common import NativeRenderer, audio_snapshot, digest


def replay(renderer, source, report, output, index=None):
    out = pathlib.Path(output)
    if out.exists():
        raise FileExistsError(out)
    data = json.loads(pathlib.Path(report).read_text())
    if data.get('schema') != 'skell.native-gate-fit.v1':
        raise ValueError('Wrong report schema')
    engine = NativeRenderer(renderer, expected_hash=data['renderer_sha256'])
    x, sr, source_hash = audio_snapshot(source)
    if source_hash != data['raw_sha256']:
        raise ValueError('Source differs')
    if sr != data['sample_rate'] or len(x) != data['frames']:
        raise ValueError('Source geometry differs')
    idx = data['selected_index'] if index is None else index
    if type(idx) is not int or not 0 <= idx < len(data['results']):
        raise ValueError('Invalid candidate index')
    r = data['results'][idx]
    parameters = [r['parameters'][k] for k in ('threshold_db', 'attack_ms', 'hold_ms', 'release_ms', 'hysteresis_db')]
    z, _ = engine.render(x, sr, parameters, r['finish'], data['input_db'], r['output_db'], data['block_size'])
    if hashlib.sha256(z.tobytes()).hexdigest() != r['render_sha256']:
        raise ValueError('Render does not reproduce selected candidate')
    if np.max(abs(resample_poly(z, 4, 1, axis=0))) > 10 ** (-1 / 20):
        raise ValueError('Estimated true peak exceeds -1 dBTP')
    if digest(source) != source_hash:
        raise ValueError('Source changed during replay')
    with out.open('xb') as f:
        sf.write(f, z, sr, format='WAV', subtype='FLOAT')
    return r['render_sha256']


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('renderer'); p.add_argument('source'); p.add_argument('report'); p.add_argument('output'); p.add_argument('--index', type=int)
    a = p.parse_args(); print(replay(a.renderer, a.source, a.report, a.output, a.index))
