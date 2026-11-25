"""Verify a private research checkpoint without extracting or executing it."""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import re
import zipfile

MANIFEST = "CHECKPOINT_MANIFEST.json"
SCHEMA = "skelly.private-checkpoint.v1"


def _safe_name(name):
    return (isinstance(name, str) and bool(name) and '\\' not in name
            and ':' not in name and not name.startswith('/')
            and all(p not in ('', '.', '..') for p in name.split('/'))
            and str(PurePosixPath(name)) == name)


def verify(path):
    """Fail closed on incomplete, duplicated, unsafe or modified members."""
    with zipfile.ZipFile(path) as z:
        names = [i.filename for i in z.infolist()]
        if any(not _safe_name(n) for n in names) or len({n.casefold() for n in names}) != len(names):
            raise ValueError("unsafe or duplicate archive path")
        if MANIFEST not in names:
            raise ValueError("missing checkpoint manifest")
        if z.getinfo(MANIFEST).file_size > 4 * 1024 * 1024:
            raise ValueError("manifest too large")
        m = json.loads(z.read(MANIFEST))
        if not isinstance(m, dict) or m.get('schema') != SCHEMA or not isinstance(m.get('files'), list):
            raise ValueError("unsupported manifest schema")
        seen = set()
        for f in m['files']:
            if not isinstance(f, dict):
                raise ValueError("invalid manifest record")
            n, size, digest = f.get('path'), f.get('bytes'), f.get('sha256')
            if not _safe_name(n):
                raise ValueError("unsafe manifest path")
            if (n == MANIFEST or n in seen
                    or type(size) is not int or size < 0 or not isinstance(digest, str)
                    or re.fullmatch(r'[0-9a-f]{64}', digest) is None):
                raise ValueError("invalid or duplicate manifest record")
            seen.add(n)
            if n not in names or z.getinfo(n).file_size != size:
                raise ValueError(f"missing member or size mismatch: {n}")
            h = hashlib.sha256()
            with z.open(n) as src:
                for block in iter(lambda: src.read(1024 * 1024), b''):
                    h.update(block)
            if h.hexdigest() != digest:
                raise ValueError(f"hash mismatch: {n}")
        if seen != set(names) - {MANIFEST} or not seen:
            raise ValueError("manifest does not cover every member")
        return {'verified_files': len(seen), 'schema': SCHEMA}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive')
    args = p.parse_args()
    print(json.dumps(verify(args.archive), sort_keys=True))


if __name__ == '__main__':
    main()
