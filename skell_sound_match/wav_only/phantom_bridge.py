"""Optional local Phantom CLI; no automatic install or cloud upload."""
import json
import os
import shutil
import subprocess
from pathlib import Path

def run_external(candidate, reference=None, *, executable=None, timeout=120):
    exe=executable or shutil.which('phantom')
    if not exe:
        return {'status':'unavailable','reason':'phantom executable not installed'}
    paths=[Path(p).resolve(strict=True) for p in (candidate,) if p is not None]
    if reference is not None:
        paths.append(Path(reference).resolve(strict=True))
    if not all(p.is_file() for p in paths):
        raise ValueError('expected local files')
    cmd=[str(exe),'compare',str(paths[0]),'--reference',str(paths[1])] if reference is not None else [str(exe),'analyze',str(paths[0]),'--json']
    env=dict(os.environ,PHANTOM_NO_TELEMETRY='1',PHANTOM_AUDIO_DIR=str(Path(os.path.commonpath([str(p.parent) for p in paths]))))
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,env=env,check=False)
    except (OSError,subprocess.TimeoutExpired) as e:
        return {'status':'failed','reason':type(e).__name__}
    result={'status':'completed' if r.returncode==0 else 'failed','returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    if r.returncode==0 and reference is None:
        try:
            result['analysis']=json.loads(r.stdout)
            if not isinstance(result['analysis'],dict) or not result['analysis']:
                raise ValueError('empty or invalid report')
        except ValueError:
            result.update(status='failed',reason='invalid JSON report')
    return result
