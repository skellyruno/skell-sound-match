"""Read-only inventory of private ZIP sources; no automatic pairing or extraction."""
import hashlib
import io
import zipfile
from pathlib import Path
import soundfile as sf


def index_archives(paths):
    rows=[]
    for path in map(Path,paths):
        with zipfile.ZipFile(path) as z:
            seen=set()
            for item in z.infolist():
                if item.is_dir() or Path(item.filename).suffix.lower() not in ('.wav','.flac','.fst','.flp'):
                    continue
                if item.filename in seen or item.file_size>512*1024*1024:
                    raise ValueError('duplicate member name or oversized asset')
                seen.add(item.filename)
                # No extraction: member names are metadata, not output paths.
                data=z.read(item)
                row=dict(archive=path.name,member=item.filename,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
                if Path(item.filename).suffix.lower() in ('.wav','.flac'):
                    info=sf.info(io.BytesIO(data))
                    row.update(frames=info.frames,rate=info.samplerate,channels=info.channels)
                rows.append(row)
    return rows
