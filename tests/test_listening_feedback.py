import pytest
from skell_sound_match.listening_feedback import bind_feedback

def fixture():
    return ({'format':'R','entries':[{'id':'one','title':'One','original_sha256':'a'*64,'experimental_pass':False,'vote':'A','notes':''}]},[{'id':'one','title':'One','passed':False,'stats':{'ref':{'sha256':'a'*64},'A':{'sha256':'b'*64},'B':{'sha256':'c'*64}}}])

@pytest.mark.parametrize('vote,selected,rejected',[('A','b',['c']),('B','c',['b']),('neither',None,['b','c'])])
def test_binding(vote,selected,rejected):
    p,m=fixture();p['entries'][0]['vote']=vote
    r=bind_feedback(p,m,expected_format='R')[0]
    assert r['selected_sha256']==(selected*64 if selected else None)
    assert r['rejected_sha256']==[s*64 for s in rejected] and not r['preset_promotion']

@pytest.mark.parametrize('field,value',[('id','wrong'),('title','other'),('original_sha256','d'*64),('experimental_pass',True),('vote','C'),('notes',None),('candidate_sha256',{'A':'c'*64,'B':'b'*64})])
def test_invalid(field,value):
    p,m=fixture();p['entries'][0][field]=value
    with pytest.raises(ValueError):bind_feedback(p,m,expected_format='R')

def test_missing_and_duplicates():
    p,m=fixture();p['entries']=[]
    with pytest.raises(ValueError):bind_feedback(p,m,expected_format='R')
    p,m=fixture();p['entries']*=2;m.append(dict(m[0],id='two'))
    with pytest.raises(ValueError):bind_feedback(p,m,expected_format='R')

def test_identical_candidates():
    p,m=fixture();m[0]['stats']['A']=m[0]['stats']['B']
    with pytest.raises(ValueError):bind_feedback(p,m,expected_format='R')


def test_three_way_vote():
    p,m=fixture();m[0]['stats']['C']={'sha256':'d'*64};p['entries'][0]['vote']='C'
    p['entries'][0]['candidate_sha256']={'A':'b'*64,'B':'c'*64,'C':'d'*64}
    r=bind_feedback(p,m,expected_format='R')[0]
    assert r['selected_sha256']=='d'*64 and r['rejected_sha256']==['b'*64,'c'*64]


def test_three_way_neither():
    p,m=fixture();m[0]['stats']['C']={'sha256':'d'*64};p['entries'][0]['vote']='neither'
    r=bind_feedback(p,m,expected_format='R')[0]
    assert r['selected_sha256'] is None and len(r['rejected_sha256'])==3
