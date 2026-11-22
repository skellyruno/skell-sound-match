#!/usr/bin/env python3
"""Apply a frozen experimental Skelly WAV-only recipe to a NEW dry vocal.

Requires only the learned JSON recipe, matching NPZ models, and source audio.
It does not load the original target, wet vocal, FL Studio project or preset.
Offline ONLY; this is not a native VST3 or realtime-safe DSP implementation.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import numpy as np
import soundfile as sf
from .wav_only_effect_match import read_audio, render_wet, safe_preview, file_hash, check_mono_compatible
from .skelly_reference_eq_trial import apply_eq, linked_leveler, CENTERS


def process(dry, sr, recipe: dict, models_dir: Path, widen=False):
    if recipe.get('schema') != 'skelly.wav-only.standalone-experiment.v1':
        raise ValueError('Unknown or incompatible recipe schema')
    if not np.isfinite(dry).all():
        raise ValueError('Nonfinite audio')
    check_mono_compatible(dry)
    main = recipe['main_model']
    if [float(i) for i in main['eq_centers_hz']] != [float(i) for i in CENTERS]:
        raise ValueError('EQ topology/version mismatch')
    coeffs = main['eq_gain_db']
    slope, tau = float(main['leveler_slope']), float(main['leveler_tau_s'])
    gain_db = float(main['train_only_output_gain_db'])
    if not np.isfinite(coeffs).all() or not math.isfinite(gain_db) or abs(gain_db)>24:
        raise ValueError('Unsafe recipe values')
    core,_ = linked_leveler(apply_eq(dry,sr,coeffs),sr,slope,tau)
    core *= 10**(gain_db/20)
    wet = np.zeros_like(core)
    used = []
    for m in recipe['stage_models']:
        name = m['name']
        if not name.replace('_','').isalnum():
            raise ValueError('Invalid model ID')
        path = (models_dir/f'{name}.npz').resolve()
        if path.parent != models_dir.resolve():
            raise ValueError('Model path escaped recipe directory')
        if not path.is_file() or file_hash(path)!=m['sha256']:
            raise ValueError(f'Absent or modified stage model {name}')
        with np.load(path) as archive:
            model_sr=int(archive['sample_rate'])
            impulse=np.asarray(archive['impulse'],dtype=np.float64)
        if model_sr!=sr or impulse.ndim!=2 or impulse.shape[1]!=dry.shape[1] or len(impulse)>3*sr+2048 or not np.isfinite(impulse).all():
            raise ValueError(f'Unsupported stage model: {name}')
        g=float(m['mixer_gain'])
        if not math.isfinite(g) or not 0<=g<=2:
            raise ValueError('Invalid mixer gain')
        wet += g*render_wet(core,impulse)
        used.append(name)
    signal = core+wet
    if widen:
        if recipe['target']!='speakerz' or 'stereo_widening_train_m_s_matrix' not in recipe:
            raise ValueError('No trained stereo-width routing in this recipe')
        weights=np.asarray(recipe['stereo_widening_train_m_s_matrix'],dtype=np.float64)
        if weights.shape!=(2,2) or not np.isfinite(weights).all() or np.max(np.abs(weights))>3 or signal.shape[1]!=2:
            raise ValueError('Unsupported stereo-width matrix')
        mid=(signal[:,0]+signal[:,1])/2
        side=(signal[:,0]-signal[:,1])/2
        transformed=np.stack([mid,side],axis=1)@weights
        signal=np.stack([transformed[:,0]+transformed[:,1],transformed[:,0]-transformed[:,1]],axis=1)
    output,safety=safe_preview(signal,-1.2)
    return output,{'used_stages':used,'widen':widen,'sample_rate':sr,'frames':len(dry),**safety}


def render_file(source:Path,recipe_file:Path,models_dir:Path,output:Path,widen=False,report:Path|None=None):
    used_paths=[source.resolve(),recipe_file.resolve(),output.resolve()]
    if report is not None:used_paths.append(report.resolve())
    if len(set(used_paths)) != len(used_paths):
        raise ValueError('File path collision')
    if output.exists() or (report is not None and report.exists()):
        raise FileExistsError('Refusing to overwrite existing output')
    dry,sr=read_audio(source)
    recipe=json.loads(recipe_file.read_text(encoding='utf8'))
    signal,meta=process(dry,sr,recipe,models_dir,widen)
    output.parent.mkdir(parents=True,exist_ok=True)
    sf.write(output,signal,sr,subtype='PCM_24')
    meta.update({'source_sha256':file_hash(source),'recipe_sha256':file_hash(recipe_file),
                 'source_file':source.name,'output_file':output.name,'target_id':recipe['target'],
                 'status':'experimental_not_approved_not_native_vst3',
                 'independent_take_similarity':'UNVERIFIED'})
    if report is not None:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
    return meta


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dry_source',type=Path)
    p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--models',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--report',type=Path)
    p.add_argument('--widen',action='store_true')
    args=p.parse_args()
    print(json.dumps(render_file(args.dry_source,args.recipe,args.models,args.output,args.widen,args.report),indent=2))
if __name__=='__main__':main()
