"""Stable content namespace from an explicit frozen dependency inventory.
Adding unrelated research files never invalidates previous replay caches.
Offline utility; not for audio callback use.
"""
from pathlib import Path, PurePosixPath
import hashlib


def dependency_namespace(root, relative_paths, archive_sha256):
    """Hash sorted, explicitly named files and a verified parent archive digest.

    File bytes are read each call. A changed dependency changes the namespace;
    missing paths fail instead of silently skipping a dependency. The caller
    must freeze a complete transitive dependency list for the recipe generation.
    """
    root = Path(root).resolve(strict=True)
    names = list(relative_paths)
    if not names or any(not isinstance(n, str) or not n for n in names) or len(set(names)) != len(names):
        raise ValueError('dependency names must be unique nonempty strings')
    if not isinstance(archive_sha256, str) or len(archive_sha256) != 64:
        raise ValueError('invalid archive digest')
    archive = bytes.fromhex(archive_sha256)
    if len(archive) != 32:
        raise ValueError('invalid archive digest')
    h = hashlib.sha256()
    for name in sorted(names):
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or p.as_posix() != name:
            raise ValueError('noncanonical dependency path')
        local = (root / name).resolve(strict=True)
        if not local.is_relative_to(root) or not local.is_file():
            raise ValueError('dependency escapes root or is not a file')
        h.update(name.encode())
        h.update(hashlib.sha256(local.read_bytes()).digest())
    h.update(archive)
    return h.hexdigest()
