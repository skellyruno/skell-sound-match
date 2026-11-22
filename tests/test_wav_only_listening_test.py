from pathlib import Path
import json
import numpy as np
import pytest
import soundfile as sf
import pyloudnorm as pyln

from skell_sound_match.wav_only.listening_test import prepare_pair


def _source(sr=32000, n_seconds=3, amp=.015):
    t=np.arange(sr*n_seconds)/sr
    carrier=np.sin(2*np.pi*(220*t+.1*np.sin(2*np.pi*t)))
    envelope=.2+.8*np.abs(np.sin(2*np.pi*t*.9))
    return np.stack([carrier*envelope*amp]*2,axis=1)


def _write_pair(tmp_path, sr=32000):
    r=tmp_path/'original.wav';c=tmp_path/'trial.wav'
    source=_source(sr)
    sf.write(r,source,sr,subtype='PCM_24')
    sf.write(c,source*1.9,sr,subtype='PCM_24')
    return r,c


def test_produces_blind_loudness_matched_and_peak_safe_flacs(tmp_path):
    ref,cand=_write_pair(tmp_path)
    out=tmp_path/'blind'
    result=prepare_pair(ref,cand,out,target_lufs=-18,seed=17)
    assert result['status']=='BLIND_LISTENING_ONLY_NOT_A_PRESET_APPROVAL'
    key=json.loads((out/'answer_key.json').read_text())
    assert set(key['blind_mapping'].values())=={'reference','candidate'}
    a,sr=sf.read(out/'A.flac',always_2d=True)
    b,sr2=sf.read(out/'B.flac',always_2d=True)
    assert sr==sr2==32000 and len(a)==len(b)
    meter=pyln.Meter(sr)
    la=meter.integrated_loudness(a);lb=meter.integrated_loudness(b)
    assert abs(la-lb)<.08
    assert max(key['measured_encoded_truepeak_4x_dbtp'])<=-1.19
    assert 'original.wav' not in (out/'LISTENING_SESSION.md').read_text()
    with pytest.raises(FileExistsError):
        prepare_pair(ref,cand,out,seed=17)


def test_rejects_different_sample_rate_and_mismatched_lengths(tmp_path):
    ref,cand=_write_pair(tmp_path)
    sf.write(cand,_source(sr=44100),44100)
    with pytest.raises(ValueError,match='Different sample rate'):
        prepare_pair(ref,cand,tmp_path/'bad')
    sf.write(cand,_source(n_seconds=2),32000)
    with pytest.raises(ValueError,match='Different sample rate'):
        prepare_pair(ref,cand,tmp_path/'bad2')
    assert not (tmp_path/'bad').exists() and not (tmp_path/'bad2').exists()


def test_rejects_silence_and_invalid_windows(tmp_path):
    ref,cand=_write_pair(tmp_path)
    sf.write(cand,np.zeros((32000*3,2)),32000)
    with pytest.raises(ValueError,match='Cannot loudness-match'):
        prepare_pair(ref,cand,tmp_path/'silent')
    with pytest.raises(ValueError,match='Clip interval'):
        prepare_pair(ref,ref.with_name('trial.wav'),tmp_path/'bad',start_seconds=2.5,duration_seconds=1)


def test_randomization_reproducible_and_source_files_unchanged(tmp_path):
    ref,cand=_write_pair(tmp_path)
    before={str(p):p.read_bytes() for p in (ref,cand)}
    a=tmp_path/'one';b=tmp_path/'two'
    prepare_pair(ref,cand,a,seed=88)
    prepare_pair(ref,cand,b,seed=88)
    assert (a/'A.flac').read_bytes()==(b/'A.flac').read_bytes()
    assert (a/'B.flac').read_bytes()==(b/'B.flac').read_bytes()
    assert all(p.read_bytes()==before[str(p)] for p in (ref,cand))
