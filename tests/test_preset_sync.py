import json,zipfile,hashlib,struct,zlib
from pathlib import Path
import pytest
from skell_sound_match.wav_only import preset_sync as s

def fixture(p,output=0):
 d={'schemaVersion':2,'activeSlotCount':10,'name':'Free Main','author':'skellyruno','bank':'Main Vocals','globals':{'mode':1,'inputDb':0,'outputDb':output,'mix':1,'macros':[.5]*8},'chain':[dict(slotId=i,type=4 if i==0 else 0,enabled=i==0,wet=1,params=[.5]*16) for i in range(16)]}
 with zipfile.ZipFile(p,'w') as z:z.writestr('preset.json',json.dumps(d))
 return p

def init(tmp_path):
 c=tmp_path/'catalog';l=tmp_path/'library';s.artist(c,'skellyruno','skellyruno');p=fixture(tmp_path/'a.skellpreset');h=s.stage(c,'free_main','skellyruno','Free Main','main',p);return c,l,p,h

def test_trial_and_promotion(tmp_path):
 c,l,p,h=init(tmp_path)
 with pytest.raises(ValueError):s.publish(c,l,'free_main')
 trial=s.publish(c,l,'free_main',trial=True);assert trial.read_bytes()==p.read_bytes();assert 'skellyruno' in (l/'ArtistTags.txt').read_text();assert '\tmain' in (l/'LibraryOrganization.txt').read_text()
 s.stage(c,'free_main','skellyruno','Free Main','main',p,True);prod=s.publish(c,l,'free_main');assert prod!=trial and prod.read_bytes()==trial.read_bytes()

def test_update_rollback(tmp_path):
 c,l,p,h=init(tmp_path);dest=s.publish(c,l,'free_main',trial=True);p2=fixture(tmp_path/'b.skellpreset',-2);h2=s.stage(c,'free_main','skellyruno','Free Main','main',p2);assert h!=h2
 assert s.publish(c,l,'free_main',trial=True)==dest;assert dest.read_bytes()==p2.read_bytes();assert (l/'SoundMatchHistory'/'free_main--trial'/f'{h}.skellpreset').read_bytes()==p.read_bytes();assert s.publish(c,l,'free_main',revision=h,trial=True).read_bytes()==p.read_bytes()

def test_local_edit_conflict(tmp_path):
 c,l,p,h=init(tmp_path);dest=s.publish(c,l,'free_main',trial=True);fixture(dest,-3);p2=fixture(tmp_path/'b.skellpreset',-2);s.stage(c,'free_main','skellyruno','Free Main','main',p2);data=dest.read_bytes()
 with pytest.raises(ValueError):s.publish(c,l,'free_main',trial=True)
 assert dest.read_bytes()==data
 s.stage(c,'free_main','skellyruno','Free Main','main',dest);assert s.publish(c,l,'free_main',trial=True).read_bytes()==data

def test_metadata_preserve(tmp_path):
 c,l,p,h=init(tmp_path);dest=s.publish(c,l,'free_main',trial=True);a=l/'ArtistTags.txt';a.write_text(a.read_text().replace('\tskellyruno','\tMy Artist'));dest.with_suffix('.png').write_bytes(b'local artwork');s.publish(c,l,'free_main',trial=True);assert 'My Artist' in a.read_text();assert dest.with_suffix('.png').read_bytes()==b'local artwork'

def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))

def test_new_artist_and_cover(tmp_path):
 c,l,p,h=init(tmp_path);p2=tmp_path/'cover.png';p2.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\xff\x00\x00'))+chunk(b'IEND',b''));s.artist(c,'other','Other artist',p2);s.stage(c,'other_adlib','other','Other Adlib','adlib',p);d=s.publish(c,l,'other_adlib',trial=True);assert d.with_suffix('.png').read_bytes()==p2.read_bytes();assert '\tadlib' in (l/'LibraryOrganization.txt').read_text()

def test_revision_tamper(tmp_path):
 c,l,p,h=init(tmp_path);f=c/'revisions'/'free_main'/f'{h}.skellpreset';fixture(f,-3)
 with pytest.raises(ValueError):s.publish(c,l,'free_main',trial=True)
 assert not (l/'Presets').exists()

def test_bad_path(tmp_path):
 c,l,p,h=init(tmp_path)
 with pytest.raises(ValueError):s.stage(c,'../oops','skellyruno','Oops','main',p)

def test_malformed_zip(tmp_path):
 p=tmp_path/'bad.skellpreset';with_zip=zipfile.ZipFile(p,'w');with_zip.writestr('../preset.json','{}');with_zip.close()
 with pytest.raises(ValueError):s.package(p)

@pytest.mark.parametrize('change',[lambda d:d['chain'][0].update(type=12),lambda d:d['chain'][0].update(wet=float('nan')),lambda d:d['chain'][15].update(enabled=True),lambda d:d['chain'][1].update(slotId=0),lambda d:d['globals'].update(outputDb=30)])
def test_bad_package(tmp_path,change):
 p=fixture(tmp_path/'a.skellpreset');d=json.loads(zipfile.ZipFile(p).read('preset.json'));change(d)
 with zipfile.ZipFile(p,'w') as z:z.writestr('preset.json',json.dumps(d))
 with pytest.raises(ValueError):s.package(p)

def test_pair_and_preflight(tmp_path):
 c,l,p,h=init(tmp_path);s.stage(c,'free_main','skellyruno','Free Main','main',p,pair='free');assert s.verify(c)=={'presets':1,'revisions':1,'loadable':1};dest=s.publish(c,l,'free_main',trial=True);o=l/'LibraryOrganization.txt';assert 'pair:user:'+dest.name.lower()+'\tfree' in o.read_text();o.write_text(o.read_text().replace('\tfree\n','\tcustom\n'));s.publish(c,l,'free_main',trial=True);assert '\tcustom\n' in o.read_text()
 f=c/'revisions'/'free_main'/f'{h}.skellpreset';fixture(f,-5)
 with pytest.raises(ValueError):s.verify(c)

def test_verify_missing_latest(tmp_path):
 c,l,p,h=init(tmp_path);v=s.catalog(c);v['presets']['free_main']['latest']='0'*64;s.put(c/'catalog.json',v)
 with pytest.raises(ValueError):s.verify(c)
