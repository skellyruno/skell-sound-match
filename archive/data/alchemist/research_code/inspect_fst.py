#!/usr/bin/env python3
"""Read FL Studio .fst metadata without executing arbitrary plugin blobs.

This is *not* a Waves-format parameter decoder. Numeric vector indexes stay raw.
"""
import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

PRESET_XML = re.compile(rb'<PresetChunkXMLTree\b.*?</PresetChunkXMLTree>', re.DOTALL)

def inspect_fst(path):
    data = Path(path).read_bytes()
    result = {'file':Path(path).name, 'bytes':len(data), 'fl_studio_format':data[:4] == b'FLhd', 'embedded_plugins':[]}
    for i, match in enumerate(PRESET_XML.finditer(data)):
        root=ET.fromstring(match.group())
        p=root.find('Preset')
        if p is None:
            continue
        head=p.find('PresetHeader')
        h=lambda k: head.findtext(k) if head is not None else None
        active=h('ActiveSetup')
        setups=[]
        for st in p.findall('PresetData'):
            n=st.find('Parameters')
            raw=(n.text or '').split() if n is not None else []
            setups.append({'id':st.attrib.get('Setup'),'name':st.attrib.get('SetupName'),
                           'raw_parameter_count':len(raw), 'raw_parameters':raw})
        tail=data[match.end():match.end()+180]
        bypass=re.search(rb'<Bypass\b[^>]*?Bypass="([01])"',tail)
        result['embedded_plugins'].append({'position':i+1,'name':h('PluginName'),
            'plugin_version':h('PluginVersion'),'preset_name':p.attrib.get('Name'),
            'active_setup':active,'bypassed_in_chunk':bool(int(bypass.group(1))) if bypass else None,
            'setups':setups})
    result['caution']=('FL Studio host state and plugin-specific numeric vectors are not a validated mapping '
                        'to Waves control names. This inspection does not prove external routing, '
                        'missing plugins, or audible effect contribution.')
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('file');a.add_argument('-o','--output')
    p=a.parse_args()
    r=inspect_fst(p.file)
    s=json.dumps(r,indent=2)
    if p.output:Path(p.output).write_text(s,encoding='utf-8')
    print(s)
