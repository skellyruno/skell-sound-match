import hashlib
from pathlib import Path
import pytest
from scripts.materialize_archive import materialize

def sha(b):return hashlib.sha256(b).hexdigest()

def test_restore_and_verify(tmp_path):
    data=b'chunk1chunk2'
    p1=tmp_path/'archive/chunks/f.part000';p1.parent.mkdir(parents=True);p1.write_bytes(b'chunk1')
    p2=tmp_path/'archive/chunks/f.part001';p2.write_bytes(b'chunk2')
    manifest={'version':1,'assets':[{'path':'data/f.bin','bytes':len(data),'sha256':sha(data),'storage':{'type':'parts','parts':[{'repo_path':'archive/chunks/f.part000','size':6,'sha256':sha(b'chunk1')},{'repo_path':'archive/chunks/f.part001','size':6,'sha256':sha(b'chunk2')} ]}}]}
    assert materialize(tmp_path,manifest)[0]['sha256']==sha(data)
    out=tmp_path/'out';materialize(tmp_path,manifest,output=out,write=True)
    assert (out/'data/f.bin').read_bytes()==data
    materialize(tmp_path,manifest,output=out,write=True)
    (out/'data/f.bin').write_bytes(b'wrong')
    with pytest.raises(FileExistsError):materialize(tmp_path,manifest,output=out,write=True)


def test_corruption_rejected(tmp_path):
    p=tmp_path/'audio.flac';p.write_bytes(b'test')
    m={'version':1,'assets':[{'path':'data/a.flac','bytes':4,'sha256':sha(b'test'),'storage':{'type':'direct','repo_path':'audio.flac'}}]}
    assert materialize(tmp_path,m)[0]['bytes']==4
    p.write_bytes(b'bad!')
    with pytest.raises(ValueError):materialize(tmp_path,m)


def test_unsafe_paths_rejected(tmp_path):
    m={'version':1,'assets':[{'path':'data/valid','bytes':1,'sha256':sha(b'x'),'storage':{'type':'direct','repo_path':'../secrets'}}]}
    with pytest.raises(ValueError):materialize(tmp_path,m)
