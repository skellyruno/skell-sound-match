import pytest
from skell_sound_match.wav_only.tone_repair_frontier import frontier,preserves_tone,target_reached

def m(score=5,tone=2,env=2,wave_db=0,side=2):return dict(score=score,tone=tone,env=env,wave_db=wave_db,side=side)
def test_keeps_tone_even_if_bad_composite():
    assert 'tone' in frontier([('base',m()),('tone',m(10,.2,8,5,9))])
def test_protects_improved_seed():
    assert not preserves_tone(m(tone=.7),m(tone=.2),m(tone=1))
    assert preserves_tone(m(tone=.22),m(tone=.2),m(tone=1))
def test_keeps_other_metric_extremes():
    r=[('tone',m(tone=.1)),('score',m(score=1)),('env',m(env=.1)),('side',m(side=.1)),('wave',m(wave_db=-10))]
    assert set(frontier(r,5))=={k for k,_ in r}
def test_dominated_excluded():
    assert frontier([('a',m()),('b',m(6,3,3,1,3))])==['a']
def test_target_unchanged():
    assert target_reached(m(score=1)) and not target_reached(m(score=1.00001))
def test_invalid():
    for rows in [[('a',m(tone=float('nan')))],[('a',m()),('a',m())]]:
        with pytest.raises(ValueError):frontier(rows)
    with pytest.raises(ValueError):frontier([('a',m())],4)
def test_empty():assert frontier([])==[]
