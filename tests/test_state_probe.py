import struct
import pytest
from skell_sound_match.wav_only.state_probe import fab_state,juce_component,waves_active_xml,ALPHABET

def raw():return b'FFBS'+struct.pack('<IIff',1,2,.25,-3.)+b'extra'
def encode(x):
 v=int.from_bytes(x,'little');return str(len(x))+'.'+''.join(ALPHABET[(v>>i)&63] for i in range(0,len(x)*8,6))
def test_raw():
 s=fab_state(raw());assert s.values==(.25,-3.) and s.trailing==b'extra' and s.version==1

def test_named():
 s=fab_state(b'FabF'+struct.pack('<II',2,3)+b'abc'+struct.pack('<IIf',0,1,.5));assert s.name_bytes==b'abc' and s.values==(.5,)

def test_component():
 x=raw();e=encode(x);assert juce_component(e)==x;assert fab_state(b'<IComponent>'+e.encode()+b'</IComponent>')==fab_state(x)
@pytest.mark.parametrize('x',[b'FFBS'+struct.pack('<II',1,100),b'FFBS'+struct.pack('<IIf',1,1,float('nan')),b'wrong bytes here',b'FabF'+struct.pack('<II',2,2048)+b'12345678'])
def test_bad_raw(x):
 with pytest.raises(ValueError):fab_state(x)
@pytest.mark.parametrize('v',['20.A','12.!!!!!!!!!!!!!!!','12.AAAAAAAAAAAAAAAAextra','1.AA'])
def test_bad_component(v):
 with pytest.raises(ValueError):juce_component(v)
def test_waves():
 x=b'<PresetChunkXMLTree><Preset><PresetHeader><PluginName>REQ</PluginName><PluginSubComp>RQ4S</PluginSubComp><ActiveSetup>SETUP_B</ActiveSetup></PresetHeader><PresetData Setup="SETUP_A"><Parameters Type="RealWorld">1 2</Parameters></PresetData><PresetData Setup="SETUP_B"><Parameters Type="RealWorld">3 * -4</Parameters></PresetData></Preset></PresetChunkXMLTree>'
 s=waves_active_xml(x)[0];assert s['values']==(3.,None,-4.) and s['setup']=='SETUP_B'
 with pytest.raises(ValueError):waves_active_xml(x.replace(b'3 * -4',b'nan'))
 with pytest.raises(ValueError):waves_active_xml(x.replace(b'SETUP_B</ActiveSetup>',b'SETUP_X</ActiveSetup>'))
