"""Skell Sound Match -> Skell Preset local-library bridge (v1).
Run with all plugin instances closed. Never loads or edits DAW session state.
"""
import argparse, hashlib, json, math, os, re, tempfile, zipfile, struct, zlib
from pathlib import Path

LIMIT=4*1024*1024
ID=re.compile(r'[a-z0-9][a-z0-9_-]{0,79}\Z')
HEX=re.compile(r'[0-9a-f]{64}\Z')
def digest(data):return hashlib.sha256(data).hexdigest()
def key(s):
    if not isinstance(s,str) or not ID.fullmatch(s):raise ValueError('invalid stable ID')
    return s

def label(s,n=60):
    if not isinstance(s,str) or not s.strip() or len(s)>n or any(ord(c)<32 for c in s):raise ValueError('invalid label')
    return s.strip()

def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():raise ValueError('refuse symbolic link')
    fd,tmp=tempfile.mkstemp(prefix='.skell-sync-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def load(path,default):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default

def put(path,value):atomic(path,(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
def number(v,lo,hi):return type(v) in (int,float) and math.isfinite(v) and lo<=v<=hi

def package(path):
    path=Path(path)
    if path.suffix.lower()!='.skellpreset' or path.stat().st_size>LIMIT:raise ValueError('invalid package size/type')
    with zipfile.ZipFile(path) as z:
        i=z.infolist()
        if len(i)!=1 or i[0].filename!='preset.json' or not 0<i[0].file_size<=262144 or (i[0].external_attr>>16)&0o170000==0o120000:raise ValueError('invalid package member')
        d=json.loads(z.read(i[0]))
    if d.get('schemaVersion')!=2 or type(d.get('activeSlotCount')) is not int or not 10<=d['activeSlotCount']<=16:raise ValueError('schema v2 rack required')
    for k,n in [('name',96),('author',96),('bank',64)]:label(d[k],n)
    g=d['globals'];s=d['chain'];count=d['activeSlotCount']
    if type(g.get('mode')) is not int or not 0<=g['mode']<=3 or not number(g.get('inputDb'),-24,24) or not number(g.get('outputDb'),-24,24) or not number(g.get('mix'),0,1):raise ValueError('invalid globals')
    if not isinstance(s,list) or len(s)!=16 or {x.get('slotId') for x in s}!=set(range(16)):raise ValueError('invalid rack slots')
    if 'macros' in g and (len(g['macros'])!=8 or not all(number(v,0,1) for v in g['macros'])):raise ValueError('invalid macros')
    for x in s:
        if type(x.get('slotId')) is not int or type(x.get('type')) is not int or not 0<=x['type']<46 or x['type']==12 or type(x.get('enabled')) is not bool or not number(x.get('wet'),0,1) or len(x.get('params',[]))!=16 or not all(number(v,0,1) for v in x['params']):raise ValueError('invalid/native-only slot')
        if x['slotId']>=count and x['enabled']:raise ValueError('enabled hidden slot')
        if 'eqQ' in x and (len(x['eqQ'])!=8 or not all(number(v,0,1) for v in x['eqQ'])):raise ValueError('invalid EQ Q')
        for k,lo,hi in [('eqLowCut',0,1),('eqHighCut',0,1),('duckDepth',0,1),('duckThreshold',-60,-12),('duckRelease',50,1500),('duckAttack',2,80),('limitAttack',0,3),('limitRelease',5,500)]:
            if k in x and not number(x[k],lo,hi):raise ValueError('invalid optional slot value')
        for k in ('duckOn','rightFirst','dubDuckOn','parallelReturn','duckExternal','duckEffect'):
            if k in x and type(x[k]) is not bool:raise ValueError('invalid slot flag')
        if 'duckSource' in x and (type(x['duckSource']) is not int or not 0<=x['duckSource']<=2):raise ValueError('invalid duck source')
        if 'studioEqKind' in x and (len(x['studioEqKind'])!=8 or not all(type(v) is int and 0<=v<=4 for v in x['studioEqKind'])):raise ValueError('invalid EQ shape')
        if 'studioEqOn' in x and (len(x['studioEqOn'])!=8 or not all(type(v) is bool for v in x['studioEqOn'])):raise ValueError('invalid EQ flag')
    for k,lo,hi in [('micPreAmount',0,1),('micPreTrim',0,1),('micGateThreshold',-80,-10),('micGateRelease',20,1000),('micGateHold',0,250),('micGateAttackMs',.5,25),('micGateHysteresisDb',0,12),('micGateDepth',0,1),('micTubeGain',-12,12),('micTubeDrive',0,1),('micTubeAir',0,6),('micTubeTrim',-12,12)]:
        if k in g and not number(g[k],lo,hi):raise ValueError('invalid optional global')
    for k in ('micPreOn','micGateOn','micTubeOn'):
        if k in g and type(g[k]) is not bool:raise ValueError('invalid global flag')
    for k,lo,hi in [('micPreInput',0,3),('micPreTarget',0,3),('stereoSeparation',-96,96)]:
        if k in g and (type(g[k]) is not int or not lo<=g[k]<=hi):raise ValueError('invalid global choice')
    return d

def valid_png(data):
    if len(data)>8*1024*1024 or len(data)<45 or data[:8]!=b'\x89PNG\r\n\x1a\n':return False
    pos=8;first=True;idat=False
    while pos+12<=len(data):
        n=struct.unpack_from('>I',data,pos)[0];kind=data[pos+4:pos+8];end=pos+12+n
        if end>len(data) or zlib.crc32(data[pos+4:end-4])!=struct.unpack_from('>I',data,end-4)[0]:return False
        if first:
            if kind!=b'IHDR' or n!=13 or not all(0<int.from_bytes(data[k:k+4],'big')<=4096 for k in (16,20)):return False
            first=False
        if kind==b'IDAT':idat=True
        if kind==b'IEND':return n==0 and idat and end==len(data)
        pos=end
    return False

def catalog(root):
    c=load(root/'catalog.json',{'schema':1,'artists':{},'presets':{}})
    if c.get('schema')!=1:raise ValueError('unknown catalog schema')
    return c

def artist(root,artist_id,name,cover=None):
    artist_id=key(artist_id);c=catalog(root);a=c['artists'].setdefault(artist_id,{});a['name']=label(name)
    if cover:
        data=Path(cover).read_bytes()
        if not valid_png(data):raise ValueError('use valid PNG artwork up to 4096x4096 and 8 MiB')
        h=digest(data);atomic(root/'artwork'/f'{h}.png',data);a['cover_sha']=h
    put(root/'catalog.json',c)

def stage(root,preset_id,artist_id,name,category,source,approved=False,pair=None):
    preset_id=key(preset_id);artist_id=key(artist_id);name=label(name,72)
    if category not in ('main','adlib'):raise ValueError('invalid category')
    c=catalog(root)
    if artist_id not in c['artists']:raise ValueError('create artist first')
    d=package(source);raw=Path(source).read_bytes();h=digest(raw)
    e=c['presets'].setdefault(preset_id,{'artist_id':artist_id,'name':name,'category':category,'revisions':[]})
    if e['artist_id']!=artist_id:raise ValueError('stable preset belongs to another artist')
    if pair is not None:e['pair']=key(pair)
    e.update(name=name,category=category);old=next((r for r in e['revisions'] if r['sha256']==h),None)
    if old is None:e['revisions'].append({'sha256':h,'status':'approved' if approved else 'trial'})
    elif approved:old['status']='approved'
    dest=root/'revisions'/preset_id/f'{h}.skellpreset'
    if dest.exists() and digest(dest.read_bytes())!=h:raise ValueError('corrupt immutable revision')
    if not dest.exists():atomic(dest,raw)
    e['latest']=h;put(root/'catalog.json',c);return h

def sidecar(path,k,v):
    raw=path.read_text(encoding='utf-8-sig') if path.exists() else ''
    if any(line.split('\t',1)[0].casefold()==k.casefold() for line in raw.splitlines()):return
    out=raw+('' if not raw or raw.endswith('\n') else '\n')+k+'\t'+v+'\n'
    if len(out.encode())>1024*1024:raise ValueError('metadata capacity')
    atomic(path,out.encode())

def publish(root,library,preset_id,revision=None,trial=False):
    c=catalog(root);preset_id=key(preset_id);e=c['presets'][preset_id];a=c['artists'][key(e['artist_id'])];h=revision or e.get('latest')
    if not isinstance(h,str) or not HEX.fullmatch(h):raise ValueError('no staged revision')
    rev=next(r for r in e['revisions'] if r['sha256']==h)
    if not trial and rev['status']!='approved':raise ValueError('native trial is not approved for production')
    src=root/'revisions'/preset_id/f'{h}.skellpreset';package(src);raw=src.read_bytes()
    if digest(raw)!=h:raise ValueError('revision checksum mismatch')
    library=Path(library);folder=library/'Presets';folder.mkdir(parents=True,exist_ok=True)
    # Independent trial channel; stable readable filenames retain favorites and artwork across revisions.
    channel=preset_id+('--trial' if trial else '');manifest=library/'SoundMatchInstalled.json';m=load(manifest,{'schema':1,'installed':{}})
    if m.get('schema')!=1:raise ValueError('unknown installed manifest')
    old=m['installed'].get(channel);name=key(e['artist_id'])+'--'+preset_id+(' [Trial]' if trial else '')+'.skellpreset';dest=folder/name
    if dest.is_symlink():raise ValueError('refuse symbolic link')
    if dest.exists():
        actual=digest(dest.read_bytes())
        if old is None or actual!=old['sha256']:
            if old is None or actual!=h:raise ValueError('local preset changed/unmanaged; use Save As or explicitly stage the edit')
        if actual!=h:
            backup=library/'SoundMatchHistory'/channel/f'{actual}.skellpreset'
            if not backup.exists():atomic(backup,dest.read_bytes())
    k='user:'+name.lower()
    # Defaults only: local artist/category/artwork edits are never overwritten.
    sidecar(library/'ArtistTags.txt',k,label(a['name']))
    sidecar(library/'LibraryOrganization.txt','type:'+k,e['category'])
    sidecar(library/'LibraryOrganization.txt','title:'+k,label(e['name'],72)+(' [Trial]' if trial else ''))
    if e.get('pair'):sidecar(library/'LibraryOrganization.txt','pair:'+k,key(e['pair']))
    if a.get('cover_sha') and not dest.with_suffix('.png').exists() and not dest.with_suffix('.jpg').exists():
        ah=a['cover_sha']
        if not isinstance(ah,str) or not HEX.fullmatch(ah):raise ValueError('invalid artwork identity')
        data=(root/'artwork'/f'{ah}.png').read_bytes()
        if digest(data)!=ah or not valid_png(data):raise ValueError('artwork checksum mismatch')
        atomic(dest.with_suffix('.png'),data)
    if not dest.exists() or digest(dest.read_bytes())!=h:atomic(dest,raw)
    m['installed'][channel]={'sha256':h,'file':name};put(manifest,m);return dest

def verify(root):
    """Verify the complete immutable catalog before any install writes."""
    c=catalog(root);count=0
    for aid,a in c['artists'].items():
        key(aid);label(a['name'])
    for pid,e in c['presets'].items():
        key(pid);key(e['artist_id']);label(e['name'],72)
        if e['artist_id'] not in c['artists'] or e['category'] not in ('main','adlib'):raise ValueError('invalid catalog entry')
        if e.get('pair'):key(e['pair'])
        seen=set()
        for r in e['revisions']:
            h=r['sha256']
            if not HEX.fullmatch(h) or h in seen or r['status'] not in ('trial','approved'):raise ValueError('invalid revision identity')
            seen.add(h);f=root/'revisions'/pid/(h+'.skellpreset');package(f)
            if digest(f.read_bytes())!=h:raise ValueError('revision checksum mismatch')
            count+=1
        if e.get('latest') and e['latest'] not in seen:raise ValueError('latest not present')
    return {'presets':len(c['presets']),'revisions':count,'loadable':sum(bool(e.get('latest')) for e in c['presets'].values())}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,required=True);sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('artist');a.add_argument('id');a.add_argument('name');a.add_argument('--cover',type=Path)
    a=sub.add_parser('stage');a.add_argument('id');a.add_argument('artist');a.add_argument('name');a.add_argument('category',choices=['main','adlib']);a.add_argument('package',type=Path);a.add_argument('--approved-native',action='store_true');a.add_argument('--pair')
    a=sub.add_parser('publish');a.add_argument('id');a.add_argument('--library',type=Path,default=Path(os.environ.get('APPDATA',Path.home()/'.config'))/'Skell Audio'/'Skell-Preset');a.add_argument('--revision');a.add_argument('--trial',action='store_true')
    sub.add_parser('list');sub.add_parser('verify');a=p.parse_args();root=a.catalog
    if a.cmd=='artist':artist(root,a.id,a.name,a.cover)
    elif a.cmd=='stage':print(stage(root,a.id,a.artist,a.name,a.category,a.package,a.approved_native,a.pair))
    elif a.cmd=='publish':print(publish(root,a.library,a.id,a.revision,a.trial))
    elif a.cmd=='verify':print(json.dumps(verify(root),indent=2))
    else:print(json.dumps(catalog(root),indent=2))
if __name__=='__main__':main()
