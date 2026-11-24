"""Train-prefix-only optimizer for the shared native Club Gate renderer."""
import argparse, hashlib, json, pathlib, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.optimize import differential_evolution
from scipy.signal import resample_poly

ENGINE_REVISION = "92b03b753c59583b6b6063228c2d630ef94daf59"

def fit(renderer, raw, target, report, maxiter=6):
    exe=pathlib.Path(renderer).resolve(); report=pathlib.Path(report)
    if report.exists(): raise FileExistsError(report)
    if subprocess.check_output([str(exe),'--version'],text=True,timeout=10).strip()!='club-gate-v1': raise ValueError('Wrong renderer version')
    x,sr=sf.read(raw,dtype='float32',always_2d=True); y,yr=sf.read(target,dtype='float32',always_2d=True)
    if not 0<=maxiter<=100: raise ValueError('maxiter outside 0..100')
    if x.shape!=y.shape or sr!=yr or x.shape[1] not in (1,2) or not 8000<=sr<=192000 or not np.isfinite(x).all() or not np.isfinite(y).all(): raise ValueError('Aligned finite mono/stereo pair required')
    if x.shape[1]==1: x=np.repeat(x,2,axis=1); y=np.repeat(y,2,axis=1)
    n=int(len(x)*.6)
    if min(n,len(x)-n)<sr: raise ValueError('Need at least one second per section')
    def score(z,t,s):
        mask=np.max(abs(s),axis=1)>=.005
        return sum(float(np.mean((z[m]-t[m])**2)/max(np.mean(s[m]**2),1e-10)) for m in (mask,~mask) if m.any())
    m=np.max(abs(x[:n]),axis=1)>.05
    g=np.sum(x[:n][m]*y[:n][m],dtype=np.float64)/max(np.sum(x[:n][m]**2,dtype=np.float64),1e-12)
    trim=float(np.clip(20*np.log10(max(g,1e-12)),-24,24)); results=[]
    with tempfile.TemporaryDirectory() as td:
        d=pathlib.Path(td); train=d/'train.f32'; full=d/'full.f32'; dest=d/'out.f32'; x[:n].tofile(train);x.tofile(full)
        def render(p,finish,source,block=256):
            dest.unlink(missing_ok=True)
            meta=json.loads(subprocess.check_output([str(exe),str(source),str(dest),str(sr),*[str(float(v)) for v in p],str(int(finish)),'0',str(trim),str(block)],text=True,timeout=60))
            z=np.fromfile(dest,dtype=np.float32).reshape(-1,2)
            if len(z)!=meta['frames'] or not np.isfinite(z).all(): raise RuntimeError('Invalid native output')
            return z,meta
        base=[-46,2,25,40,4]
        for finish in (False,True):
            before,_=render(base,finish,full)
            def objective(p): return score(render(p,finish,train)[0],y[:n],x[:n])
            opt=differential_evolution(objective,[(-65,-30),(.5,10),(0,80),(20,160),(0,8)],seed=23,popsize=4,maxiter=maxiter,polish=False,x0=base)
            p=opt.x if opt.fun<objective(base) else base
            z,meta=render(p,finish,full)
            results.append(dict(finish=finish,parameters=dict(zip(('threshold_db','attack_ms','hold_ms','release_ms','hysteresis_db'),map(float,p))),output_db=trim,baseline_train=score(before[:n],y[:n],x[:n]),baseline_later=score(before[n:],y[n:],x[n:]),train=score(z[:n],y[:n],x[:n]),later=score(z[n:],y[n:],x[n:]),block_exact=all(np.array_equal(z,render(p,finish,full,b)[0]) for b in (1,64,511,1024)),peak_dbtp_estimate=float(20*np.log10(max(np.max(abs(resample_poly(z,4,1,axis=0))),1e-12))),processing_seconds=meta['processing_seconds'],render_sha256=hashlib.sha256(z.tobytes()).hexdigest()))
    out=dict(schema='skell.native-gate-fit.v1',expected_core_revision=ENGINE_REVISION,renderer_version='club-gate-v1',input_db=0,block_size=256,raw_sha256=hashlib.sha256(pathlib.Path(raw).read_bytes()).hexdigest(),target_sha256=hashlib.sha256(pathlib.Path(target).read_bytes()).hexdigest(),renderer_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),sample_rate=sr,frames=len(x),train_frames=n,selection='train prefix only; later same-take diagnostic',results=results,selected_index=int(np.argmin([r['train'] for r in results])))
    with report.open('x') as f: json.dump(out,f,indent=2)
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('renderer');p.add_argument('raw');p.add_argument('target');p.add_argument('report');p.add_argument('--maxiter',type=int,default=6);a=p.parse_args();print(json.dumps(fit(a.renderer,a.raw,a.target,a.report,a.maxiter),indent=2))
