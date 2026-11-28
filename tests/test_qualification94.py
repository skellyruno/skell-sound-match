import numpy as np,pytest
from skell_sound_match.wav_only import qualification94 as q,covariance94 as c

def sample(n=65536):return np.random.default_rng(94).normal(0,.03,(n,2)).astype('f')
def metric(a,b):return dict(score=float(np.sqrt(np.mean((a-b)**2))),tone=0.)
def test_split_guard():
    v=q.PairPlan.chronological(0,100000);assert v.audit==slice(70000,100000);assert v.fit.stop<v.selection.start<v.selection.stop<v.audit.start
    with pytest.raises(ValueError):q.PairPlan.chronological(0,10000)
def test_frozen_threshold():
    r=dict(score44=1.5,score48=1.5,peak44=-1,peak48=-1,stress44=0,stress48=0);assert q.classify(r,2)['qualified'];r['score48']=1.501;assert not q.classify(r,2)['qualified'];r['score48']=1.5;r['stress44']=.001;assert not q.classify(r,2)['improved'];r.pop('peak44')
    with pytest.raises(ValueError):q.classify(r,2)
def test_target_future_independent_selection():
    x=sample(100000);y=x*.9;t=x.copy();v=q.PairPlan.chronological(0,len(x));a=q.selection_profile(x,y,t,v,metric);t[v.audit]*=50;b=q.selection_profile(x,y,t,v,metric);assert a==b and a['has_active']
def test_audit_dry_only_and_stress():
    x=sample();v=q.PairPlan.chronological(0,len(x));calls=[]
    def render(a):calls.append(a.copy());return a
    y,r=q.audit(render,x,x,v,metric,b'frozen',1.);assert len(calls)==4;np.testing.assert_array_equal(calls[0],x);np.testing.assert_allclose(calls[2],x*10**.3);assert r['safe'] and r['qualified'] and q.audio_hash(y)==r['output_pcm_sha256'];assert r['recipe_sha256']!=q.audio_hash(y)
def test_bad_audio():
    x=sample();v=q.PairPlan.chronological(0,len(x))
    with pytest.raises(ValueError):q.audit(lambda a:a[:-1],x,x,v,metric,b'frozen',1.)
    with pytest.raises(ValueError):q.validate_audio(np.zeros((10,1)))
def test_covariance_known_gain():
    x=sample();a=c.bands(x);t=c.bands(x*1.2);M=c.fit(a,t,0,len(x),0,0);y=c.apply(a,M,1.);np.testing.assert_allclose(y,x*1.2,atol=2e-5,rtol=.001)
def test_covariance_train_mask():
    x=sample();A=c.bands(x);T=c.bands(x);v=c.fit(A,T,0,32768,.1,1);T[32768:]*=100;z=c.fit(A,T,0,32768,.1,1);np.testing.assert_array_equal(v,z)
