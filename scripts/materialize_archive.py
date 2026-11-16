"""Reconstruct lossless sound-matching research data from GitHub object chunks.

Usage: python scripts/materialize_archive.py --verify
       python scripts/materialize_archive.py --restore [--output PATH]
No network, audio processing, overwrites, or unverified reconstruction.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path(repo: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('Invalid archive path')
    target=(repo/name).resolve()
    if not target.is_relative_to(repo.resolve()):
        raise ValueError('Archive path traversal rejected')
    return target


def materialize(repo: Path, manifest: dict, *, output: Path | None = None, write: bool = False) -> list[dict]:
    repo=repo.resolve()
    assert manifest.get('version')==1
    results=[]
    for item in manifest['assets']:
        storage=item.get('storage',{})
        kind=storage.get('type')
        if kind=='direct':
            parts=[_path(repo,storage['repo_path'])]
        elif kind=='parts':
            parts=[_path(repo,p['repo_path']) for p in storage['parts']]
            if not parts:raise ValueError('Empty part list')
        else:
            raise ValueError('Missing asset storage map')
        chunks=[]
        for i,p in enumerate(parts):
            raw=p.read_bytes()
            if kind=='parts':
                note=storage['parts'][i]
                if len(raw)!=note['size'] or _sha(raw)!=note['sha256']:
                    raise ValueError('Chunk integrity mismatch: '+str(p))
            chunks.append(raw)
        data=b''.join(chunks)
        if len(data)!=item['bytes'] or _sha(data)!=item['sha256']:
            raise ValueError('Restored asset checksum mismatch: '+item['path'])
        if write:
            if output is None:raise ValueError('Missing output directory')
            path=_path(output,item['path'])
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                if _sha(path.read_bytes())!=_sha(data):
                    raise FileExistsError('Refusing to overwrite: '+str(path))
            else:
                path.write_bytes(data)
        results.append({'path':item['path'],'bytes':len(data),'sha256':item['sha256']})
    return results


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
