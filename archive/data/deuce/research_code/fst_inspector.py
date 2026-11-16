#!/usr/bin/env python3
"""Read-only FL Studio mixer preset (.fst) inspector.

Inspects FLhd/FLdt event records, mixer slots and embedded Waves XML chunks.
Does NOT load VSTs or execute preset/plugin data. Unknown plugin parameters are
preserved as raw values without inventing labels.
"""
import argparse, hashlib, json, re, struct, xml.etree.ElementTree as ET
from pathlib import Path

class FSTFormatError(ValueError): pass


def read_events(path):
    b=Path(path).read_bytes()
    if len(b)<22 or b[:4]!=b'FLhd' or b[14:18]!=b'FLdt':
        raise FSTFormatError('Invalid or unsupported FLhd/FLdt container')
    num=struct.unpack_from('<I',b,18)[0]
    if num > len(b)-22 or num != len(b)-22:
        raise FSTFormatError('FLdt size does not match file')
    cur=22; out=[]
    while cur<len(b):
        event_start=cur; key=b[cur];cur+=1
        if key<64:
            if cur+1>len(b):raise FSTFormatError('Truncated byte event')
            value=b[cur];cur+=1
        elif key<128:
            if cur+2>len(b):raise FSTFormatError('Truncated word event')
            value=struct.unpack_from('<H',b,cur)[0];cur+=2
        elif key<192:
            if cur+4>len(b):raise FSTFormatError('Truncated dword event')
            value=struct.unpack_from('<I',b,cur)[0];cur+=4
        else:
            length=0; shift=0
            while True:
                if cur>=len(b) or shift>28: raise FSTFormatError('Bad variable-length header')
                z=b[cur];cur+=1;length|=(z&127)<<shift;shift+=7
                if not(z&128): break
            if cur+length>len(b):raise FSTFormatError('Truncated variable-length payload')
            value=b[cur:cur+length];cur+=length
        out.append((event_start,key,value))
    return b,out


def u16str(data):
    return data.decode('utf-16le',errors='replace').rstrip('\x00')


def get_waves_xml(data):
    m=re.search(rb'<PresetChunkXMLTree version="3">.*?</PresetChunkXMLTree>',data,re.S)
    if not m:return None
    root=ET.fromstring(m.group())
    hd=root.find('.//PresetHeader')
    name=hd.findtext('PluginName') if hd is not None else None
    setup=hd.findtext('ActiveSetup') if hd is not None else None
    ver=hd.findtext('PluginVersion') if hd is not None else None
    vals=[]
    for e in root.findall('.//PresetData'):
        if e.get('Setup')==setup:
            pp=e.find('Parameters')
            vals=(pp.text or '').split() if pp is not None else []
            break
    result={'plugin_name':name,'active_setup':setup,'plugin_version':ver,
            'active_parameter_tokens':vals,'token_count':len(vals)}
    if name=='REQ' and len(vals)>=30:
        # Waves REQ slot structure: five numeric tokens for each of six bands.
        # Type ID is intentionally uninterpreted (no guessing shelf/cut semantics).
        result['six_band_EQ_stored_values']=[
            {'band':i+1,'enabled_id':vals[i*5], 'type_id':vals[i*5+1],
             'gain_db':float(vals[i*5+2]),'frequency_hz':float(vals[i*5+3]),
             'q_or_width':float(vals[i*5+4])} for i in range(6)]
        result['stereo_band_tokens_identical']=vals[:30]==vals[30:60]
    elif name=='DeEsser' and len(vals)>=3:
        result['deesser_candidate_frequency_hz']=float(vals[0])
        result['deesser_candidate_threshold_db']=float(vals[2])
    return result


def inspect(path):
    raw,events=read_events(path)
    o={'source_filename':Path(path).name,'sha256':hashlib.sha256(raw).hexdigest(),
       'file_bytes':len(raw),'container':'FLhd/FLdt','fl_version':None,
       'track_name':None,'slots':[], 'warnings':[]}
    current=None
    for off,key,v in events:
        if key==199 and isinstance(v,bytes):o['fl_version']=v.decode('ascii','replace').strip('\x00')
        if key==204 and isinstance(v,bytes):o['track_name']=u16str(v)
        if key==201 and isinstance(v,bytes):
            current={'slot_index':None,'slot_name':u16str(v),'instrument_name':None,
                     'saved_parameter_bytes':None,'native_state':None,'waves':None}
            o['slots'].append(current)
        if current is None:continue
        if key==212 and isinstance(v,bytes) and len(v)>=8:
            current['slot_index']=struct.unpack_from('<I',v,4)[0]
        elif key==203 and isinstance(v,bytes):current['instrument_name']=u16str(v)
        elif key==213 and isinstance(v,bytes):
            current['saved_parameter_bytes']=len(v)
            current['waves']=get_waves_xml(v)
            if current['slot_name']=='Soundgoodizer' and len(v)>=12:
                version,mode,amount=struct.unpack_from('<III',v,0)
                current['native_state']={'state_version':version,'mode_index':mode,
                  'mode_letter':'ABCD'[mode] if mode<4 else None,
                  'amount_raw_integer':amount,
                  'amount_percent':None,
                  'note':'Percentage scale not verified; do not equate raw integer with percent'}
    used={s['slot_index'] for s in o['slots']}
    if used:
        o['empty_slots_before_last_plugin']=[x for x in range(max(used)+1) if x not in used]
    o['warnings']=['Stored state is not proof that a slot is audible/active; host bypass, wet/dry, mixer routing, and plugin installation require validation.',
      'Waves XML tokens are stored parameters, not verified mappings to physical knobs except explicitly identified fields.',
      'Proprietary plugin state (including Fresh Air) is not decoded.']
    return o


def main():
    p=argparse.ArgumentParser();p.add_argument('files',nargs='+');p.add_argument('-o','--output');a=p.parse_args()
    results=[inspect(f) for f in a.files]
    dumped=json.dumps({'files':results},indent=2)
    if a.output:
        path=Path(a.output)
        if path.exists():raise FileExistsError(path)
        path.write_text(dumped+'\n')
    else:print(dumped)

if __name__=='__main__':main()
