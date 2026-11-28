import pytest
from skell_sound_match.partial_feedback import bind_partial_feedback


def fixture():
    m = [{'id': str(i), 'name': 'Test '+str(i), 'clips': {'ref': {'sha256':'a'*64}, 'A': {'sha256':'b'*64}, 'B': {'sha256':'c'*64}}} for i in range(2)]
    p = {'format':'SKELLY_SOUND_MATCH_R19_FEEDBACK', 'partial':True, 'entries':[{'id':'0','title':'Test 0','original_sha256':'a'*64,'candidate_sha256':{'A':'b'*64,'B':'c'*64},'experimental_pass':True,'vote':'B','notes':''}]}
    return p,m


def test_subset():
    p,m=fixture();r=bind_partial_feedback(p,m)
    assert r['partial'] and r['unreviewed_ids']==['1'] and len(r['votes'])==1
    assert r['votes'][0]['selected_sha256']=='c'*64 and not r['votes'][0]['preset_promotion']


def test_empty_review():
    p,m=fixture();p['entries']=[];r=bind_partial_feedback(p,m)
    assert not r['votes'] and r['unreviewed_ids']==['0','1']


@pytest.mark.parametrize('bad',['partial','candidate','unknown','duplicate','missing_hash','manifest_duplicate'])
def test_reject(bad):
    p,m=fixture()
    if bad=='partial':p['partial']=False
    elif bad=='candidate':p['entries'][0]['candidate_sha256']['B']='d'*64
    elif bad=='unknown':p['entries'][0]['id']='missing'
    elif bad=='duplicate':p['entries']*=2
    elif bad=='missing_hash':del p['entries'][0]['candidate_sha256']
    else:m.append(m[0])
    with pytest.raises(ValueError):bind_partial_feedback(p,m)
