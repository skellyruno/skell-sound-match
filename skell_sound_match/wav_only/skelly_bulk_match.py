#!/usr/bin/env python3
"""Private, incremental, multi-preset audio-only intake + offline research.

No private files are uploaded. Names are heuristics, not verified provenance.
Presets are always experimental until independent-take and owner listening tests.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
import sqlite3
import sys
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
from .skelly_reference_eq_trial import match, apply_eq, linked_leveler, truepeak
from .wav_only_effect_match import write_model_and_preview, file_hash, safe_preview

MAX_MEMBER_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
MAX_ENTRIES = 4000
SOURCE_EXT = {'.wav', '.flac'}
LABELS = {'delay':'delay','del':'delay','echo':'delay','rev':'reverb','reverb':'reverb',
          'chorus':'chorus','flangus':'flangus','flanger':'flangus',
          'convolver':'convolver','convolution':'convolver',
          'all':'all','everything':'all','full':'all','combined':'all',
          'main':'main','dry':'dry','raw':'dry','unprocessed':'dry',
          'wet':'wet','reference':'reference','rec':'rec','recording':'rec'}
REMOVE_WORDS = set(LABELS) | {'47','percent','separated','stereo','with','only','vocal','vocals','fx','effects','print','printed','mix','mixed','processed','audio','stem','take'}
ALIASES = {'hop out':'hop_out','hopout':'hop_out','speakerz':'speakerz','alchemist':'alchemist','deuce':'deuce'}


def sha256_stream(f):
    h=hashlib.sha256()
    while True:
        block=f.read(1 << 20)
        if not block:break
        h.update(block)
    return h.hexdigest()


def canonical(txt):
    txt=unicodedata.normalize('NFKC',txt).lower()
    return re.findall(r'[a-z0-9]+',txt)


def infer(path, parent=''):
    """Produce conservative target / role hints; never claim chain provenance."""
    t=canonical(Path(path).stem)
    set_t=set(t)
    if 'main' in set_t and set_t.intersection({'dry','raw'}):role='main'
    elif 'all' in set_t or 'everything' in set_t or ('full' in set_t and 'combined' in set_t):role='all'
    elif 'delay' in set_t or 'del' in set_t or 'echo' in set_t:role='delay'
    elif 'reverb' in set_t or 'rev' in set_t:role='reverb'
    elif 'chorus' in set_t:role='chorus'
    elif 'flangus' in set_t or 'flanger' in set_t:role='flangus'
    elif 'convolver' in set_t or 'convolution' in set_t:role='convolver'
    elif 'main' in set_t:role='main'
    elif set_t.intersection({'dry','raw','unprocessed'}):role='dry'
    elif set_t.intersection({'rec','recording'}):role='rec'
    elif set_t.intersection({'wet','reference'}):role='reference'
    else:role='unknown'
    if '47' in set_t and set_t.intersection({'separated','stereo'}) and role in {'main','all'}:
        role += '_width'
    leftovers=[tok for tok in t if tok not in REMOVE_WORDS]
    pwords=[tok for tok in canonical(parent) if tok not in REMOVE_WORDS]
    # generic file names like dry.wav get identity from directory, not called "dry".
    if not leftovers and pwords:leftovers=pwords
    name=' '.join(leftovers) or Path(path).stem.lower()
    for alias, slug in sorted(ALIASES.items(),key=lambda z:-len(z[0])):
        if name==alias or name.startswith(alias+' '):
            if name==alias:return slug,role
            suffix=name[len(alias):].strip()
            if suffix in {'1','2','3'}:return slug+'_'+suffix,role
    return safe_slug(name),role


def safe_slug(text):
    s='_'.join(canonical(text))
    return (s[:72].strip('_') or 'unidentified')


def open_db(workspace):
    workspace.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(workspace/'catalog.sqlite3')
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS archives (path TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, scanned TEXT NOT NULL)')
    db.execute('''CREATE TABLE IF NOT EXISTS items (
       archive TEXT NOT NULL, member TEXT NOT NULL, sha256 TEXT NOT NULL,
       bytes INTEGER NOT NULL, sample_rate INTEGER NOT NULL, channels INTEGER NOT NULL,
       frames INTEGER NOT NULL, target_id TEXT NOT NULL, role TEXT NOT NULL,
       file_kind TEXT NOT NULL, PRIMARY KEY (archive,member))''')
    db.commit()
    return db


def zip_fingerprint(path):
    stat=path.stat()
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)>MAX_ENTRIES:raise ValueError('Archive has too many members')
        if sum(x.file_size for x in infos)>MAX_ARCHIVE_BYTES:raise ValueError('Archive uncompressed size exceeds guard')
        parts=[(i.filename,i.CRC,i.file_size,i.compress_size,i.header_offset) for i in infos]
    h=hashlib.sha256(json.dumps(parts,ensure_ascii=False).encode()).hexdigest()
    return f'{stat.st_size}:{stat.st_mtime_ns}:{h}'


def _assert_zip_member(info):
    if info.is_dir():return False
    if info.file_size>MAX_MEMBER_BYTES:raise ValueError(f'Member over 256 MB: {info.filename}')
    if info.flag_bits & 1:raise ValueError('Encrypted ZIP member unsupported')
    if info.file_size>10_000_000 and info.compress_size and info.file_size/info.compress_size>2000:
        raise ValueError(f'Extreme compression ratio: {info.filename}')
    pp=Path(info.filename.replace('\\','/'))
    if pp.is_absolute() or '..' in pp.parts or info.filename.startswith(('/', '\\')):
        raise ValueError(f'Unsafe member path: {info.filename}')
    return True


def scan_file(f, kind, name, parent):
    try:
        info=sf.info(f)
        if info.samplerate<32000 or info.samplerate>192000 or info.channels not in (1,2) or info.frames<info.samplerate:
            return None
        f.seek(0)
        sha=sha256_stream(f)
        target,role=infer(name,parent)
        return {'sha256':sha,'sample_rate':info.samplerate,'channels':info.channels,
                'frames':info.frames,'target_id':target,'role':role,'file_kind':kind}
    except (RuntimeError,ValueError,OSError) as ex:
        return {'error':str(ex)}


def scan_archives(inputs, workspace, db):
    count_new=0; count_skip=0; warnings=[]
    for raw in inputs:
        p=Path(raw).expanduser().resolve()
        if p.is_dir():
            found=sorted(y for y in p.rglob('*') if y.is_file() and y.suffix.lower() in SOURCE_EXT|{'.zip'})
        else:found=[p]
        for item in found:
            if not item.is_file():warnings.append(f'Not found: {item}');continue
            if item.suffix.lower() not in SOURCE_EXT|{'.zip'}:continue
            archive=str(item)
            if item.suffix.lower()=='.zip':
                fp=zip_fingerprint(item)
            else:
                st=item.stat();fp=f'{st.st_size}:{st.st_mtime_ns}'
            old=db.execute('SELECT fingerprint FROM archives WHERE path=?',(archive,)).fetchone()
            if old and old['fingerprint']==fp:
                count_skip+=1;continue
            fresh=[]
            if item.suffix.lower()=='.zip':
                with zipfile.ZipFile(item) as z:
                    for info in z.infolist():
                        if not _assert_zip_member(info):continue
                        if Path(info.filename).suffix.lower() not in SOURCE_EXT:continue
                        with z.open(info) as f:
                            meta=scan_file(f,Path(info.filename).suffix.lower(),Path(info.filename).name,Path(info.filename).parent.name)
                        if not meta:continue
                        if 'error' in meta:warnings.append(f'{item.name}:{info.filename}: {meta["error"]}');continue
                        fresh.append((archive,info.filename,meta['sha256'],info.file_size,
                              meta['sample_rate'],meta['channels'],meta['frames'],meta['target_id'],meta['role'],meta['file_kind']))
            else:
                with item.open('rb') as f:meta=scan_file(f,item.suffix.lower(),item.name,item.parent.name)
                if meta and 'error' not in meta:
                    fresh.append((archive,'',meta['sha256'],item.stat().st_size,meta['sample_rate'],
                        meta['channels'],meta['frames'],meta['target_id'],meta['role'],meta['file_kind']))
                elif meta and 'error' in meta:warnings.append(f'{item.name}: {meta["error"]}')
            # Only replace one archive's entries after the full successful iteration.
            with db:
                db.execute('DELETE FROM items WHERE archive=?',(archive,))
                db.executemany('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?)',fresh)
                db.execute("INSERT OR REPLACE INTO archives VALUES(?,?,datetime('now'))",(archive,fp))
            count_new+=1
    return {'new_or_changed_archives':count_new,'unchanged_skipped':count_skip,'warnings':warnings}


def items(db):return [dict(r) for r in db.execute('SELECT * FROM items ORDER BY target_id,role,archive,member')]


def select_plan(rows):
    grouped=defaultdict(list)
    for row in rows:grouped[row['target_id']].append(row)
    planned=[]
    for target, group in sorted(grouped.items()):
        by_role=defaultdict(list)
        for row in group:by_role[row['role']].append(row)
        def choose(role):
            unique={x['sha256']:x for x in by_role.get(role,[])}
            return list(unique.values())
        dry,main=choose('dry'),choose('main')
        # The unadorned base recording (e.g. HOP OUT.wav) is a defensible
        # candidate source when one explicitly marked MAIN print exists.
        # Keep its provenance unverified; never infer from arbitrary UNKNOWNs.
        if not dry and len(main)==1:
            naked=[x for x in by_role.get('unknown',[])
                   if safe_slug(Path(x['member'] or x['archive']).stem)==target]
            if len({x['sha256'] for x in naked})==1:
                dry=list({x['sha256']:x for x in naked}.values())
        status='READY_FOR_MAIN_FIT' if len(dry)==len(main)==1 else 'REVIEW_NEEDED'
        if not dry: status='NEEDS_DRY_PRINT'
        if not main:status='NEEDS_MAIN_PRINT'
        if len(dry)>1 or len(main)>1:status='AMBIGUOUS_TAKES'
        if dry and main and status=='READY_FOR_MAIN_FIT':
            if (dry[0]['frames'],dry[0]['sample_rate'],dry[0]['channels']) != (
                 main[0]['frames'],main[0]['sample_rate'],main[0]['channels']):status='MISMATCHED_FORMAT_OR_LENGTH'
        stage_names=sorted(set(row['role'] for row in group)-{'dry','main'})
        planned.append({'target_id':target,'status':status,'dry':dry[0] if len(dry)==1 else None,
                 'main':main[0] if len(main)==1 else None,'stage_roles':stage_names,
                 'files':len(group),'unique_hashes':len({x['sha256'] for x in group}),
                 'source_evidence':'filename-and-format-only; verify same performance and zero offset'})
    return planned


def write_catalog(workspace,db,scanned):
    rows=items(db); plan=select_plan(rows)
    summary={'schema':'skelly.private.bulk-audio-intake.v1','source':'local_private_workspace',
           'cataloged_files':len(rows),'unique_audio_blobs':len({r['sha256'] for r in rows}),
           'groups':len(plan),'scan':scanned,'targets':plan,
           'unverified':['Archive name does not prove artist, settings, same take or original chain',
                         'Main/FX role is inferred from filenames; review anomalies before promotion',
                         'No existing or new factory program overwritten']}
    (workspace/'BATCH_CATALOG.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    with (workspace/'AUDIO_INDEX.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=['target_id','role','archive','member','sha256','bytes','sample_rate','channels','frames','file_kind'])
        w.writeheader();w.writerows(rows)
    lines=['# Private Skelly bulk matching work queue','',f"{len(rows)} indexed files, {summary['unique_audio_blobs']} unique hashes, {len(plan)} targets.\n",
           '| Target | State | Files | Unique | Stage prints |','|---|---|---:|---:|---|']
    for t in plan:
        lines.append(f"| {t['target_id']} | {t['status']} | {t['files']} | {t['unique_hashes']} | {', '.join(t['stage_roles']) or '—'} |")
    lines+=['','All roles are inferred from filenames and formats; no independent sound-match approval.',
            'Original ZIPs untouched; isolated matching reports go into fits/<target_id>/.']
    (workspace/'WORK_QUEUE.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return summary


def materialize(row,workspace):
    objdir=workspace/'private_audio_cache'
    objdir.mkdir(exist_ok=True)
    path=objdir/(row['sha256']+row['file_kind'])
    if path.exists():
        if file_hash(path)!=row['sha256']:raise ValueError('Cache hash mismatch')
        return path
    src=Path(row['archive'])
    if not src.is_file():raise FileNotFoundError(f'Original upload unavailable: {src}')
    tmp=path.with_suffix(path.suffix+'.partial')
    if tmp.exists():tmp.unlink()
    try:
        if row['member']:
            with zipfile.ZipFile(src) as z, z.open(row['member']) as s, tmp.open('xb') as d:
                while True:
                    chunk=s.read(1<<20)
                    if not chunk:break
                    d.write(chunk)
        else:
            with src.open('rb') as s,tmp.open('xb') as d:
                while True:
                    chunk=s.read(1<<20)
                    if not chunk:break
                    d.write(chunk)
        if file_hash(tmp)!=row['sha256']:raise ValueError('Source changed since scan')
        tmp.replace(path)
        return path
    finally:
        if tmp.exists():tmp.unlink()


def windows_for(source_path, target_path):
    import soundfile as sf
    a,sr=sf.read(source_path,always_2d=True,dtype='float32')
    b,sr2=sf.read(target_path,always_2d=True,dtype='float32')
    if sr!=sr2 or a.shape!=b.shape:raise ValueError('Rate/shape differ')
    # Evaluate activity of the presumed dry, avoiding silent post-vocal tails.
    win=max(1,round(sr*.1));n=len(a)//win
    if n<80:raise ValueError('Need ~8s of vocal to make a reliable temporal holdout')
    rms=np.sqrt(np.mean(a[:n*win].reshape(n,win,-1).astype('float64')**2,axis=(1,2)))
    th=max(float(rms.max())*.06,1.0e-4)
    idx=np.flatnonzero(rms>th)
    if len(idx)<30:raise ValueError('Too little active dry vocal for automatic split')
    active_s=min((idx[-1]+1)*win/sr,len(a)/sr)
    if active_s<9:raise ValueError('Insufficient active vocal for fixed train/holdout')
    train=(max(.3,round(active_s*.06,2)),round(active_s*.43,2))
    hold=(round(active_s*.53,2),round(active_s*.91,2))
    if train[1]-train[0]<2.5 or hold[1]-hold[0]<2.5:raise ValueError('Insufficient active split')
    # Diagnostic only. Large lag could invalidate same-take comparisons.
    # Decimate for cheap lag check; independent original clips need manual verification.
    start=int(.1*sr);end=min(len(a),start+int(3*sr))
    x=a[start:end].mean(axis=1)[::8].astype('float64')
    y=b[start:end].mean(axis=1)[::8].astype('float64')
    x-=x.mean();y-=y.mean()
    maxlag=round(.08*sr/8)
    corr=signal.correlate(y,x,mode='full',method='fft')
    lags=signal.correlation_lags(len(y),len(x),mode='full')
    mask=np.abs(lags)<=maxlag
    best=np.argmax(np.abs(corr[mask]));lag=int(lags[mask][best]*8)
    ref=math.sqrt(float(np.dot(x,x)*np.dot(y,y)))
    confidence=float(np.max(np.abs(corr[mask]))/max(ref,1e-12))
    return train, hold, {'activity_end_s':round(active_s,3),'estimated_lag_samples_8step':lag,
                          'band_unfiltered_abs_correlation':round(confidence,5),
                          'alignment':('UNVERIFIED' if abs(lag)>round(sr*.025) or confidence<.2 else
                            'small_processing_offset_not_corrected' if abs(lag)>16 else
                            'plausible_zero_offset_not_proven')}


def fit_targets(db, workspace, selected=None, effects=False, limit=None):
    plan=select_plan(items(db)); result=[]
    todo=[x for x in plan if not selected or x['target_id'] in selected]
    if limit:todo=todo[:limit]
    for t in todo:
        target=t['target_id'];folder=workspace/'fits'/safe_slug(target);folder.mkdir(parents=True,exist_ok=True)
        if t['status']!='READY_FOR_MAIN_FIT':
            result.append({'target':target,'status':t['status']});continue
        dry,main=t['dry'],t['main']
        marker=hashlib.sha256((dry['sha256']+main['sha256']+'auto-main-v1').encode()).hexdigest()
        report=folder/f'main_{marker[:16]}.json'; recipe=folder/f'recipe_{marker[:16]}.json'
        if report.exists() and recipe.exists():
            result.append({'target':target,'status':'CACHED_MAIN_FIT','report':str(report),'recipe':str(recipe)})
        else:
            try:
                source=materialize(dry,workspace);wet=materialize(main,workspace)
                train,hold,al=windows_for(source,wet)
                if al['alignment']=='UNVERIFIED':
                    result.append({'target':target,'status':'NEEDS_ALIGNMENT_REVIEW','diagnostic':al});continue
                metrics=match(source,wet,train,hold)
                metrics['alignment_diagnostic']=al
                metrics['target_id']=target
                metrics['provenance']='INFERRED_BY_FILENAME; not independently confirmed'
                holdm=metrics['scores']['holdout']
                improved=holdm['combined_mean_abs_band_db']<holdm['baseline_mean_abs_band_db'] and holdm['combined_envelope_200ms_mae_db']<holdm['baseline_envelope_200ms_mae_db']
                metrics['both_holdout_metrics_improved']=improved
                recipe_content={'schema':'skelly.wav-only.batch-main.v1','target_id':target,
                         'sample_rate':dry['sample_rate'],'train_s':train,'holdout_s':hold,
                         'source_sha256':dry['sha256'],'main_reference_sha256':main['sha256'],
                         'eq_centers_hz':metrics['centers_hz'],'eq_gain_db':metrics['gain_db'],
                         'leveler':metrics['training_selected_linked_leveler'],
                         'experimental_only':True,'both_holdout_metrics_improved':improved,
                         'provenance':'filenames_only','independent_performance_validated':False}
                report.write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf8')
                recipe.write_text(json.dumps(recipe_content,indent=2)+'\n',encoding='utf8')
                result.append({'target':target,'status':'FIT_NOT_APPROVED','report':str(report),
                               'recipe':str(recipe),'holdout':{k:holdm[k] for k in (
                                 'baseline_mean_abs_band_db','combined_mean_abs_band_db',
                                 'baseline_envelope_200ms_mae_db','combined_envelope_200ms_mae_db')},
                               'both_improved':improved})
            except (ValueError,OSError,FloatingPointError) as ex:
                result.append({'target':target,'status':'FAILED_OR_NEEDS_REVIEW','error':str(ex)})
                continue
        if effects:
            # Reference stage models are never auto-promoted into recipes.
            main_row=t['main']
            for stage in ('delay','reverb','convolver','flangus'):
                candidates=[r for r in items(db) if r['target_id']==target and r['role']==stage]
                if len({x['sha256'] for x in candidates})!=1:continue
                rr=candidates[0]; key=hashlib.sha256((main_row['sha256']+rr['sha256']+stage).encode()).hexdigest()[:16]
                model=folder/f'{stage}_{key}.npz'; stage_report=folder/f'{stage}_{key}.json'; preview=folder/f'{stage}_{key}.flac'
                if model.exists() and stage_report.exists() and preview.exists():continue
                try:
                    mpath=materialize(main_row,workspace);e=materialize(rr,workspace)
                    # Training FIRs require a prefix starting at 0; keep target holdout sealed.
                    tr,h,_=windows_for(mpath,e)
                    tr=(0.,max(5.,tr[1])); h=(max(tr[1]+.4,h[0]),h[1])
                    if h[1]-h[0]<1.:raise ValueError('Not enough stage holdout')
                    method='delay' if stage=='delay' else ('reverb' if stage=='reverb' else 'linear_fir')
                    out=write_model_and_preview(mpath,e,method,tr,h,model,stage_report,preview,
                              response_seconds=.85 if stage=='reverb' else .15 if stage=='flangus' else 1.)
                    result.append({'target':target,'effect':stage,'status':'STAGE_RESEARCH_PASS' if out['holdout_better_than_no_wet'] else 'STAGE_REJECTED','relative_holdout_error':out['scores']['holdout']['wet_relative_rms_error']})
                except (ValueError,OSError,FloatingPointError) as ex:
                    result.append({'target':target,'effect':stage,'status':'STAGE_FAILED','error':str(ex)})
    (workspace/'FIT_STATUS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


def apply_saved_recipe(source, recipe, out):
    if out.exists() or source.resolve()==out.resolve():raise FileExistsError('Cannot overwrite audio')
    x,sr=sf.read(source,always_2d=True,dtype='float64')
    if x.shape[1] not in (1,2) or not np.isfinite(x).all():raise ValueError('Bad input')
    config=json.loads(recipe.read_text())
    if config.get('schema')!='skelly.wav-only.batch-main.v1' or config['sample_rate']!=sr:
        raise ValueError('Recipe type or sample rate mismatch')
    y=apply_eq(x,sr,config['eq_gain_db'])
    lv=config['leveler'];y,_=linked_leveler(y,sr,lv['slope'],lv['envelope_tau_s'])
    y,meta=safe_preview(y,-1.2)
    out.parent.mkdir(parents=True,exist_ok=True)
    sf.write(out,y,sr,subtype='PCM_24')
    return {'source_sha256':file_hash(source),'recipe_sha256':file_hash(recipe),'preview':out.name,
            'true_peak_estimate_4x':meta,'status':'offline_experiment_not_native_or_owner_approved'}



def apply_many(workspace, source_paths, preset_ids, output_dir, catalog_dry=False, recipe_root=None):
    """Batch audition frozen standalone recipes against arbitrary dry WAVs.

    One new dry recording can render through every saved preset. Never uses a
    matching wet reference in application and never overwrites older previews.
    """
    from .apply_reconstructed_preset import render_file
    if recipe_root is None:
        raise ValueError('Private recipe root is required; the public repository ships no vocal-derived presets')
    kit=Path(recipe_root).expanduser().resolve()
    if not kit.is_dir():
        raise ValueError(f'Private recipe root does not exist: {kit}')
    if 'all' in preset_ids:
        if len(preset_ids) != 1:
            raise ValueError('Use --presets all alone or specify explicit preset IDs')
        preset_ids=sorted({p.name[:-len('_source_only_chain.json')]
            for p in (kit/'reports').glob('*_source_only_chain.json')})
        if not preset_ids:
            raise ValueError('No private frozen standalone recipes in recipe-root/reports')
    samples=[]
    for p in source_paths:
        p=Path(p).expanduser().resolve()
        if p.is_dir():samples.extend((q,None) for q in sorted(q for q in p.rglob('*') if q.suffix.lower() in SOURCE_EXT))
        elif p.is_file() and p.suffix.lower() in SOURCE_EXT:samples.append((p,None))
        else:raise ValueError(f'Expected WAV/FLAC input or folder: {p}')
    if catalog_dry:
        if workspace is None:raise ValueError('Catalog workspace is required')
        db=open_db(workspace)
        for target in select_plan(items(db)):
            if target['dry'] is not None:
                samples.append((materialize(target['dry'],workspace),target['target_id']+'_dry'))
    samples=list({str(x.resolve()):(x,label) for x,label in samples}.values())
    if not samples:raise ValueError('No dry recordings selected')
    output_dir.mkdir(parents=True,exist_ok=True)
    results=[]
    for src,source_label in samples:
        fingerprint=file_hash(src)
        for preset in preset_ids:
            name=safe_slug(preset)
            recipe=kit/'reports'/f'{name}_source_only_chain.json'
            if not recipe.exists():
                results.append({'source':src.name,'preset':name,'status':'UNKNOWN_OR_UNFROZEN_PRESET'})
                continue
            recipe_hash=file_hash(recipe)
            stem=f'{safe_slug(source_label or src.stem)[:40]}_{fingerprint[:10]}__{name}_{recipe_hash[:10]}'
            output=output_dir/(stem+'.flac');report=output_dir/(stem+'.json')
            if output.exists() or report.exists():
                if output.is_file() and report.is_file():
                    prev=json.loads(report.read_text())
                    if prev.get('source_sha256')==fingerprint and prev.get('recipe_sha256')==recipe_hash and \
                       prev.get('output_file')==output.name and file_hash(output)==prev.get('output_sha256'):
                        results.append({'source':src.name,'preset':name,'status':'CACHED_UNCHANGED', 'output':str(output)})
                        continue
                results.append({'source':src.name,'preset':name,'status':'OUTPUT_COLLISION_REVIEW','output':str(output)})
                continue
            try:
                # Render to temporary local private paths and validate before publication.
                meta=render_file(src,recipe,kit/'recipes',output,report=None)
                meta['output_sha256']=file_hash(output)
                report.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
                results.append({'source':src.name,'preset':name,'status':'OFFLINE_PREVIEW_ONLY','source_label':source_label or src.name,
                                'output':str(output),'estimated_4x_true_peak_dbtp':meta.get('estimated_true_peak_posttrim_dbtp')})
            except (ValueError,OSError,RuntimeError,KeyError) as ex:
                results.append({'source':src.name,'preset':name,'status':'FAILED_OR_INCOMPATIBLE','error':str(ex)})
    (output_dir/'BATCH_APPLY_STATUS.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
    return results


def cli():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    scan=sub.add_parser('scan',help='inventory ZIP(s) or folder(s) incrementally; no originals changed')
    scan.add_argument('inputs',type=Path,nargs='+');scan.add_argument('--workspace',type=Path,required=True)
    fst=sub.add_parser('fst-catalog',help='safely catalog FL Studio .fst effect labels from a ZIP')
    fst.add_argument('zip_file',type=Path)
    fst.add_argument('--output',type=Path,required=True)
    fit=sub.add_parser('fit',help='run main vocal matched-EQ/dynamics fit on all eligible targets')
    fit.add_argument('--workspace',type=Path,required=True);fit.add_argument('--target',action='append')
    fit.add_argument('--effects',action='store_true',help='also train time-invariant stage models (slow)')
    fit.add_argument('--limit',type=int)
    apply=sub.add_parser('apply-main',help='render frozen new main-only trial on a dry recording')
    apply.add_argument('input',type=Path);apply.add_argument('--recipe',required=True,type=Path)
    apply.add_argument('--output',required=True,type=Path)
    many=sub.add_parser('apply-many',help='play multiple existing frozen presets on new dry WAV/FLAC sources')
    many.add_argument('sources',type=Path,nargs='*',help='one or more dry WAVs or directories')
    many.add_argument('--presets',nargs='+',default=['all'],
                      help='preset IDs or all (discover private frozen standalone recipes)')
    many.add_argument('--output-dir',type=Path,required=True)
    many.add_argument('--workspace',type=Path,help='prior scanned database if using --from-catalog')
    many.add_argument('--recipe-root',type=Path,required=True,help='PRIVATE folder with reports/ recipes/; never committed')
    many.add_argument('--from-catalog',action='store_true',help='also use each target dry source from prior scan')
    args=parser.parse_args()
    if args.action=='fst-catalog':
        from .flstudio_preset_catalog import inspect_zip
        if args.output.exists():
            raise FileExistsError('Refusing to overwrite a preset catalog')
        if args.output.resolve()==args.zip_file.resolve():
            raise ValueError('Input/output collision')
        report=inspect_zip(args.zip_file)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        print(json.dumps({'fst_count':report['fst_count'],'report':str(args.output)}))
        return
    if args.action=='apply-many':
        print(json.dumps(apply_many(args.workspace,args.sources,args.presets,args.output_dir,args.from_catalog,args.recipe_root),indent=2));return
    if args.action=='apply-main':print(json.dumps(apply_saved_recipe(args.input,args.recipe,args.output),indent=2));return
    db=open_db(args.workspace)
    if args.action=='scan':
        scanned=scan_archives(args.inputs,args.workspace,db)
        summary=write_catalog(args.workspace,db,scanned)
        print(json.dumps({'new_or_changed_archives':scanned['new_or_changed_archives'],
          'unchanged_archives_skipped':scanned['unchanged_skipped'],
          'files':summary['cataloged_files'],'unique_hashes':summary['unique_audio_blobs'],
          'targets':[{k:q[k] for k in ('target_id','status','files','stage_roles')} for q in summary['targets']],
          'warnings':scanned['warnings']},indent=2))
    else:print(json.dumps(fit_targets(db,args.workspace,set(map(safe_slug,args.target or [])),args.effects,args.limit),indent=2))

if __name__=='__main__':cli()
