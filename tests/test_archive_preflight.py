import hashlib
import copy
import pytest
from scripts.materialize_archive import materialize

def sha(x):return hashlib.sha256(x).hexdigest()

def manifest_one(path,original,b):
 return {'path':path,'bytes':len(b),'sha256':sha(b),'storage':{'type':'direct','repo_path':original}}

def test_later_corrupt_asset_cannot_partially_write(tmp_path):
 (tmp_path/'good').write_bytes(b'good');(tmp_path/'bad').write_bytes(b'bad')
 m={'version':1,'assets':[manifest_one('good.wav','good',b'good'),manifest_one('bad.wav','bad',b'expected')]}
 target=tmp_path/'out'
 with pytest.raises(ValueError):materialize(tmp_path,m,output=target,write=True)
 assert not target.exists()

def test_later_collision_cannot_partially_write(tmp_path):
 (tmp_path/'good').write_bytes(b'good');(tmp_path/'second').write_bytes(b'second')
 target=tmp_path/'out';target.mkdir();(target/'second.wav').write_bytes(b'other')
 m={'version':1,'assets':[manifest_one('good.wav','good',b'good'),manifest_one('second.wav','second',b'second')]}
 with pytest.raises(FileExistsError):materialize(tmp_path,m,output=target,write=True)
 assert not (target/'good.wav').exists()

def test_duplicate_path_rejected(tmp_path):
 (tmp_path/'good').write_bytes(b'good')
 x=manifest_one('dup.wav','good',b'good')
 with pytest.raises(ValueError,match='Duplicate'):
  materialize(tmp_path,{'version':1,'assets':[x,copy.deepcopy(x)]})

def test_optimized_python_mode_does_not_bypass_version_check(tmp_path):
 with pytest.raises(ValueError):materialize(tmp_path,{'version':2,'assets':[]})

def test_same_destination_is_idempotent(tmp_path):
 (tmp_path/'good').write_bytes(b'good')
 m={'version':1,'assets':[manifest_one('good.wav','good',b'good')]}
 dest=tmp_path/'out';materialize(tmp_path,m,output=dest,write=True);materialize(tmp_path,m,output=dest,write=True)
 assert (dest/'good.wav').read_bytes()==b'good'
