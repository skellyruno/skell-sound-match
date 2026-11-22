import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from skell_sound_match.wav_only.html_listening_lab import make_lab


def fixture(tmp_path):
    sr = 32000
    t = np.arange(sr * 3) / sr
    for name, amp in [("a", 0.1), ("b", 0.05)]:
        audio = amp * np.sin(2 * np.pi * 220 * t)
        sf.write(tmp_path / f"{name}.wav", np.column_stack((audio, audio)), sr)
    payload = {"groups": [{"id": "test", "title": "T" ,"seconds": 2,
                           "clips": [{"label": "original", "path": "a.wav", "kind": "reference"},
                                     {"label": "trial", "path": "b.wav"}]}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload),encoding="utf-8")
    return path


def test_build_embeds_audio_and_hides_direct_paths(tmp_path):
    src=fixture(tmp_path)
    dest=tmp_path/"lab.html"
    result=make_lab(src,dest,seed=1234)
    html=dest.read_text(encoding="utf-8")
    assert result["groups"]==1 and result["clips"]==2
    assert "data:audio/flac;base64," in html
    assert "a.wav" not in html and "b.wav" not in html
    assert "winner" in html and "loser" in html and "Download feedback JSON" in html
    assert all(a["peak_dbtp_4x"]<=-1.18 for a in result["audits"])
    assert result["audits"][0]["encoded_flac_sha256"]


def test_no_overwrite_and_mismatch(tmp_path):
    src=fixture(tmp_path)
    out=tmp_path/"lab.html"
    make_lab(src,out)
    with pytest.raises(FileExistsError):
        make_lab(src,out)
    payload=json.loads(src.read_text(encoding="utf-8"))
    payload['groups'][0]['clips'][1]['path']='a.wav'
    payload['groups'][0]['id']='test'
    payload['groups'].append(payload['groups'][0])
    src.write_text(json.dumps(payload),encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        make_lab(src,tmp_path/"new.html")


def test_missing_input_and_out_of_bounds(tmp_path):
    src=fixture(tmp_path)
    payload=json.loads(src.read_text(encoding="utf-8"))
    payload['groups'][0]['start']=2.5
    src.write_text(json.dumps(payload),encoding="utf-8")
    with pytest.raises(ValueError, match="Insufficient"):
        make_lab(src,tmp_path/"new.html")
    payload['groups'][0]['start']=0
    payload['groups'][0]['clips'][0]['path']='missing.wav'
    src.write_text(json.dumps(payload),encoding="utf-8")
    with pytest.raises((FileNotFoundError, RuntimeError)):
        make_lab(src,tmp_path/"new.html")


def test_manifest_escape(tmp_path):
    src=fixture(tmp_path)
    payload=json.loads(src.read_text(encoding="utf-8"))
    payload['groups'][0]['title']='A </script><script>alert(1)</script>'
    src.write_text(json.dumps(payload),encoding="utf-8")
    result=make_lab(src,tmp_path/"new.html")
    html=(tmp_path/"new.html").read_text(encoding="utf-8")
    assert '</script><script>alert(1)' not in html
    assert '\\u003c/script\\u003e' in html