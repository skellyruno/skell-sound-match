"""Bounded extraction of an explicitly embedded RIFF/WAVE payload.
Pass only an already-validated plugin-stage state (not an arbitrary project).
No filesystem access, opaque parameter interpretation or audio publication.
"""
import struct

MAX_STATE = 16 * 1024 * 1024


def _valid_wave(data):
    if len(data) < 44 or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        return False
    if struct.unpack_from('<I', data, 4)[0] + 8 != len(data):
        return False
    pos = 12; fmt = 0; audio = 0
    while pos < len(data):
        if pos + 8 > len(data):
            return False
        tag = data[pos:pos+4]; n = struct.unpack_from('<I', data, pos+4)[0]
        start = pos + 8; end = start + n
        if end > len(data):
            return False
        if tag == b'fmt ':
            fmt += 1
            if n < 16 or fmt != 1:
                return False
            _, channels, rate = struct.unpack_from('<HHI', data, start)
            if not 1 <= channels <= 8 or not 8000 <= rate <= 192000:
                return False
        if tag == b'data':
            audio += 1
            if not n or audio != 1:
                return False
        pos = end + (n & 1)
        # Some writers omit the terminal pad of an odd-sized final chunk.
        if end == len(data):
            pos = end
    return pos == len(data) and fmt == audio == 1


def extract_embedded_wave(state):
    """Return exactly one structurally valid WAVE byte sequence; reject ambiguity.

    This does not verify codec contents, the sample data or the stage's identity.
    Decode and check those separately with a trusted audio reader.
    """
    if not isinstance(state, bytes) or not 44 <= len(state) <= MAX_STATE:
        raise ValueError('invalid stage size')
    pos = 0; found = None
    while True:
        i = state.find(b'RIFF', pos)
        if i < 0:
            break
        pos = i + 4
        if i + 12 > len(state) or state[i+8:i+12] != b'WAVE':
            continue
        n = struct.unpack_from('<I', state, i+4)[0] + 8
        if not 44 <= n <= len(state)-i:
            continue
        data = state[i:i+n]
        if not _valid_wave(data):
            continue
        if found is not None:
            raise ValueError('ambiguous embedded WAVE payloads')
        found = data
        pos = i + n
    if found is None:
        raise ValueError('no complete embedded WAVE payload')
    return found
