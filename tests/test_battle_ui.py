import json
import subprocess
import shutil
import pytest
from skell_sound_match.wav_only.battle_royale_lab import write_lab


def test_session_binds_reference_candidates_and_blocks_duplicate_identities(tmp_path):
    uri='data:audio/flac;base64,AA=='
    doc={'groups':[{'id':'test','title':'Test','reference':uri,'candidates':[{'letter':l,'identity':l,'audio':uri} for l in 'ABC']}]}
    first=write_lab(doc,tmp_path/'one.html')
    doc['groups'][0]['reference']=uri+'A'
    assert write_lab(doc,tmp_path/'two.html') != first
    doc['groups'][0]['candidates'][1]['identity']='A'
    with pytest.raises(ValueError):write_lab(doc,tmp_path/'invalid.html')


def test_battle_transport_tie_and_blocked_votes(tmp_path):
    if not shutil.which('node'):pytest.skip('Node runtime unavailable')
    uri='data:audio/flac;base64,AA=='
    groups=[{'id':str(i),'title':'Test','note':'','reference':uri,'reviewable':i==0,'candidates':[{'letter':l,'identity':str(i)+l,'audio':uri} for l in 'ABC']} for i in range(2)]
    groups.append({'id':'single','title':'One','note':'','reference':uri,'reviewable':True,'candidates':[{'letter':'A','identity':'new','audio':uri}]})
    groups.append({'id':'pair','title':'Pair','note':'','reference':uri,'reviewable':True,'candidates':[{'letter':l,'identity':'pair'+l,'audio':uri} for l in 'AB']})
    path=tmp_path/'test.html';write_lab({'groups':groups},path)
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map(),storage={};let pauses=0,plays=0;
const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{paused:true,currentTime:0,setAttribute(){},append(){},pause(){this.paused=true;pauses++},load(){},removeAttribute(){},play(){this.paused=false;plays++;return Promise.resolve()}});return nodes.get(id)},createElement(){return {}}};
const context=vm.createContext({document,localStorage:{getItem(){return null},setItem(k,v){storage[k]=v}}});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8').split('<script>')[1].split('</script>')[0],context);
const run=s=>vm.runInContext(s,context),audio=nodes.get('audio');
nodes.get('a').onclick();audio.currentTime=3;nodes.get('b').onclick();assert.equal(audio.currentTime,0);assert.equal(run('active'),'B');
audio.currentTime=2;nodes.get('b').onclick();assert(audio.paused);assert.equal(audio.currentTime,2);nodes.get('b').onclick();assert(!audio.paused);
nodes.get('original').onclick();assert.equal(audio.currentTime,0);assert.equal(run('active'),'original');
nodes.get('voteA').onclick();nodes.get('dropC').onclick();nodes.get('tie').onclick();assert.equal(run('state().eliminate'),'');assert.equal(run('feedback().results[0].survivors.length'),3);
nodes.get('dropB').onclick();assert.equal(run('state().winner'),'');nodes.get('voteA').onclick();nodes.get('next').onclick();assert.equal(run('n'),1);assert.equal(audio.currentTime,0);assert(audio.paused);
assert(nodes.get('voteA').disabled);nodes.get('voteA').onclick();assert.equal(run('state().winner'),'');
assert.equal(run('feedback().results[0].submitted'),true);assert.equal(run('feedback().results[0].candidate_versions[0].identity'),'0A');assert.equal(run('feedback().results[1].reviewable'),false);
run('show(2)');assert(nodes.get('b').disabled);assert(nodes.get('voteA').hidden);nodes.get('rating').value='4';nodes.get('rating').onchange();nodes.get('next').onclick();assert.equal(run('feedback().results[2].rating'),4);assert.equal(run('feedback().results[2].winner'),'');assert.equal(run('feedback().results[2].survivors.length'),1);
assert.equal(run('n'),3);assert(nodes.get('dropA').hidden);assert(nodes.get('dropA').disabled);nodes.get('voteA').onclick();nodes.get('dropB').onclick();nodes.get('next').onclick();assert.equal(run('feedback().results[3].submitted'),true);assert.equal(run('feedback().results[3].eliminate'),'');assert.equal(run('feedback().results[3].survivors.length'),2);
'''
    subprocess.run(['node','-e',script,str(path)],check=True,capture_output=True,text=True)
