"""Native transport/provenance regressions; mock transport is not DSP evidence."""
import importlib.util
import json
from pathlib import Path
import sys
import os
import numpy as np
import pytest
import soundfile as sf

TOOLS = Path(__file__).resolve().parents[1] / 'tools'


@pytest.fixture
def common(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location('native_gate_common', TOOLS / 'native_gate_common.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_quiet_training_gain_and_silence_are_not_confused(common):
    t = np.arange(8000) / 8000
    voice = .01 * np.sin(2 * np.pi * 180 * t)
    source = np.column_stack((voice, voice))
    assert common.training_trim(source, source * 2) == pytest.approx(20 * np.log10(2))
    assert common.training_trim(source * 10, source * 20) == pytest.approx(20 * np.log10(2))
    with pytest.raises(ValueError, match='Insufficient active'):
        common.training_trim(source * 0, source)
    with pytest.raises(ValueError, match='positive aligned'):
        common.training_trim(source, -source)


def test_audio_snapshot_hashes_exact_decoded_bytes(common, tmp_path):
    file = tmp_path / 'source.wav'
    sf.write(file, np.ones(8000) * .01, 8000, subtype='FLOAT')
    data, rate, identity = common.audio_snapshot(file)
    assert data.shape == (8000, 2) and rate == 8000
    assert identity == common.digest(file)
    sf.write(file, np.zeros(8000), 8000, subtype='FLOAT')
    assert common.digest(file) != identity
    assert np.max(data) > 0


def test_pairing_rejects_equal_length_wrong_or_shifted_take(common):
    rng=np.random.default_rng(42);source=rng.normal(0,.1,(8000,2))
    assert common.verify_gate_pairing(source,source*1.2)['waveform_cosine']==pytest.approx(1)
    for target in (rng.normal(0,.1,source.shape),np.roll(source,16,axis=0),-source):
        with pytest.raises(ValueError,match='pairing'):
            common.verify_gate_pairing(source,target)


@pytest.mark.parametrize('fault', ['length', 'nan_samples', 'frames', 'latency', 'timing', 'binary'])
def test_renderer_rejects_bad_transport_and_changed_binary(common, tmp_path, monkeypatch, fault):
    executable = tmp_path / 'renderer'; executable.write_bytes(b'trusted executable')
    def call(args, **kwargs):
        if args[-1] == '--version':return 'club-gate-v1\n'
        source = np.fromfile(args[1], dtype=np.float32)
        if fault == 'length':source = source[:-2]
        if fault == 'nan_samples':source[0] = np.nan
        source.tofile(args[2])
        if fault == 'binary':executable.write_bytes(b'replaced executable')
        return json.dumps({'frames':False if fault == 'frames' else 100,
                           'latency_samples':1 if fault == 'latency' else 0,
                           'processing_seconds':float('nan') if fault == 'timing' else .001})
    monkeypatch.setattr(common.subprocess, 'check_output', call)
    engine = common.NativeRenderer(executable)
    with pytest.raises(ValueError):engine.render(np.ones((100,2),np.float32),44100,[-46,2,25,40,4],False)


def test_renderer_fails_before_executing_changed_identity(common, tmp_path, monkeypatch):
    file=tmp_path/'renderer';file.write_bytes(b'new binary')
    def unexpected(*args,**kwargs):raise AssertionError('Must reject hash before executing')
    monkeypatch.setattr(common.subprocess,'check_output',unexpected)
    with pytest.raises(ValueError,match='binary differs'):common.NativeRenderer(file,expected_hash='0'*64)


@pytest.mark.parametrize('bad', [{'finish':.5}, {'block':True}, {'input_db':float('nan')}, {'sr':44100.5}])
def test_renderer_never_coerces_invalid_report_parameters(common,tmp_path,monkeypatch,bad):
    file=tmp_path/'renderer';file.write_bytes(b'identity')
    monkeypatch.setattr(common.subprocess,'check_output',lambda *a,**k:'club-gate-v1\n')
    engine=common.NativeRenderer(file)
    values={'sr':44100,'parameters':[-46,2,25,40,4],'finish':False,**bad}
    with pytest.raises(ValueError,match='parameters'):
        engine.render(np.ones((100,2),np.float32),**values)


def test_later_validation_cannot_select_a_better_fallback(common,tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('fit_native_gate_under_test',TOOLS/'fit_native_gate.py')
    fitter=importlib.util.module_from_spec(spec);spec.loader.exec_module(fitter)
    frames=24000;split=int(frames*.6)
    source=tmp_path/'source.wav';target=tmp_path/'target.wav'
    sf.write(source,np.full((frames,2),.1,np.float32),8000,subtype='FLOAT')
    sf.write(target,np.full((frames,2),.1,np.float32),8000,subtype='FLOAT')
    class Transport:
        sha256='0'*64
        def __init__(self,*args,**kwargs):pass
        def check_identity(self):pass
        def render(self,x,sr,p,finish,**kwargs):
            z=x.copy()
            if p[0]==-46:z*=.5
            elif finish:z[:min(split,len(z))]*=.99
            elif len(z)==frames:z[split:]=0
            return z,{'processing_seconds':.001,'latency_samples':0}
    def optimize(objective,*args,**kwargs):
        from types import SimpleNamespace
        p=[-50,2,25,40,4]
        return SimpleNamespace(x=p,fun=objective(p))
    monkeypatch.setattr(fitter,'NativeRenderer',Transport)
    monkeypatch.setattr(fitter,'differential_evolution',optimize)
    report=fitter.fit('unused',source,target,tmp_path/'report.json',maxiter=0)
    assert report['results'][0]['train']<report['results'][1]['train']
    assert report['results'][0]['later']>report['results'][1]['later']
    assert report['selected_index']==0 and not report['listening_eligible']
    assert report['results'][1]['listening_eligible']


@pytest.mark.skipif(not os.environ.get('SKELL_NATIVE_GATE_RENDERER'),reason='Pinned native renderer not supplied')
def test_actual_native_quiet_fit_and_float_wav_replay(common,tmp_path):
    import fit_native_gate
    import replay_native_gate
    sr=8000;t=np.arange(sr*3)/sr
    x=np.column_stack([.01*np.sin(2*np.pi*180*t)]*2).astype(np.float32)
    source=tmp_path/'source.wav';target=tmp_path/'target.wav';report=tmp_path/'fit.json';output=tmp_path/'replay.wav'
    sf.write(source,x,sr,subtype='FLOAT');sf.write(target,x*2,sr,subtype='FLOAT')
    exe=os.environ['SKELL_NATIVE_GATE_RENDERER']
    result=fit_native_gate.fit(exe,source,target,report,maxiter=0)
    assert result['results'][0]['output_db']==pytest.approx(6.020599913,abs=1e-5)
    identity=replay_native_gate.replay(exe,source,report,output)
    data,_=sf.read(output,dtype='float32',always_2d=True)
    assert common.hashlib.sha256(data.tobytes()).hexdigest()==identity
    with pytest.raises(FileExistsError):replay_native_gate.replay(exe,source,report,output)
