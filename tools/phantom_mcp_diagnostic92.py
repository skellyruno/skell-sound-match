"""Local Phantom MCP diagnostic client; requires optional mcp in its own environment."""
import asyncio,json,os,sys,tempfile
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
async def diagnose(executable, paths, timeout=90):
    files=[Path(p).resolve(strict=True) for p in paths]
    if not files or not all(p.is_file() for p in files):raise ValueError('expected local audio files')
    exe=Path(executable).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='skell-phantom-mcp-') as d:
        env={'HOME':d,'XDG_CONFIG_HOME':d,'XDG_CACHE_HOME':d,'XDG_DATA_HOME':d,'PHANTOM_NO_TELEMETRY':'1','PHANTOM_QUIET':'1','FASTMCP_SHOW_SERVER_BANNER':'false','FASTMCP_CHECK_FOR_UPDATES':'off','FASTMCP_LOG_LEVEL':'WARNING','PHANTOM_AUDIO_DIR':os.path.commonpath([str(p.parent) for p in files]),'PATH':os.environ.get('PATH','')}
        params=StdioServerParameters(command=str(exe),env=env,cwd=d)
        async with asyncio.timeout(timeout):
            async with stdio_client(params) as (r,w):
                async with ClientSession(r,w) as client:
                    await client.initialize()
                    result={}
                    for f in files:
                        v=await client.call_tool('full_diagnostic',{'file_path':str(f)})
                        if v.isError:raise RuntimeError('Phantom diagnostic rejected input')
                        q=v.structuredContent
                        if not q:q=json.loads(''.join(c.text for c in v.content if getattr(c,'type','')=='text'))
                        if set(q)=={'result'}:q=q['result']
                        if not isinstance(q,dict) or not {'spectral','dynamics','loudness','phase','stereo','problems'}<=set(q):raise ValueError('unexpected Phantom report schema')
                        result[f.name]=q
                    return result
if __name__=='__main__':
    print(json.dumps(asyncio.run(diagnose(sys.argv[1],sys.argv[2:])),indent=2,allow_nan=False))
