"""Safe metadata-only inventory of FL Studio .fst effect-name evidence.

Does not decode proprietary plugin parameters, active/bypass states, or FLP
project routing. User recordings, binary FST/FLP state and file paths stay
private; reports contain only known plugin labels and SHA-256 fingerprints.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import struct
import zipfile

MAX_FST_BYTES = 8_000_000
MAX_ZIP_FILES = 512
MAX_TOTAL_BYTES = 100_000_000
MAX_RATIO = 500
KNOWN_PLUGINS = {
    'Soundgoodizer', 'Maximus', 'Panagement 2', 'Fresh Air',
    'Baby Comeback', 'DeEsser Stereo',
}
PREFIXES = ('Fruity ', 'Waves ', 'Panagement ', 'FabFilter ', 'Valhalla ')
_UTF16_LABEL = re.compile(rb'(?:[\x20-\x7e]\x00){4,}')


def _plugin_label(text: str) -> bool:
    return text in KNOWN_PLUGINS or any(text.startswith(p) for p in PREFIXES)


def inspect_fst(data: bytes, name: str = '') -> dict:
    if len(data) < 22 or len(data) > MAX_FST_BYTES:
        raise ValueError('FST file out of size range')
    if data[:4] != b'FLhd' or struct.unpack_from('<I', data, 4)[0] != 6:
        raise ValueError('Invalid FL Studio header')
    if data[14:18] != b'FLdt' or struct.unpack_from('<I', data, 18)[0] != len(data)-22:
        raise ValueError('Invalid or truncated FL Studio event chunk')
    strings = [m.group().decode('utf-16le') for m in _UTF16_LABEL.finditer(data[22:])]
    version = next((v for v in strings if v.startswith('FL Studio ')), None)
    plugins = [v for v in strings if _plugin_label(v)]
    return {
        'name': Path(name).name,
        'sha256': hashlib.sha256(data).hexdigest(),
        'format': 'FL Studio .fst container',
        'fl_studio_version': version,
        'candidate_effect_names_in_serialized_order': plugins,
        'active_bypass_states_verified': False,
        'plugin_settings_verified': False,
        'warning': 'Effect-name evidence only; no third-party parameter or bypass-state reconstruction',
    }


def inspect_zip(path: Path) -> dict:
    entries = []
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_FILES:
            raise ValueError('Too many ZIP entries')
        total = 0
        seen = set()
        for info in infos:
            if info.is_dir():
                continue
            entry = info.filename.replace('\\', '/')
            parts = entry.split('/')
            if entry.startswith('/') or '..' in parts or any(not x for x in parts):
                raise ValueError('Unsafe archive path')
            if entry.casefold() in seen:
                raise ValueError('Duplicate archive path')
            seen.add(entry.casefold())
            if info.flag_bits & 1 or (info.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                raise ValueError('Encrypted or symlink member')
            if info.file_size > MAX_FST_BYTES and entry.lower().endswith('.fst'):
                raise ValueError('Oversized FST')
            if info.file_size > MAX_TOTAL_BYTES or info.file_size / max(info.compress_size, 1) > MAX_RATIO:
                raise ValueError('Oversized or overly compressed member')
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError('Archive exceeds size budget')
            if entry.lower().endswith('.fst'):
                entries.append(inspect_fst(archive.read(info), entry))
    return {
        'schema': 'skelly.fst-intake-catalog.v1',
        'source_zip_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'fst_count': len(entries),
        'presets': entries,
        'privacy': 'No original audio, FLP/FST bytes, personal paths or plugin parameters exported',
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('zip_file', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing overwrite')
    if args.output.resolve() == args.zip_file.resolve():
        raise ValueError('Input/output collision')
    report = inspect_zip(args.zip_file)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'fst_count': report['fst_count'], 'report': str(args.output)}))


if __name__ == '__main__':
    main()
