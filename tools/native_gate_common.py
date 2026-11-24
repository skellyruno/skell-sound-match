"""Identity and transport checks shared by native gate fitting and replay."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import soundfile as sf


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audio_snapshot(path):
    payload = Path(path).read_bytes()
    x, sr = sf.read(io.BytesIO(payload), dtype='float32', always_2d=True)
    if not len(x) or x.shape[1] not in (1, 2) or not 8000 <= sr <= 192000 or not np.isfinite(x).all():
        raise ValueError('Expected finite nonempty mono/stereo audio')
    return np.repeat(x, 2, axis=1) if x.shape[1] == 1 else x, sr, hashlib.sha256(payload).hexdigest()


def training_trim(source, target):
    """Calibrate voiced samples without treating quiet vocals as silence."""
    peak = np.max(np.abs(source), axis=1)
    maximum = float(np.max(peak))
    if maximum <= 1e-7:
        raise ValueError('Insufficient active training signal for gate matching')
    active = peak > max(min(.05, maximum * .2), 1e-7)
    a, b = source[active].astype(np.float64), target[active].astype(np.float64)
    gain = float(np.sum(a * b) / np.sum(a * a))
    if not np.isfinite(gain) or gain <= 0:
        raise ValueError('Training target has no positive aligned gain')
    return float(np.clip(20 * np.log10(gain), -24, 24))


class NativeRenderer:
    def __init__(self, executable, expected_hash=None):
        self.path = Path(executable).resolve()
        self.sha256 = digest(self.path)
        if expected_hash is not None and expected_hash != self.sha256:
            raise ValueError('Renderer binary differs')
        if subprocess.check_output([str(self.path), '--version'], text=True, timeout=10).strip() != 'club-gate-v1':
            raise ValueError('Wrong renderer version')
        self.check_identity()

    def check_identity(self):
        if digest(self.path) != self.sha256:
            raise ValueError('Renderer binary changed during operation')

    def render(self, source, sr, parameters, finish, input_db=0., output_db=0., block=256):
        self.check_identity()
        bounds = ((-75, -15), (.5, 25), (0, 250), (20, 600), (0, 12))
        if (len(parameters) != 5 or not all(np.isfinite(v) and lo <= v <= hi for v, (lo, hi) in zip(parameters, bounds)) or
                type(sr) is not int or not 8000 <= sr <= 192000 or
                type(block) is not int or not 1 <= block <= 8192 or
                type(finish) not in (int, bool) or finish not in (0, 1) or
                not all(np.isfinite(v) and -24 <= v <= 24 for v in (input_db, output_db))):
            raise ValueError('Invalid native gate parameters')
        x = np.asarray(source, dtype=np.float32)
        if x.ndim != 2 or x.shape[1] != 2 or not len(x) or not np.isfinite(x).all():
            raise ValueError('Invalid renderer source')
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / 'input.f32', Path(td) / 'output.f32'
            x.tofile(a)
            payload = subprocess.check_output([str(self.path), str(a), str(b), str(sr),
                       *[str(float(v)) for v in parameters], str(int(finish)),
                       str(input_db), str(output_db), str(block)], text=True, timeout=60)
            self.check_identity()
            meta = json.loads(payload)
            if b.stat().st_size != x.nbytes:
                raise ValueError('Native renderer output length differs from source')
            z = np.fromfile(b, dtype=np.float32).reshape(x.shape)
        seconds = meta.get('processing_seconds')
        if (type(meta.get('frames')) is not int or meta['frames'] != len(x) or
                type(meta.get('latency_samples')) is not int or meta['latency_samples'] != 0 or
                not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or
                not np.isfinite(seconds) or seconds < 0 or not np.isfinite(z).all()):
            raise ValueError('Invalid native renderer output metadata or samples')
        return z, meta
