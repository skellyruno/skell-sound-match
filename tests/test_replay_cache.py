import numpy as np
import pytest
from skell_sound_match.wav_only.replay_cache import cached_replay, replay_key


def test_repeat_and_exact_identity(tmp_path):
    x=np.ones((64,2),'f'); calls=[]
    def run(v,sr): calls.append(sr);return v*.5
    for _ in range(2):np.testing.assert_array_equal(cached_replay(tmp_path,'v1','a','seed',x,44100,run),x*.5)
    assert len(calls)==1
    for namespace,stage,rate,source in [('v2','seed',44100,x),('v1','other',44100,x),('v1','seed',48000,x),('v1','seed',44100,x*2)]:
        cached_replay(tmp_path,namespace,'a',stage,source,rate,run)
    assert len(calls)==5


def test_corrupt_recomputed(tmp_path):
    x=np.ones((10,2),'f');k,_=replay_key('v','a','s',x,44100)
    (tmp_path/(k+'.npz')).write_bytes(b'corrupt')
    y=cached_replay(tmp_path,'v','a','s',x,44100,lambda v,s:v*2)
    np.testing.assert_array_equal(y,x*2)


def test_wrong_digest_recomputed(tmp_path):
    x=np.ones((10,2),'f');k,_=replay_key('v','a','s',x,44100)
    np.savez(tmp_path/(k+'.npz'),samples=x*9,key=k,sha256='bad')
    np.testing.assert_array_equal(cached_replay(tmp_path,'v','a','s',x,44100,lambda v,s:v),x)


@pytest.mark.parametrize('x,rate',[(np.zeros((3,1)),44100),(np.full((3,2),np.nan),44100),(np.zeros((0,2)),44100),(np.ones((3,2)),True)])
def test_invalid_input(x,rate):
    with pytest.raises(ValueError):replay_key('v','a','s',x,rate)


def test_invalid_render_not_published(tmp_path):
    with pytest.raises(ValueError):cached_replay(tmp_path,'v','a','s',np.ones((3,2),'f'),44100,lambda v,s:v[:2])
    assert not list(tmp_path.iterdir())


def test_truncated_zip_recomputed(tmp_path):
    x=np.ones((10,2),'f');k,_=replay_key('v','a','s',x,44100)
    (tmp_path/(k+'.npz')).write_bytes(b'PK\x03\x04' + bytes(16))
    np.testing.assert_array_equal(cached_replay(tmp_path,'v','a','s',x,44100,lambda v,s:v),x)
