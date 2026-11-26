import numpy as np
import pytest
from skell_sound_match.wav_only.multiband_reconstruction import active_partition,split_bands,fit_energy,render_energy,fit_dynamic,render_dynamic


def tone(sr,seconds=3):
    t=np.arange(int(sr*seconds))/sr
    return np.column_stack([.08*np.sin(2*np.pi*210*t)+.03*np.sin(2*np.pi*2300*t),.07*np.sin(2*np.pi*210*t)-.03*np.sin(2*np.pi*2300*t)]).astype('f')

@pytest.mark.parametrize('sr',[32000,44100,48000,96000,192000])
def test_unity_and_causality(sr):
    x=tone(sr,1);b=split_bands(x,sr);assert np.max(abs(render_energy(b,np.ones((4,2)))-x))<1e-7
    c=fit_dynamic(b,b,sr);y=render_dynamic(b,c,sr);assert np.max(abs(y-x))<1e-7
    h=np.zeros((4,2,4));h[:,:,0]=2;h[:,:,1]=.2;h[:,:,2]=.1;h[:,:,3]=-25
    y=render_dynamic(b,h,sr);z=x.copy();z[len(x)//2:]=0;q=render_dynamic(split_bands(z,sr),h,sr);assert np.array_equal(y[:len(x)//2],q[:len(x)//2])

def test_activity_tail():
    sr=44100;x=np.vstack([tone(sr),np.zeros((sr*5,2),'f')]);t=x.copy();t[3*sr:4*sr]=tone(sr,1)*.1
    end,a,b=active_partition(x,t,sr);assert end>=4*sr and end<5*sr and abs(a-.45*3*sr)<441 and abs(b-.7*3*sr)<441

def test_silent_reject():
    sr=44100;x=tone(sr);z=np.zeros_like(x)
    with pytest.raises(ValueError):active_partition(x,z,sr)
    with pytest.raises(ValueError):fit_energy(split_bands(x,sr),split_bands(z,sr))
    with pytest.raises(ValueError):fit_dynamic(split_bands(x,sr),split_bands(z,sr),sr)

def test_energy_fit():
    sr=44100;x=tone(sr);b=split_bands(x,sr);g=np.array([[1.2,.7],[.8,1.4],[1.,1.],[.7,1.2]])
    # Direct exact filter-bank enrollment geometry, independent of target generation.
    h=fit_energy(b,b*g);assert np.max(abs(h-g))<1e-5
    assert np.isfinite(render_energy(b,h)).all()

def test_antiphase():
    sr=44100;x=tone(sr);x[:,1]=-x[:,0];b=split_bands(x,sr);g=fit_energy(b,b*.7);y=render_energy(b,g);assert np.array_equal(y[:,0],-y[:,1])

def test_invalid():
    sr=44100;x=tone(sr);b=split_bands(x,sr)
    for edges in [(0,100),(4000,3000),(30000,)]:
        with pytest.raises(ValueError):split_bands(x,sr,edges)
    with pytest.raises(ValueError):split_bands(np.full_like(x,np.nan),sr)
    with pytest.raises(ValueError):render_energy(b,np.ones((4,2))*100)
    with pytest.raises(ValueError):render_dynamic(b,np.ones((4,2,4))*100,sr)
    with pytest.raises(ValueError):active_partition(x,x[:-1],sr)


def test_long_padded_export():
    sr=44100;x=np.zeros((round(51.4*sr),2),'f');x[:3*sr]=tone(sr);t=x.copy();t[3*sr:4*sr]=tone(sr,1)*.1
    end,a,b=active_partition(x,t,sr);assert 4*sr<=end<5*sr and a==int(.45*(3*sr)) and b==int(.7*(3*sr))
    with pytest.raises(ValueError):split_bands(x,sr)
