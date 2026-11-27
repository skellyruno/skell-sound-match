import numpy as np
import pytest
from scipy import signal
from skell_sound_match.wav_only.flexible_eq import response, fit_studio_eq

@pytest.mark.parametrize('sr',[44100,48000,96000])
def test_filter_response(sr):
    f=np.array([70.,100.,1000.,4000.,9000.])
    norm=np.log(1000./20)/np.log(1000)
    # Neutral bell/shelf; exact standard high/lowpass coefficient agreement.
    for k in [0,3,4]:
        assert np.allclose(response(f,sr,[norm,.5],[.4],[k]),1.,atol=1e-9)
    for k,mode in [(1,'highpass'),(2,'lowpass')]:
        width=np.log((1/np.sqrt(2))/.35)/np.log(12)
        _,h=signal.sosfreqz(signal.butter(2,1000.,fs=sr,btype=mode,output='sos'),worN=f,fs=sr)
        assert np.allclose(response(f,sr,[norm,.5],[width],[k]),h,atol=1e-9)

@pytest.mark.parametrize('sr',[44100,48000])
def test_synthetic_band_fit(sr):
    rng=np.random.default_rng(58);x=rng.normal(0,.03,(sr*2,2));t=signal.sosfilt(signal.butter(2,160,fs=sr,btype='highpass',output='sos'),x,axis=0)*.8
    fit=fit_studio_eq(x[:sr],t[:sr],sr,topology='cuts')
    assert len(fit['params'])==16 and len(fit['q'])==8 and all(0<=v<=1 for v in fit['params']+fit['q'])
    f,p=signal.welch(x[sr:],sr,nperseg=2048,axis=0);_,q=signal.welch(t[sr:],sr,nperseg=2048,axis=0);k=np.array(fit['enabled']);h=response(f,sr,np.asarray(fit['params']).reshape(8,2)[k],np.asarray(fit['q'])[k],np.asarray(fit['kinds'])[k])*10**(fit['gain']/20)
    m=(f>=70)&(f<=15000);before=np.mean(abs(10*np.log10(p[m].sum(1)/q[m].sum(1))));after=np.mean(abs(10*np.log10(p[m].sum(1)*abs(h[m])**2/q[m].sum(1))))
    assert after<before*.65

def test_reject_silent_and_invalid():
    x=np.zeros((8192,2))
    with pytest.raises(ValueError):fit_studio_eq(x,x)
    with pytest.raises(ValueError):fit_studio_eq(x,x[:-1])
