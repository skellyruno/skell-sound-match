"""Regression coverage for scalable WAV-only batch intake, safety and caching."""
import io
import json
import sys
import zipfile
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
from skell_sound_match.wav_only.skelly_bulk_match import (infer, open_db, scan_archives, select_plan, items, materialize,
     windows_for, safe_slug, apply_saved_recipe, apply_many)

@pytest.mark.parametrize('filename,target,role',[
    ('speakerz dry.wav','speakerz','dry'),
    ('speakerz main .wav','speakerz','main'),
    ('speakerz main + 47% separated .wav','speakerz','main_width'),
    ('speakerz everything + 47% stereo separated.wav','speakerz','all_width'),
    ('speakerz main + delay.wav','speakerz','delay'),
    ('speakerz main convolver.wav','speakerz','convolver'),
    ('HOP OUT.wav','hop_out','unknown'),
    ('HOP OUT MAIN DRY.wav','hop_out','main'),
    ('HOP OUT MAIN REV.wav','hop_out','reverb'),
    ('HOP OUT MAIN CHORUS.wav','hop_out','chorus'),
    ('Alchemist REC Printed.wav','alchemist','rec'),
    ('Deuce main only.wav','deuce','main'),
])
def test_stage_name_inference(filename,target,role):
    assert infer(filename)==(target,role)


def audio_bytes(seconds=2,sr=44100,tone=300):
    t=np.arange(sr*seconds)/sr
    x=np.stack((.05*np.sin(t*2*np.pi*tone),)*2,axis=1)
    f=io.BytesIO();sf.write(f,x,sr,format='WAV',subtype='PCM_24')
    return f.getvalue()


def fixture_zip(tmp_path):
    zpath=tmp_path/'session.zip'
    with zipfile.ZipFile(zpath,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('HOP OUT.wav',audio_bytes())
        z.writestr('HOP OUT MAIN DRY.wav',audio_bytes(tone=320))
        z.writestr('HOP OUT MAIN REV.wav',audio_bytes(tone=320))
    return zpath


def test_scan_resume_and_unlabeled_source_heuristic(tmp_path):
    zpath=fixture_zip(tmp_path)
    db=open_db(tmp_path/'work')
    original=zpath.read_bytes()
    s=scan_archives([zpath],tmp_path/'work',db)
    assert s['new_or_changed_archives']==1
    rows=items(db)
    assert len(rows)==3
    plan=select_plan(rows)
    assert len(plan)==1 and plan[0]['status']=='READY_FOR_MAIN_FIT'
    assert plan[0]['target_id']=='hop_out'
    s2=scan_archives([zpath],tmp_path/'work',db)
    assert s2['unchanged_skipped']==1
    assert zpath.read_bytes()==original
    row=plan[0]['dry']
    a=materialize(row,tmp_path/'work')
    assert a.exists()
    # Tampering with extracted cache is rejected and cannot corrupt source ZIP.
    a.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='Cache hash mismatch'):
        materialize(row,tmp_path/'work')
    assert zpath.read_bytes()==original


def test_duplicate_content_deduplicated_while_retaining_provenance(tmp_path):
    z=tmp_path/'dupes.zip'
    with zipfile.ZipFile(z,'w') as a:
        a.writestr('other dry.wav',audio_bytes())
        a.writestr('other main.wav',audio_bytes())
        a.writestr('other main + delay.wav',audio_bytes(tone=350))
    db=open_db(tmp_path/'catalog')
    scan_archives([z],tmp_path/'catalog',db)
    rows=items(db)
    assert len(rows)==3
    assert len({r['sha256'] for r in rows})==2
    assert select_plan(rows)[0]['status']=='READY_FOR_MAIN_FIT'


def test_ambiguous_dry_sources_require_review(tmp_path):
    z=tmp_path/'two.zip'
    with zipfile.ZipFile(z,'w') as a:
        a.writestr('star dry.wav',audio_bytes(tone=300))
        a.writestr('star raw.wav',audio_bytes(tone=310))
        a.writestr('star main.wav',audio_bytes(tone=330))
    db=open_db(tmp_path/'catalog')
    scan_archives([z],tmp_path/'catalog',db)
    assert select_plan(items(db))[0]['status']=='AMBIGUOUS_TAKES'


def test_zip_traversal_rejected_and_previous_catalog_not_clobbered(tmp_path):
    valid=fixture_zip(tmp_path)
    db=open_db(tmp_path/'catalog')
    scan_archives([valid],tmp_path/'catalog',db)
    z=tmp_path/'unsafe.zip'
    with zipfile.ZipFile(z,'w') as a:a.writestr('../evil.wav',audio_bytes())
    with pytest.raises(ValueError,match='Unsafe member'):
        scan_archives([z],tmp_path/'catalog',db)
    assert len(items(db))==3
    assert not (tmp_path/'evil.wav').exists()


