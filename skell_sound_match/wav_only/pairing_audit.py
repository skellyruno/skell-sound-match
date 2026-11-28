"""Private comparison provenance and alignment gates, not plugin-state inference."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
from scipy import signal
import soundfile as sf


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def alignment(source,target,sr):
    """Compare multiple windows; ambiguous nonlinear/modulated prints stay unverified.

    Positive lag means the target occurs later than the source. Offsets are
    reported, never silently corrected. Only plausible zero-offset pairs pass.
    """
    x=np.asarray(source,dtype=float);y=np.asarray(target,dtype=float)
    if x.shape!=y.shape or x.ndim!=2 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Alignment requires finite equal-format arrays')
    if len(x)<sr*2:raise ValueError('Need two seconds for pairing audit')
    # Mid-channel identity can vanish for anti-phase effects; fail conservatively.
    a=x.mean(axis=1);b=y.mean(axis=1)
    sos=signal.butter(3,[150,4500],btype='bandpass',fs=sr,output='sos')
    a=signal.sosfilt(sos,a)[::4];b=signal.sosfilt(sos,b)[::4]
    rate=sr/4;span=round(rate*1.2);maxlag=round(rate*.15)
    starts=np.linspace(0,max(0,len(a)-span),9).astype(int)
    energy=[float(np.mean(a[s:s+span]**2)) for s in starts]
    selected=[i for i in range(len(starts)) if energy[i]>max(energy)*.04]
    lags=[];correlations=[]
    for i in selected:
        start=starts[i];u=a[start:start+span];v=b[start:start+span]
        u=u-u.mean();v=v-v.mean()
        cc=signal.correlate(v,u,mode='full',method='fft')
        ll=signal.correlation_lags(len(v),len(u));mask=np.abs(ll)<=maxlag
        index=int(np.argmax(np.abs(cc[mask])))
        lags.append(int(ll[mask][index]*4))
        correlations.append(float(abs(cc[mask][index])/max(np.linalg.norm(u)*np.linalg.norm(v),1e-16)))
    win=round(sr*.02);n=len(x)//win
    ea=np.sqrt(np.mean(x[:n*win].reshape(n,win,-1)**2,axis=(1,2)))
    eb=np.sqrt(np.mean(y[:n*win].reshape(n,win,-1)**2,axis=(1,2)))
    env_corr=float(np.corrcoef(ea,eb)[0,1]) if np.std(ea)>1e-10 and np.std(eb)>1e-10 else 0.
    median=float(np.median(lags)) if lags else 0.
    spread=float(np.percentile(lags,90)-np.percentile(lags,10)) if lags else float('inf')
    corr=float(np.median(correlations)) if correlations else 0.
    reasons=[]
    # Compression can change the envelope substantially. Strong waveform
    # identity across windows is independent evidence, even with low envelope
    # correlation; envelope similarity alone can never establish identity.
    if len(lags)<3 or corr<.45 or (corr<.8 and env_corr<.75):reasons.append('Insufficient same-performance signal evidence')
    if abs(median)>16:reasons.append('Nonzero processing offset requires explicit alignment review')
    if spread>32:reasons.append('Window offsets are inconsistent')
    return {'status':'SIGNAL_PAIR_CHECK_PASS' if not reasons else 'UNVERIFIED',
            'median_lag_samples':median,'lag_spread_samples':spread,
            'median_abs_bandpassed_correlation':corr,'envelope_correlation':env_corr,
            'window_lags_samples':lags,'reasons':reasons}


def audit_group(group,base):
    """Hashes bind the actual reference, source and candidate render provenance."""
    issues=[];base=Path(base)
    source=group.get('source',{});reference=group.get('reference',{})
    source_path=(base/source['path']).resolve();reference_path=(base/reference['path']).resolve()
    x,sr=sf.read(source_path,always_2d=True);y,rate=sf.read(reference_path,always_2d=True)
    sh=file_sha(source_path);rh=file_sha(reference_path)
    if source.get('sha256')!=sh or reference.get('sha256')!=rh:raise ValueError('Source/reference SHA-256 mismatch')
    if sr!=rate or x.shape!=y.shape:raise ValueError('Source/reference format or duration mismatch')
    if not group.get('recording_id') or reference.get('recording_id')!=group['recording_id']:
        issues.append('Reference recording identity unverified')
    if reference.get('stage')!=group.get('stage'):issues.append('Reference processing stage mismatch')
    evidence=alignment(x,y,sr)
    audits=[]
    for c in group.get('candidates',[]):
        p=(base/c['path']).resolve();z,fs=sf.read(p,always_2d=True)
        if c.get('sha256')!=file_sha(p):raise ValueError('Candidate SHA-256 mismatch')
        if c.get('source_sha256')!=sh or c.get('fit_reference_sha256')!=rh:
            issues.append('Candidate render provenance does not match this source/reference')
        if c.get('recording_id')!=group['recording_id'] or c.get('stage')!=group['stage']:
            issues.append('Candidate take or stage differs from comparison')
        offset=c.get('offset_samples',0)
        if not isinstance(offset,int) or not 0<=offset<=sr:raise ValueError('Invalid declared candidate latency')
        if fs!=sr or z.shape[1]!=x.shape[1] or len(z)!=len(x)+offset:
            raise ValueError('Candidate format or duration mismatch')
        z=z[offset:offset+len(x)]
        if not c.get('complete_stage',False):issues.append('Candidate omits required processing stages')
        if c.get('regression',False):issues.append('Candidate failed a measured regression gate')
        # Input->processed lag includes intentional processing. What must align
        # for playback is this candidate with its actual processed reference.
        timing=alignment(z,y,sr)
        if timing['status']!='SIGNAL_PAIR_CHECK_PASS':
            issues.append('Candidate/reference performance or timing remains unverified')
        audits.append({'version_id':c['version_id'],'sha256':c['sha256'],'timing':timing})
    if not group.get('candidates'):issues.append('No accepted candidate for this stage')
    return {'status':'PAIRING_CHECKS_PASS' if not issues else 'UNVERIFIED',
            'issues':list(dict.fromkeys(issues)),'source_sha256':sh,'reference_sha256':rh,
            'alignment':evidence,'candidates':audits,'sample_rate':sr,'frames':len(x)}
