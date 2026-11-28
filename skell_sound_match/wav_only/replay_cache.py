"""Private offline replay cache keyed by exact input and dependency namespace.
Do not use from an audio callback. The caller must supply a content-addressed
namespace covering all transitive recipe/code dependencies. Never cache target
waveforms with this helper; cached arrays are private dry-input renders.
"""
from pathlib import Path
import hashlib
import os
import tempfile
import zipfile
import numpy as np


def replay_key(namespace, case_id, stage, samples, rate):
    if not all(isinstance(v, str) and v for v in (namespace, case_id, stage)):
        raise ValueError('missing replay identity')
    if type(rate) is not int or not 8000 <= rate <= 192000:
        raise ValueError('invalid sample rate')
    x = np.ascontiguousarray(samples, dtype=np.float32)
    if x.ndim != 2 or x.shape[1] != 2 or not len(x) or not np.isfinite(x).all():
        raise ValueError('expected finite nonempty stereo audio')
    h = hashlib.sha256()
    for value in (namespace, case_id, stage, str(rate), str(x.shape)):
        b = value.encode('utf-8'); h.update(len(b).to_bytes(8, 'little')); h.update(b)
    h.update(memoryview(x).cast('B'))
    return h.hexdigest(), x


def cached_replay(directory, namespace, case_id, stage, samples, rate, render):
    """Return a validated private cached render or atomically publish a new one.

    One archive stores the key, shape, payload and checksum together; concurrent
    writers may duplicate work but cannot publish a partial archive. Corrupt
    entries are ignored. Caller owns eviction and private directory lifecycle.
    """
    key, x = replay_key(namespace, case_id, stage, samples, rate)
    d = Path(directory); d.mkdir(parents=True, exist_ok=True)
    path = d / (key + '.npz')
    def digest(y):
        return hashlib.sha256(memoryview(np.ascontiguousarray(y)).cast('B')).hexdigest()
    def valid(y):
        return y.shape == x.shape and y.dtype == np.float32 and np.isfinite(y).all()
    try:
        with np.load(path, allow_pickle=False) as f:
            y = f['samples']
            if str(f['key']) == key and valid(y) and str(f['sha256']) == digest(y):
                return y
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
        pass
    y = np.ascontiguousarray(render(x, rate), dtype=np.float32)
    if not valid(y):
        raise ValueError('invalid replay output')
    fd, tmp = tempfile.mkstemp(prefix=key + '.', suffix='.tmp', dir=d)
    try:
        with os.fdopen(fd, 'wb') as f:
            np.savez(f, samples=y, key=key, sha256=digest(y))
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return y
