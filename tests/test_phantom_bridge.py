import json
from pathlib import Path
from types import SimpleNamespace
from skell_sound_match.wav_only import phantom_bridge as p
def test_missing_tool(monkeypatch):
    monkeypatch.setattr(p.shutil,'which',lambda _:None)
    assert p.run_external('unused')['status']=='unavailable'
def test_json_and_isolated_home(monkeypatch,tmp_path):
    a=tmp_path/'a.wav';a.touch();seen=[]
    def fake(cmd,**kw):
        assert cmd==['phantom','analyze',str(a),'--json']
        home=Path(kw['env']['HOME']);seen.append(home)
        assert kw['env']['PHANTOM_NO_TELEMETRY']=='1' and kw['cwd']==str(home)
        assert 'phantom' in json.loads((home/'.mcp.json').read_text())['mcpServers']
        return SimpleNamespace(returncode=0,stdout='{"test":1}',stderr='')
    monkeypatch.setattr(p.subprocess,'run',fake)
    assert p.run_external(a,executable='phantom')['analysis']=={'test':1}
    assert not seen[0].exists() and not (tmp_path/'.mcp.json').exists()
def test_invalid_json(monkeypatch,tmp_path):
    a=tmp_path/'a.wav';a.touch()
    monkeypatch.setattr(p.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='not json',stderr=''))
    assert p.run_external(a,executable='phantom')['status']=='failed'
def test_compare(monkeypatch,tmp_path):
    a=tmp_path/'a.wav';a.touch();b=tmp_path/'b.wav';b.touch()
    def fake(cmd,**kw):
        assert cmd==['phantom','compare',str(a),'--reference',str(b),'--json']
        return SimpleNamespace(returncode=0,stdout='{"comparison":true}',stderr='')
    monkeypatch.setattr(p.subprocess,'run',fake)
    assert p.run_external(a,b,executable='phantom')['analysis']=={'comparison':True}
