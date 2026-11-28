"""Optional local Phantom 2.0 CLI; no automatic dependency install or audio upload."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

def run_external(candidate, reference=None, *, executable=None, timeout=120):
    exe=executable or shutil.which('phantom')
    if not exe:
        return {'status':'unavailable','reason':'phantom executable not installed'}
    exe=str(Path(exe).resolve()) if os.path.sep in str(exe) else str(exe)
    paths=[Path(candidate).resolve(strict=True)]
    if reference is not None:
        paths.append(Path(reference).resolve(strict=True))
    if not all(p.is_file() for p in paths):
        raise ValueError('expected local files')
    cmd=[exe,'compare',str(paths[0]),'--reference',str(paths[1]),'--json'] if reference is not None else [exe,'analyze',str(paths[0]),'--json']
    with tempfile.TemporaryDirectory(prefix='skell-phantom-') as scratch:
        # Phantom 2.0 checks this entry before its automatic onboarding.
        # Configure only a disposable home, never the user's MCP or DAW settings.
        root=Path(scratch)
        (root/'.mcp.json').write_text(json.dumps({'mcpServers':{'phantom':{'command':'phantom-mcp','args':[]}}}))
        env=dict(os.environ,HOME=scratch,XDG_CONFIG_HOME=scratch,XDG_CACHE_HOME=scratch,XDG_DATA_HOME=scratch,PHANTOM_OUTPUT_DIR=scratch,PHANTOM_NO_TELEMETRY='1',PHANTOM_AUDIO_DIR=os.path.commonpath([str(p.parent) for p in paths]))
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,env=env,cwd=scratch,stdin=subprocess.DEVNULL,check=False)
        except (OSError,subprocess.TimeoutExpired) as e:
            return {'status':'failed','reason':type(e).__name__}
    result={'status':'completed' if r.returncode==0 else 'failed','returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    if r.returncode==0:
        try:
            report=json.loads(r.stdout)
            if not isinstance(report,dict) or not report:
                raise ValueError('empty or invalid report')
            result['analysis']=report
        except ValueError:
            result.update(status='failed',reason='invalid JSON report')
    return result
