"""Reproduce a selected native fit on the same input, checking recorded identities."""
import argparse, hashlib, json, pathlib, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

def replay(renderer, source, report, output, index=None):
    exe=pathlib.Path(renderer).resolve(); source=pathlib.Path(source); out=pathlib.Path(output)
    if out.exists(): raise FileExistsError(out)
    data=json.loads(pathlib.Path(report).read_text())
    if data.get('schema')!='skell.native-gate-fit.v1': raise ValueError('Wrong report schema')
    if hashlib.sha256(exe.read_bytes()).hexdigest()!=data['renderer_sha256']: raise ValueError('Renderer binary differs')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=data['raw_sha256']: raise ValueError('Source differs')
    x,sr=sf.read(source,dtype='float32',always_2d=True)
    if x.shape[1]==1:x=np.repeat(x,2,axis=1)
    if sr!=data['sample_rate'] or len(x)!=data['frames'] or x.shape[1]!=2 or not np.isfinite(x).all():raise ValueError('Source geometry differs')
    idx=data['selected_index'] if index is None else index
    if not isinstance(idx,int) or not 0<=idx<len(data['results']):raise ValueError('Invalid candidate index')
    r=data['results'][idx]; p=r['parameters']
    with tempfile.TemporaryDirectory() as td:
        a=pathlib.Path(td)/'in.f32'; b=pathlib.Path(td)/'out.f32';x.tofile(a)
        subprocess.run([str(exe),str(a),str(b),str(sr),*[str(p[k]) for k in ('threshold_db','attack_ms','hold_ms','release_ms','hysteresis_db')],str(int(r['finish'])),str(data['input_db']),str(r['output_db']),str(data['block_size'])],check=True,capture_output=True,timeout=60)
        z=np.fromfile(b,dtype=np.float32).reshape(-1,2)
    if z.shape!=x.shape or not np.isfinite(z).all() or hashlib.sha256(z.tobytes()).hexdigest()!=r['render_sha256']:raise ValueError('Render does not reproduce selected candidate')
    if np.max(abs(resample_poly(z,4,1,axis=0)))>10**(-1/20):raise ValueError('Estimated true peak exceeds -1 dBTP')
    # Float WAV avoids changing the exact matched samples. Exclusive output creation.
    with out.open('xb') as f:sf.write(f,z,sr,format='WAV',subtype='FLOAT')
    return r['render_sha256']
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('renderer');p.add_argument('source');p.add_argument('report');p.add_argument('output');p.add_argument('--index',type=int);a=p.parse_args();print(replay(a.renderer,a.source,a.report,a.output,a.index))
