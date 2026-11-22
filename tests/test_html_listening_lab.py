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


def test_append_reuses_previous_blind_letters_and_audio_without_reencoding(tmp_path):
    src = fixture(tmp_path)
    first = tmp_path / "first.html"
    one = make_lab(src, first, seed=27)
    assert one["groups"] == 1 and one["new_groups"] == 1
    payload = json.loads(src.read_text(encoding="utf-8"))
    payload["groups"][0]["id"] = "new-round"
    payload["groups"][0]["title"] = "More vocals"
    src.write_text(json.dumps(payload), encoding="utf-8")
    second = tmp_path / "second.html"
    two = make_lab(src, second, seed=900, append_from=first)
    assert two["groups"] == 2 and two["new_groups"] == 1
    assert two["clips"] == 4 and two["new_clips"] == 2
    assert two["session_id"] != one["session_id"]
    import re
    old = re.search(r"const LAB = (.*?);\nconst states", first.read_text(), re.S)
    new = re.search(r"const LAB = (.*?);\nconst states", second.read_text(), re.S)
    assert old and new
    a, b = json.loads(old.group(1)), json.loads(new.group(1))
    assert a["groups"][0] == b["groups"][0]
    assert a["groups"][0]["clips"][0]["audio"] == b["groups"][0]["clips"][0]["audio"]
    assert "audio.currentTime=0" in second.read_text()
    assert "Switching keeps the current time" not in second.read_text()
    assert "skelly-blind-feedback-v2-" in second.read_text()
    assert "too close to call" in second.read_text().lower()


def test_append_rejects_duplicate_round_and_malformed_lab(tmp_path):
    src = fixture(tmp_path)
    first = tmp_path / "first.html"
    make_lab(src, first)
    with pytest.raises(ValueError, match="unique"):
        make_lab(src, tmp_path/"duplicate.html", append_from=first)
    bogus = tmp_path/"bogus.html"
    bogus.write_text("<p>not the generator output</p>")
    with pytest.raises(ValueError, match="does not contain"):
        make_lab(src, tmp_path/"other.html", append_from=bogus)


def test_stable_session_fingerprint_only_when_content_and_letters_identical(tmp_path):
    src=fixture(tmp_path)
    a=make_lab(src,tmp_path/"a.html",seed=5)
    b=make_lab(src,tmp_path/"b.html",seed=5)
    assert a["session_id"] == b["session_id"]
    assert a["html_sha256"] == b["html_sha256"]


def test_externalize_fast_html_preserves_blind_session_and_lossless_audio(tmp_path):
    from skell_sound_match.wav_only.html_listening_lab import externalize_lab
    import base64
    src=fixture(tmp_path)
    full=tmp_path/'full.html'
    previous=make_lab(src,full,seed=42)
    fast=tmp_path/'light.html'
    result=externalize_lab(full,fast)
    assert result['groups']==1 and result['clips']==2
    assert result['session_id']==previous['session_id']
    assert fast.stat().st_size<30_000
    text=fast.read_text(encoding='utf-8')
    assert 'data:audio/flac;base64,' not in text
    assert 'skelly-blind-feedback-v2-' in text
    from re import search, S
    a=json.loads(search(r'const LAB = (.*?);\nconst states',full.read_text(),S).group(1))
    b=json.loads(search(r'const LAB = (.*?);\nconst states',text,S).group(1))
    assert a['session_id']==b['session_id']
    assert [c['identity'] for c in a['groups'][0]['clips']]==[c['identity'] for c in b['groups'][0]['clips']]
    for original,light in zip(a['groups'][0]['clips'],b['groups'][0]['clips']):
        path=tmp_path/light['audio']
        assert path.is_file()
        assert b' [original reference]' not in path.name.encode()
        assert path.read_bytes()==base64.b64decode(original['audio'].split(',',1)[1])
    with pytest.raises(FileExistsError):
        externalize_lab(full,fast)


def test_externalize_refuses_existing_audio_folder(tmp_path):
    from skell_sound_match.wav_only.html_listening_lab import externalize_lab
    src=fixture(tmp_path)
    full=tmp_path/'full.html'
    make_lab(src,full)
    (tmp_path/'light_audio').mkdir()
    with pytest.raises(FileExistsError):
        externalize_lab(full,tmp_path/'light.html')


def test_switching_back_to_paused_round_keeps_global_audio_owner(tmp_path):
    # Regression: a same-letter resume must claim currentAudio, or clicking
    # another round can leave two audios playing simultaneously.
    src=fixture(tmp_path)
    make_lab(src,tmp_path/'lab.html',seed=3)
    rendered=(tmp_path/'lab.html').read_text(encoding='utf8')
    assert "if(active===c.letter){currentAudio=audio;" in rendered
    assert "if(currentAudio&&currentAudio!==audio){currentAudio.pause()}" in rendered