def test_audio_window_selected_from_active_not_silent_tail(tmp_path):
    sr=44100; t=np.arange(sr*15)/sr
    x=.04*np.sin(2*np.pi*340*t)
    source=np.concatenate([x,np.zeros(sr*20)])
    cand=np.concatenate([x*.8,np.zeros(sr*20)])
    a=tmp_path/'dry.wav';b=tmp_path/'main.wav'
    sf.write(a,source,sr);sf.write(b,cand,sr)
    train,hold,diagnostic=windows_for(a,b)
    assert hold[1]<16
    assert train[1]<hold[0]
    assert diagnostic['alignment']=='plausible_zero_offset_not_proven'


def test_batch_main_recipe_does_not_overwrite(tmp_path):
    src=tmp_path/'dry.wav'
    sf.write(src,np.ones((44100,1))*.002,44100)
    r=tmp_path/'recipe.json'
    r.write_text(json.dumps({'schema':'skelly.wav-only.batch-main.v1','sample_rate':44100,
            'eq_gain_db':[0]*8,'leveler':{'slope':0.,'envelope_tau_s':.025}}))
    target=tmp_path/'render.flac'
    out=apply_saved_recipe(src,r,target)
    assert out['status']=='offline_experiment_not_native_or_owner_approved'
    assert target.exists()
    with pytest.raises(FileExistsError):apply_saved_recipe(src,r,target)


def _private_fake_recipe_root(tmp_path):
    from skell_sound_match.wav_only.wav_only_effect_match import file_hash
    kit=tmp_path/'private_kit'
    (kit/'reports').mkdir(parents=True)
    (kit/'recipes').mkdir()
    sr=44100
    np.savez_compressed(kit/'recipes'/'echo.npz',
                        impulse=np.array([[.08,.04]],dtype=np.float64),
                        sample_rate=np.array(sr))
    recipe={
        'schema':'skelly.wav-only.standalone-experiment.v1',
        'target':'speakerz',
        'main_model':{
            'eq_centers_hz':[100,220,470,1000,2100,4300,8000,13000],
            'eq_gain_db':[0.]*8,'leveler_slope':0.,'leveler_tau_s':.025,
            'train_only_output_gain_db':0.},
        'stage_models':[{'name':'echo','sha256':file_hash(kit/'recipes'/'echo.npz'),
                         'mixer_gain':.25}]
    }
    (kit/'reports'/'speakerz_source_only_chain.json').write_text(json.dumps(recipe))
    return kit


def test_batch_saved_replay_and_resume(tmp_path):
    src=tmp_path/'fresh dry.wav'
    sr=44100
    sf.write(src,np.stack([np.sin(np.arange(sr*3)*2*np.pi*300/sr)*.02]*2,axis=1),sr)
    outdir=tmp_path/'previews'
    private_kit=_private_fake_recipe_root(tmp_path)
    a=apply_many(None,[src],['speakerz'],outdir,recipe_root=private_kit)
    assert a[0]['status']=='OFFLINE_PREVIEW_ONLY'
    b=apply_many(None,[src],['speakerz'],outdir,recipe_root=private_kit)
    assert b[0]['status']=='CACHED_UNCHANGED'
    Path(a[0]['output']).write_bytes(b'tampered')
    c=apply_many(None,[src],['speakerz'],outdir,recipe_root=private_kit)
    assert c[0]['status']=='OUTPUT_COLLISION_REVIEW'


def test_batch_requires_private_recipes(tmp_path):
    with pytest.raises(ValueError,match='Private recipe root'):
        apply_many(None,[],['speakerz'],tmp_path/'previews')


def test_slug_and_unknown_model_safe(tmp_path):
    assert safe_slug('../../SOMETHING')=='something'
    src=tmp_path/'dry.wav';sf.write(src,np.zeros((44100*3,1)),44100)
    r=apply_many(None,[src],['missing-preset'],tmp_path/'outs',recipe_root=_private_fake_recipe_root(tmp_path))
    assert r[0]['status']=='UNKNOWN_OR_UNFROZEN_PRESET'


def test_batch_discovery_uses_only_private_recipe_root(tmp_path):
    kit=_private_fake_recipe_root(tmp_path)
    src=tmp_path/'dry.wav'
    sr=44100
    y=np.sin(np.arange(sr*2)*2*np.pi*310/sr)*.01
    sf.write(src,np.stack([y,y],axis=1),sr)
    res=apply_many(None,[src],['all'],tmp_path/'preview',recipe_root=kit)
    assert len(res)==1 and res[0]['preset']=='speakerz'
    assert res[0]['status']=='OFFLINE_PREVIEW_ONLY'
    with pytest.raises(ValueError,match='Use --presets all alone'):
        apply_many(None,[src],['all','speakerz'],tmp_path/'other',recipe_root=kit)
    with pytest.raises(ValueError,match='No private frozen'):
        apply_many(None,[src],['all'],tmp_path/'third',recipe_root=tmp_path)
