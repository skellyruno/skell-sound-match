import pytest
from skell_sound_match.wav_only.tone_first_policy import assess, audible_proxy, quality, ready

def metric(score=5,tone=2,env=2,wave_db=-3,side=1):
    return dict(score=score,tone=tone,env=env,wave_db=wave_db,side=side)

def test_tone_win_with_waveform_disagreement():
    b=metric(); c=metric(score=4,tone=.8,wave_db=1)
    r=assess(c,b)
    assert r['quality_pass'] and r['waveform_worse'] and not r['target_met']

def test_tone_win_retained_when_composite_not_ready():
    b=metric(); c=metric(score=6,tone=.4,env=9,wave_db=2)
    assert assess(c,b)['retain_for_repair'] and not quality(c,b)

def test_safety_not_overridden_by_tone():
    b=metric(); c=metric(score=3,tone=.4)
    a=dict(peak44=-1.2,peak48=-1.3,stress=-.2,latency=0,previous_latency=0)
    assert ready(c,b,**a)
    for k,v in [('peak44',-.9),('peak48',.1),('stress',.01),('latency',1),('stress',float('nan'))]:
        assert not ready(c,b,**(a|{k:v}))

def test_dynamics_and_stereo_preserved():
    b=metric(); assert not quality(metric(score=3,tone=.3,env=3),b)
    assert not quality(metric(score=3,tone=.3,side=3),b)

def test_target_and_validation():
    assert assess(metric(score=1,tone=.1),metric())['target_met']
    assert not assess(metric(score=1.001,tone=.1),metric())['target_met']
    with pytest.raises(ValueError): audible_proxy(metric(tone=float('nan')))
