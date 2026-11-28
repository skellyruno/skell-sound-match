import pytest
from skell_sound_match.wav_only.milestone import summarize_milestone, safe_worst_score


def row(id='a', a=1.4, b=1.5, peak=-1., stress=0.):
    return dict(id=id, score44=a, score48=b, peak44_dbTP=peak,
                peak48_dbTP=peak, stress44_dbTP=stress, stress48_dbTP=stress)


def test_exact_boundary_and_two_rates():
    assert safe_worst_score(row()) == 1.5
    r = summarize_milestone(['a','b'], [row(),row('b',.8,1.501)])
    assert r['qualifying'] == ['a'] and r['required'] == 2


def test_duplicate_versions_count_once_and_missing_stays():
    r = summarize_milestone(list('abc'),[row(a=.8,b=.9),row(a=.7,b=.8)])
    assert r['count'] == 1 and r['total'] == 3 and r['best_safe_scores']['a']==.8
    assert r['missing_safe'] == ['b','c']


def test_peak_safety_unchanged_when_threshold_relaxes():
    records = [row('a',.1,.2,peak=-.99),row('b',.2,.3,stress=.01),row('c',1.2,1.3)]
    assert summarize_milestone(list('abc'),records,1)['count']==0
    assert summarize_milestone(list('abc'),records,1.5)['qualifying']==['c']


def test_milestone_33():
    ids = [str(i) for i in range(33)]
    r = summarize_milestone(ids,[row(i) for i in ids[:23]])
    assert r['required']==24 and r['remaining']==1


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1,True,'1'])
def test_bad_score(bad):
    assert safe_worst_score(row(a=bad)) is None


def test_invalid_cases():
    with pytest.raises(ValueError): summarize_milestone(['a','a'],[])
    with pytest.raises(ValueError): summarize_milestone(['a'],[row('b')])
    with pytest.raises(ValueError): summarize_milestone(['a'],[],float('nan'))
