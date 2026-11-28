"""Unified offline audition, promotion and replay evidence.
The fixed historical score/peak gates are intentionally not tunable here.
All target-dependent operations are outside the renderer. Same-take audits
are retrospective and not proof of independent performance or native realtime.
"""
from dataclasses import dataclass
import hashlib
import math
import numpy as np
from scipy import signal

@dataclass(frozen=True)
class PairPlan:
    start: int
    end: int
    train_end: int
    audit_start: int
    guard: int = 4096
    def __post_init__(self):
        if not (0<=self.start<self.train_end<self.audit_start<self.end) or self.guard<0:
            raise ValueError('invalid split')
        if self.train_end-self.start<=2*self.guard or self.audit_start-self.train_end<=2*self.guard:
            raise ValueError('insufficient guarded data')
    @classmethod
    def chronological(cls,start,end,train_fraction=.45,guard=4096):
        if not 0<train_fraction<.7:raise ValueError('invalid training fraction')
        return cls(start,end,start+int(train_fraction*(end-start)),start+int(.7*(end-start)),guard)
    @property
    def fit(self):return slice(self.start+self.guard,self.train_end-self.guard)
    @property
    def selection(self):return slice(self.train_end+self.guard,self.audit_start-self.guard)
    @property
    def audit(self):return slice(self.audit_start,self.end)

def validate_audio(x):
    a=np.asarray(x,dtype=np.float32)
    if a.ndim!=2 or a.shape[1]!=2 or not len(a) or not np.isfinite(a).all():raise ValueError('invalid stereo PCM')
    return np.ascontiguousarray(a)

def audio_hash(x):
    a=validate_audio(x);return hashlib.sha256(np.asarray(a.shape,dtype='<i8').tobytes()+a.astype('<f4',copy=False).tobytes()).hexdigest()

def _score(metric,x,t):
    q={k:float(v) for k,v in metric(x,t).items()}
    if 'score' not in q or q['score']<0 or not all(math.isfinite(v) for v in q.values()):raise ValueError('invalid metric')
    return q

def _peak(x):return 20*math.log10(max(1e-12,float(np.max(abs(signal.resample_poly(x,4,1,axis=0))))))

def selection_profile(x,y,t,plan,metric):
    """Pre-audit metrics only, including active and tail sections separately.
    Uses nonoverlapping 0.5s windows where reference contains audible signal.
    Does not use final audit to rank candidates; records missing active data.
    """
    s=plan.selection;d=validate_audio(x)[s];v=validate_audio(y)[s];u=validate_audio(t)[s]
    if not len(u) or not (d.shape==v.shape==u.shape):raise ValueError('selection unavailable')
    total=_score(metric,v,u);parts=[];size=22050
    ref_rms=np.sqrt(np.mean(u*u));dry_rms=np.sqrt(np.mean(d*d))
    active=[];tail=[]
    for j in range(0,len(u),size):
        stop=min(j+size,len(u));q=u[j:stop];p=d[j:stop]
        if len(q)<4096 or np.sqrt(np.mean(q*q))<max(ref_rms*.04,1e-6):continue
        a=bool(np.sqrt(np.mean(p*p))>=max(dry_rms*.06,1e-5));z=_score(metric,v[j:stop],q);(active if a else tail).append(z['score']);parts.append({'start':s.start+j,'end':s.start+stop,'active':a,'metrics':z})
    return {'whole':total,'windows':parts,'active_mean':float(np.mean(active)) if active else None,'tail_mean':float(np.mean(tail)) if tail else None,'worst':max((v['metrics']['score'] for v in parts),default=total['score']),'has_active':bool(active)}

def classify(report,previous_worst):
    """Exact existing qualification gate; fail closed on incomplete evidence."""
    if not math.isfinite(previous_worst) or previous_worst<0:raise ValueError('invalid previous best')
    required=('score44','score48','peak44','peak48','stress44','stress48')
    if any(k not in report or not math.isfinite(float(report[k])) for k in required):raise ValueError('incomplete evidence')
    if min(report['score44'],report['score48'])<0:raise ValueError('negative error score')
    w=max(report['score44'],report['score48']);safe=max(report['peak44'],report['peak48'])<=-1 and max(report['stress44'],report['stress48'])<=0
    return dict(worst=float(w),safe=bool(safe),improved=bool(safe and w<previous_worst),qualified=bool(safe and w<=1.5))

def audit(render,x,t,plan,metric,recipe_bytes,previous_worst):
    """Render 44.1 and resampled 48k paths plus actual +6 dB dry stress.
    Renderer accepts only dry PCM; recipes are frozen externally.
    Cannot certify renderer itself has no hidden target use.
    """
    x=validate_audio(x);t=validate_audio(t)
    if x.shape!=t.shape or plan.end>len(x):raise ValueError('mismatched sources')
    if not isinstance(recipe_bytes,bytes) or not recipe_bytes:raise ValueError('missing frozen recipe bytes')
    def r(a):
        y=validate_audio(render(a.copy()))
        if y.shape!=a.shape:raise ValueError('renderer changed source length')
        return y
    x48=signal.resample_poly(x,160,147,axis=0).astype('f');x0=signal.resample_poly(x48,147,160,axis=0).astype('f');y=r(x);v48=signal.resample_poly(r(x0),160,147,axis=0)[:len(x48)];s1=r(x*10**.3);s2=signal.resample_poly(r(x0*10**.3),160,147,axis=0)[:len(x48)];a=_score(metric,y[plan.audit],t[plan.audit]);b=_score(metric,signal.resample_poly(v48,147,160,axis=0)[:len(t)][plan.audit],t[plan.audit]);q=dict(score44=a['score'],score48=b['score'],metrics44=a,metrics48=b,peak44=_peak(y),peak48=_peak(v48),stress44=_peak(s1),stress48=_peak(s2),recipe_sha256=hashlib.sha256(recipe_bytes).hexdigest(),dry_pcm_sha256=audio_hash(x),target_pcm_sha256=audio_hash(t),output_pcm_sha256=audio_hash(y),output48_pcm_sha256=audio_hash(v48),stress44_pcm_sha256=audio_hash(s1),stress48_pcm_sha256=audio_hash(s2),audit_start=plan.audit_start,audit_end=plan.end,rate_path='44.1k internal; 48k roundtrip',validation='retrospective same-take')
    q.update(classify(q,previous_worst));return y,q
