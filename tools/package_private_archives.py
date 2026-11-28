"""Bundle explicit private ZIP inputs without publishing or changing originals.

Manifest: {"files":[{"name":"example.zip","size_bytes":123,"sha256":"..."}]}.
Run outside a public checkout. README is optional; outputs refuse overwrite.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def hash_stream(stream):
    result=hashlib.sha256();size=0
    for block in iter(lambda:stream.read(1024*1024),b''):
        result.update(block);size+=len(block)
    return result.hexdigest(),size


def build(source,manifest,output,readme=None):
    source=Path(source).resolve();output=Path(output).resolve()
    for parent in output.parents:
        if (parent/'.git').exists() or ((parent/'pyproject.toml').exists() and (parent/'skell_sound_match').is_dir()):
            raise ValueError('Private bundle must remain outside a source repository')
    if output.exists():raise FileExistsError(output)
    files=json.loads(Path(manifest).read_text(encoding='utf-8'))['files'];records=[];names=set()
    if not files:raise ValueError('No archive inputs')
    for entry in files:
        name=entry['name']
        if Path(name).name!=name or '/' in name or '\\' in name or not name.lower().endswith('.zip') or name in names:
            raise ValueError('Expected unique ZIP basenames')
        names.add(name);path=source/name
        if path.resolve()==output:raise ValueError('Output cannot be an input')
        with path.open('rb') as f:identity,size=hash_stream(f)
        if size!=entry['size_bytes'] or (entry.get('sha256') and identity!=entry['sha256']):
            raise ValueError('Input identity differs: '+name)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:raise ValueError('Input ZIP CRC failed: '+name)
        records.append({'name':name,'size_bytes':size,'sha256':identity,'zip_crc_check':'PASS'})
    temporary=output.with_suffix(output.suffix+'.partial')
    with zipfile.ZipFile(temporary,'x',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
        for entry in records:archive.write(source/entry['name'],entry['name'])
        archive.writestr('MANIFEST.json',json.dumps({'files':records},indent=2)+'\n')
        if readme:archive.writestr('README.md',Path(readme).read_bytes())
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:raise ValueError('Output ZIP CRC failed')
        for entry in records:
            with archive.open(entry['name']) as f:identity,size=hash_stream(f)
            with (source/entry['name']).open('rb') as f:current=hash_stream(f)
            if (identity,size)!=(entry['sha256'],entry['size_bytes']) or current!=(identity,size):
                raise ValueError('Nested or original bytes changed')
    # Exclusive installation preserves another writer's output.
    with temporary.open('rb') as src,output.open('xb') as dst:
        for block in iter(lambda:src.read(1024*1024),b''):dst.write(block)
    temporary.unlink()
    with output.open('rb') as f:identity,size=hash_stream(f)
    return {'output':str(output),'size_bytes':size,'sha256':identity,'archives':len(records),'integrity':'PASS'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('manifest');p.add_argument('output');p.add_argument('--readme')
    a=p.parse_args();print(json.dumps(build(a.source,a.manifest,a.output,a.readme),indent=2))
