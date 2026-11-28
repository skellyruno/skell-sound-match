"""Verify or reconstruct a lossless sound-match archive without changing originals.

Usage: python scripts/materialize_archive.py --verify
       python scripts/materialize_archive.py --restore [--output PATH]

All assets and output collisions are preflighted before any file is written.
Files are then created via same-directory temporary files and os.replace.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('Invalid archive path')
    target=(root/name).resolve()
    if not target.is_relative_to(root.resolve()) or target==root.resolve():
        raise ValueError('Archive path traversal rejected')
    return target


def _valid_hash(value) -> bool:
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def _decode(repo: Path, item: dict) -> bytes:
    storage=item.get('storage',{})
    kind=storage.get('type')
    if kind=='direct':
        paths=[(_path(repo,storage['repo_path']),None)]
    elif kind=='parts':
        parts=storage.get('parts')
        if not isinstance(parts,list) or not parts:
            raise ValueError('Empty or invalid part list')
        paths=[(_path(repo,p['repo_path']),p) for p in parts]
    else:
        raise ValueError('Missing asset storage map')
    chunks=[]
    for path,part in paths:
        raw=path.read_bytes()
        if part is not None:
            if (type(part.get('size')) is not int or part['size']<0 or
                not _valid_hash(part.get('sha256')) or
                len(raw)!=part['size'] or _sha(raw)!=part['sha256']):
                raise ValueError('Chunk integrity mismatch: '+str(path))
        chunks.append(raw)
    data=b''.join(chunks)
    if (type(item.get('bytes')) is not int or item['bytes']<0 or
        not _valid_hash(item.get('sha256')) or
        len(data)!=item['bytes'] or _sha(data)!=item['sha256']):
        raise ValueError('Restored asset checksum mismatch: '+str(item.get('path')))
    return data


def materialize(repo: Path, manifest: dict, *, output: Path | None = None, write: bool = False) -> list[dict]:
    repo=repo.resolve()
    if not isinstance(manifest,dict) or manifest.get('version')!=1 or not isinstance(manifest.get('assets'),list):
        raise ValueError('Unsupported or invalid archive manifest')
    if write and output is None:
        raise ValueError('Missing output directory')
    if write:
        output=output.resolve()
    # Preflight *every* chunk, path and destination before writing anything.
    assets=[]
    seen=set()
    for item in manifest['assets']:
        if not isinstance(item,dict) or not isinstance(item.get('path'),str):
            raise ValueError('Malformed asset record')
        if item['path'] in seen:
            raise ValueError('Duplicate archive destination: '+item['path'])
        seen.add(item['path'])
        if write:
            path=_path(output,item['path'])
            if path.exists() and not path.is_file():
                raise FileExistsError('Existing destination is not a file: '+str(path))
        else:
            path=None
        data=_decode(repo,item)
        if path is not None and path.exists() and _sha(path.read_bytes())!=item['sha256']:
            raise FileExistsError('Refusing to overwrite: '+str(path))
        assets.append((item,path,data))
    if write:
        for item,path,data in assets:
            if path.exists():
                continue
            path.parent.mkdir(parents=True,exist_ok=True)
            tmp_path=None
            try:
                with tempfile.NamedTemporaryFile(prefix='.skell-archive-',dir=path.parent,delete=False) as f:
                    tmp_path=Path(f.name)
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                if _sha(tmp_path.read_bytes())!=item['sha256']:
                    raise IOError('Temporary file integrity mismatch')
                os.replace(tmp_path,path)
            finally:
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)
    return [{'path':x['path'],'bytes':len(data),'sha256':x['sha256']} for x,_,data in assets]


def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--verify',action='store_true')
    mode.add_argument('--restore',action='store_true')
    parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path,default=Path('archive/restored'))
    a=parser.parse_args()
    man=json.loads((a.repo_root/'archive/manifest.json').read_text(encoding='utf-8'))
    result=materialize(a.repo_root,man,output=a.output,write=a.restore)
    print(f"Verified {len(result)} assets; {sum(x['bytes'] for x in result)/1e6:.2f} MB original bytes" + ('; restored' if a.restore else ''))

if __name__=='__main__':main()
