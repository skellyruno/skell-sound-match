"""Public synthetic smoke test. Never reads corpus or uploads recordings."""
import json,sys,tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from skell_sound_match.wav_only.phantom_bridge import run_external
exe=sys.argv[1];out=Path(sys.argv[2])
with tempfile.TemporaryDirectory() as d:
    p=Path(d)
    sr=44100;t=np.arange(sr*5)/sr
    m=(.15*np.sin(2*np.pi*220*t)+.04*np.sin(2*np.pi*1250*t))*(.7+.3*np.sin(2*np.pi*2*t))
    s=.02*np.sin(2*np.pi*470*t)
    sf.write(p/'reference.wav',np.column_stack([m+s,m-s]),sr,subtype='FLOAT')
    sf.write(p/'candidate.wav',np.column_stack([m*.75+s*.5,m*.75-s*.5]),sr,subtype='FLOAT')
    a=run_external(p/'candidate.wav',executable=exe)
    b=run_external(p/'candidate.wav',p/'reference.wav',executable=exe)
    (out/'synthetic-analysis.json').write_text(json.dumps(a,indent=2))
    (out/'synthetic-comparison.json').write_text(json.dumps(b,indent=2))
    assert a['status']==b['status']=='completed', (a,b)
    assert a['analysis']['sample_rate']==sr and a['analysis']['channels']==2
    assert -25<a['analysis']['loudness']['integrated_lufs']<-20
    assert a['analysis']['stereo']['correlation']>.9
    assert b['analysis'],b
    print('Actual Phantom structured analysis and comparison succeeded on generated test pair')
