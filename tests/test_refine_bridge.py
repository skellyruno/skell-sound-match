"""Synthetic regression tests for the experimental research bridge."""
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match import refine_bridge as bridge


def synth(tmp_path, stereo=False):
    sr=22050
    t=np.arange(sr*10)/sr
    x=.05*np.sin(2*np.pi*220*t)*(0.5+0.4*np.sin(2*np.pi*2*t))
    if stereo:
        x=np.stack((x,np.roll(x,600)),axis=1)
    a,b=tmp_path/"prev.wav",tmp_path/"ref.wav"
    sf.write(a,x,sr);sf.write(b,x,sr)
    return a,b


def test_pair_accepts_valid_files(tmp_path):
    a,b=synth(tmp_path)
    assert bridge.validate_pair(a,b)[0]==22050


def test_rejects_stereo_ambience(tmp_path):
    a,b=synth(tmp_path,True)
    with pytest.raises(ValueError,match="Stereo ambience"):
        bridge.validate_pair(a,b)


def test_no_existing_output(tmp_path):
    a,b=synth(tmp_path)
    dest=tmp_path/"already";dest.mkdir()
    with pytest.raises(FileExistsError):
        bridge.run(tmp_path/"none.py",a,b,dest)


def test_rejects_unsafe_peak(tmp_path):
    a,b=synth(tmp_path)
    x,sr=sf.read(a)
    x[:10]=1.1
    sf.write(tmp_path/"hot.wav",x,sr,subtype="FLOAT")
    with pytest.raises(ValueError,match="dBTP"):
        bridge.check_candidate(tmp_path/"hot.wav",sr,(sr*10,1))


def test_evidence_gate_rejects_tonal_regression():
    one={"spectral_error_9band_db":.3,"envelope_error_db":{"20ms":1.0,"200ms":.5}}
    two={"spectral_error_9band_db":.5,"envelope_error_db":{"20ms":.9,"200ms":.4}}
    r={"metrics":{"previous":{"validation":one,"late":one},
                  "refined_out_of_fold":{"validation":two,"late":two}},
       "gate":{"passed":True}}
    assert not bridge.evaluate_report(r)
    two["spectral_error_9band_db"]=.2
    assert bridge.evaluate_report(r)
