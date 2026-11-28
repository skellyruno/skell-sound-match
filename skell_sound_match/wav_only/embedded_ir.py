"""Recover embedded stereo WAV impulse responses from local preset containers.

No preset bytes or impulse responses are stored by this module. This is offline
research: the container does not specify the host plugin's mix or IR routing.
"""
from dataclasses import dataclass
from io import BytesIO
import struct
import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class EmbeddedIR:
    offset: int
    sample_rate: int
    samples: np.ndarray


def recover_stereo_ir(data: bytes, max_bytes: int = 32 * 1024 * 1024) -> list[EmbeddedIR]:
    """Scan bounded RIFF/WAVE chunks; skip malformed, mono, and silent assets."""
    if not isinstance(data, bytes) or max_bytes < 44 or len(data) > max_bytes:
        raise ValueError('Invalid or oversized preset container')
    found = []
    cursor = 0
    while True:
        i = data.find(b'RIFF', cursor)
        if i < 0:
            break
        cursor = i + 4
        if i + 12 > len(data) or data[i+8:i+12] != b'WAVE':
            continue
        size = struct.unpack_from('<I', data, i+4)[0] + 8
        if size < 44 or i + size > len(data):
            continue
        try:
            with sf.SoundFile(BytesIO(data[i:i+size])) as handle:
                if handle.channels != 2 or not 8000 <= handle.samplerate <= 192000 or not 0 < handle.frames <= handle.samplerate * 30:
                    continue
                rate = handle.samplerate
                samples = handle.read(dtype='float64', always_2d=True)
        except (ValueError, RuntimeError, OSError):
            continue
        if not np.isfinite(samples).all() or np.max(np.abs(samples)) == 0:
            continue
        samples.setflags(write=False)
        found.append(EmbeddedIR(i, rate, samples))
        cursor = i + size
    return found
