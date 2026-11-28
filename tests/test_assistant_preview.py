import numpy as np,pytest
from skell_sound_match.wav_only.assistant_preview import fit,render,fit_motion,render_motion,preview,estimated_peak
SR=32000
@pytest.fixture
def tone():
 t=np.arange(5*SR)/SR;rng=np.random.default_rng(9);x=(.08*np.sin(2*np.pi*180*t)+.05*np.sin(2*np.pi*1100*t)+.015*rng.normal(size=len(t)))*(.7+.3*np.sin(2*np.pi*2*t));return np.column_stack((x,-x)).astype('f')
def test_fir(tone):
 target=render(tone,[1.]+[.15]+[0.]*14);h=fit(tone,target,SR,16,1.);assert np.sum(abs(h-np.r_[1.,np.zeros(15)]))<=.35000001;z=render(tone,h);assert np.mean((z-target)**2)<np.mean((tone-target)**2);assert np.max(abs(z[:,0]+z[:,1]))==0
 def later(x):return render(x,h)
 x=tone.copy();x[len(x)//2:]=0;assert np.array_equal(later(x)[:len(x)//2],z[:len(x)//2])
def test_motion(tone):
 recipe=fit_motion(tone,tone*.8,SR,True,2.);z=render_motion(tone,SR,recipe);assert np.isfinite(z).all() and np.max(abs(z[:,0]+z[:,1]))==0;assert np.mean((z-tone*.8)**2)<np.mean((tone-tone*.8)**2)
def test_preview_no_change(tone):
 copy=tone.copy();report,y=preview(tone,tone,SR,pair_confirmed=True);assert y is None and report['status']=='NO_IMPROVEMENT' and report['trial_count']==15;assert np.array_equal(tone,copy)
def test_preview_candidate(tone):
 target=render(tone,[1.,-.3]+[0.]*14);report,y=preview(tone,target,SR,pair_confirmed=True);assert report['trial_count']==15;assert report['status']=='AUDITION_ONLY' and y is not None and estimated_peak(y)<=-1
@pytest.mark.parametrize('what',['unconfirmed','shape','nan','silence','coefficients','motion'])
def test_reject(tone,what):
 with pytest.raises(ValueError):
  if what=='unconfirmed':preview(tone,tone,SR)
  elif what=='shape':preview(tone,tone[:-1],SR,pair_confirmed=True)
  elif what=='nan':preview(tone,np.full_like(tone,np.nan),SR,pair_confirmed=True)
  elif what=='silence':preview(tone,np.zeros_like(tone),SR,pair_confirmed=True)
  elif what=='coefficients':render(tone,np.ones(16))
  else:render_motion(tone,SR,dict(multiband=False,cap=3.,coefficients=[[9.,0,0,0]]))

def test_private_export(tone,tmp_path):
 import hashlib,soundfile as sf
 from skell_sound_match.wav_only.assistant_preview import preview_files
 a=tmp_path/'a.wav';b=tmp_path/'b.wav';sf.write(a,tone,SR,subtype='FLOAT');sf.write(b,render(tone,[1.,-.3]+[0.]*14),SR,subtype='FLOAT');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();out=tmp_path/'private'
 args=dict(source_sha256=sha(a),reference_sha256=sha(b),take='synthetic',stage='main',pair_confirmed=True)
 with pytest.raises(ValueError):preview_files(a,b,out,**dict(args,source_sha256='0'*64))
 assert not out.exists();r=preview_files(a,b,out,**args);assert r['status']=='AUDITION_ONLY' and sha(out/'AUDITION_ONLY.flac')==r['export_sha256'] and (out/'report.json').exists()
 with pytest.raises(FileExistsError):preview_files(a,b,out,**args)
