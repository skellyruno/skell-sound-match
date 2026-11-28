import numpy as np,soundfile as sf,pytest
from dataclasses import replace
from skell_sound_match.wav_only.reference_router import Reference,digest,choose_exact,suggest,fit_exact
SR=32000
@pytest.fixture
def data(tmp_path):
 t=np.arange(2*SR)/SR;x=.1*np.sin(2*np.pi*180*t);p=tmp_path/'ref.wav';sf.write(p,x,SR,subtype='FLOAT');e=Reference('r','take1','myers','main','ref.wav',digest(p),True);return tmp_path,x,e

def test_exact(data):
 root,x,e=data;assert choose_exact(root,[e],take='take1',stage='main',family='myers')[0]==e
@pytest.mark.parametrize('change',[{'take':'take2'},{'stage':'complete'},{'family':'speakerz'},{'reviewed':False}])
def test_wrong_metadata(data,change):
 root,x,e=data
 with pytest.raises(ValueError):choose_exact(root,[replace(e,**change)],take='take1',stage='main',family='myers')
def test_tampered(data):
 root,x,e=data;(root/e.path).write_bytes(b'tampered')
 with pytest.raises(ValueError):choose_exact(root,[e],take='take1',stage='main',family='myers')
def test_ambiguous(data):
 root,x,e=data
 with pytest.raises(ValueError):choose_exact(root,[e,replace(e,key='second')],take='take1',stage='main',family='myers')
def test_traversal(data):
 root,x,e=data;p=root.parent/'outside.wav';sf.write(p,x,SR,subtype='FLOAT')
 with pytest.raises(ValueError):choose_exact(root,[replace(e,path='../outside.wav',sha256=digest(p))],take='take1',stage='main',family='myers')
def test_shortlist(data):
 root,x,e=data;assert suggest(root,[e,replace(e,key='other',stage='complete')],x,SR,stage='main')[0].key=='r';assert suggest(root,[e],x,SR,stage='adlib-base')==[]
def test_require_confirmation(data):
 root,x,e=data
 with pytest.raises(ValueError):fit_exact(root,[e],root/e.path,root/'out',source_sha256=e.sha256,take=e.take,stage=e.stage,family=e.family)
