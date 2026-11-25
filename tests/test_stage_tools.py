import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import pytest
import numpy as np
from stage_tools import GateSettings,EchoSettings,gate,echo
@pytest.mark.parametrize('rate',[44100,48000,96000,192000])
def test_gate(rate):
    rng=np.random.default_rng(2);x=(rng.normal(size=(rate//2,2))*.025).astype(np.float32);x[rate//5:rate//4]*=5
    q=GateSettings(-30,110,-70)
    y=gate(x,rate,q)
    assert np.array_equal(y[:rate//4],gate(x[:rate//4],rate,q))
    assert np.isfinite(y).all();assert np.max(np.abs(y))<=np.max(np.abs(x))
    loud=np.where(np.max(abs(x),axis=1)>=10**(-30/20))[0]
    assert np.array_equal(y[loud],x[loud])
    assert np.all(gate(np.zeros_like(x),rate)==0)
@pytest.mark.parametrize('rate',[44100,48000,96000,192000])
def test_echo(rate):
    x=np.zeros((rate,2),np.float32);x[0,0]=1
    q=EchoSettings(100,.25,.1,1)
    y=echo(x,rate,q)
    n=rate//10
    assert y[0,0]==1 and y[n,1]==.25 and y[2*n,1]==.1
    assert y[n,0]==0 and y[2*n,0]==0
    assert np.array_equal(y[:rate//2],echo(x[:rate//2],rate,q))
    assert np.array_equal(echo(x,rate,EchoSettings(100,0,0,1)),x)
@pytest.mark.parametrize('bad',[GateSettings(0,60,-80),GateSettings(-30,-1,-90),GateSettings(-30,60,1),GateSettings(float('nan'),90,-60)])
def test_bad_gate(bad):
    with pytest.raises(ValueError):gate(np.ones((99,2),np.float32),44100,bad)
@pytest.mark.parametrize('bad',[EchoSettings(10,0,0,0),EchoSettings(100,2,0,0),EchoSettings(100,0,0,2),EchoSettings(float('nan'),0,0,0)])
def test_bad_echo(bad):
    with pytest.raises(ValueError):echo(np.ones((99,2),np.float32),44100,bad)
