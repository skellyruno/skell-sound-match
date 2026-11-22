import json,shutil,subprocess
from pathlib import Path
import pytest
from skell_sound_match.wav_only.verified_listening_lab import make_lab,TEMPLATE
from test_pairing_audit import fixture


def test_audited_audio_mapping_and_loudness(tmp_path):
    group,x,sr=fixture(tmp_path)
    group.update(preset='Synthetic',listen_for='Tone',start=.2,seconds=2)
    group['reference']['label']='Original main'
    group['candidates'][0]['identity']='private-version'
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'schema':'skelly.verified-listening-manifest.v1','groups':[group]}))
    output=tmp_path/'lab.html';qa=make_lab(manifest,output)
    assert qa['pairing_pass']==1
    source=output.read_text(encoding='utf-8');doc=json.JSONDecoder().raw_decode(source.split('const LAB=',1)[1])[0]
    assert 'letter' not in doc['groups'][0]['reference']
    assert doc['groups'][0]['candidates'][0]['letter']=='A'
    levels=[x['lufs'] for x in qa['audits'][0]['encoded_checks']]
    assert max(levels)-min(levels)<.05
    with pytest.raises(FileExistsError):make_lab(manifest,output)


def test_new_frontend_runtime(tmp_path):
    node=shutil.which('node')
    if not node:pytest.skip('Node is required for JavaScript regression checks')
    def group(n,count,status='PAIRING_CHECKS_PASS'):
        return {'id':str(n),'preset':'Synthetic '+str(n),'stage':'main','listen_for':'Tone','seconds':6,'recording_id':'take1','status':status,'issues':[],
          'reference':{'label':'Original main','sha256':'r','audio':'synthetic-original'},
          'candidates':[{'letter':chr(65+i),'identity':'private-version','version_id':str(i),'sha256':str(i),'audio':'synthetic-'+str(i)} for i in range(count)]}
    doc={'session_id':'unit','groups':[group(0,2),group(1,1),group(2,0,'UNVERIFIED')]}
    html=TEMPLATE.replace('/*__LAB__*/',json.dumps(doc));script=html.split('<script>',1)[1].split('</script>',1)[0]
    path=tmp_path/'script.cjs';path.write_text(script,encoding='utf-8')
    result=subprocess.run([node,str(Path(__file__).with_name('verified_lab_runtime.cjs')),str(path)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


def test_numbered_takes_and_separate_archives_are_not_cross_paired():
    from skell_sound_match.wav_only.skelly_bulk_match import select_plan
    def row(name,role,archive='batch.zip',sha='x'):
        return dict(target_id='speakerz',archive=archive,member=name,role=role,sha256=sha,frames=32000,sample_rate=32000,channels=2)
    rows=[row('speakerz take 1 dry.wav','dry',sha='a'),row('speakerz take 2 main.wav','main',sha='b')]
    assert len(select_plan(rows))==2
    rows=[row('speakerz dry.wav','dry','first.zip','a'),row('speakerz main.wav','main','other.zip','b')]
    assert select_plan(rows)[0]['status']=='CROSS_RECORDING_REVIEW_REQUIRED'
