from pathlib import Path
import json
import numpy as np
import soundfile as sf
import pytest
from skell_sound_match.sustained_air_fit import fit_files,apply_files,fit,AirFitError

def vocal(sr=44100,length=1.5):
 t=np.arange(round(sr*length))/sr
 x=.045*(np.sin(2*np.pi*220*t)+.2*np.sin(2*np.pi*1300*t)+.04*np.sin(2*np.pi*10600*t))
 return x[:,None]

def test_offline_model_roundtrip_and_nonoverwrite(tmp_path):
 x=vocal(); src=tmp_path/'src.wav';ref=tmp_path/'ref.wav';mod=tmp_path/'model.json';trial=tmp_path/'trial.wav';report=tmp_path/'report.json'
 sf.write(src,x,44100,subtype='PCM_24');sf.write(ref,x,44100,subtype='PCM_24')
 a=fit_files(src,ref,mod,trial,report)
 assert a['trained_settings']['amount'] in (0,.25,.35,.45)
 assert json.loads(mod.read_text())['approval']=='EXPERIMENT_ONLY'
 dst=tmp_path/'render_again.wav';apply_files(src,mod,dst)
 first,_=sf.read(trial);second,_=sf.read(dst)
 assert np.array_equal(first,second)
 with pytest.raises(FileExistsError):apply_files(src,mod,dst)
 with pytest.raises(FileExistsError):fit_files(src,ref,mod,trial,report)

def test_mismatched_audio_fails_without_files(tmp_path):
 x=vocal();src=tmp_path/'src.wav';ref=tmp_path/'ref.wav';sf.write(src,x,44100);sf.write(ref,x[:40000],44100)
 with pytest.raises(AirFitError):fit_files(src,ref,tmp_path/'model',tmp_path/'out',tmp_path/'report')
 assert not (tmp_path/'out').exists()

def test_unsuitable_rate_and_nonfinite_rejected():
 x=vocal()
 with pytest.raises(ValueError):fit(x,x,16000)
 with pytest.raises(AirFitError):fit(x,x*.5,44100,train_window=(0,4))
