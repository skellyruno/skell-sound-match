import json
import shutil
import subprocess
from pathlib import Path

import pytest

from skell_sound_match.wav_only.html_listening_lab import _TEMPLATE


def test_generated_playback_and_vote_logic(tmp_path):
    node=shutil.which('node')
    if not node:pytest.skip('Node is required for the synthetic JavaScript runtime test')
    groups=[{'id':str(n),'title':'Synthetic','note':'','duration':8,'clips':[
        {'letter':'A','kind':'reference','identity':'Original','audio':'synthetic-a'},
        {'letter':'B','kind':'candidate','identity':'Trial B','audio':'synthetic-b'},
        {'letter':'C','kind':'candidate','identity':'Trial C','audio':'synthetic-c'}]} for n in range(2)]
    html=_TEMPLATE.replace('/*__PRIVATE_GROUP_DATA__*/',json.dumps({'session_id':'unit','groups':groups}))
    script=html.split('<script>',1)[1].split('</script>',1)[0]
    target=tmp_path/'generated.cjs';target.write_text(script,encoding='utf-8')
    result=subprocess.run([node,str(Path(__file__).with_name('listening_lab_runtime.cjs')),str(target)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'PASS:' in result.stdout
