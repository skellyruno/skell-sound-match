"""Read the explicitly observed FL Studio 26.1.6 project prefix only.

Not a complete FLP parser. Event 156 encodes milli-BPM. The observed version
uses a three-byte event-172 payload in this header sequence. Reject unknown
layouts instead of scanning opaque plug-in payloads for plausible numbers.
"""
import struct


def tempo_prefix(raw):
    if not isinstance(raw, bytes) or not 64 <= len(raw) <= 128 * 1024 * 1024:
        raise ValueError('invalid project size')
    if (raw[:4] != b'FLhd' or struct.unpack_from('<I', raw, 4)[0] != 6
            or struct.unpack_from('<H', raw, 8)[0] != 0
            or raw[14:18] != b'FLdt' or struct.unpack_from('<I', raw, 18)[0] != len(raw)-22):
        raise ValueError('invalid project envelope')
    pos = 22

    def fixed(event, n):
        nonlocal pos
        if pos+n+1 > len(raw) or raw[pos] != event:
            raise ValueError('unexpected prefix event')
        data = raw[pos+1:pos+n+1]
        pos += n+1
        return data

    def variable(event):
        nonlocal pos
        if pos >= len(raw) or raw[pos] != event:
            raise ValueError('unexpected prefix event')
        pos += 1
        n = 0
        for i in range(3):
            if pos >= len(raw):
                raise ValueError('truncated length')
            v = raw[pos]
            pos += 1
            n |= (v & 127) << (7*i)
            if v < 128:
                break
        else:
            raise ValueError('oversized prefix length')
        if n < 1 or n > 4096 or pos+n > len(raw):
            raise ValueError('invalid prefix length')
        data = raw[pos:pos+n]
        pos += n
        return data

    version = variable(199)
    if version != b'26.1.6.5639\0' or struct.unpack('<I', fixed(159, 4))[0] != 5639:
        raise ValueError('unsupported project version')
    fixed(169, 4)
    fixed(28, 1)
    if fixed(172, 3) != b'\x01\x01\x00':
        raise ValueError('unsupported modern prefix flag')
    for event in (192, 200):
        if event == 200:
            fixed(37, 1)
        data = variable(event)
        if len(data)%2 or data[-2:] != b'\0\0':
            raise ValueError('invalid UTF-16 prefix string')
        try:
            data[:-2].decode('utf-16le')
        except UnicodeDecodeError as exc:
            raise ValueError('invalid prefix string') from exc
    tempo = struct.unpack('<I', fixed(156, 4))[0]
    if not 10000 <= tempo <= 522000:
        raise ValueError('invalid saved tempo')
    fixed(67, 2)
    fixed(9, 1)
    fixed(11, 1)
    return tempo / 1000.0
