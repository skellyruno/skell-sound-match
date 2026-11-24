import copy
import pytest
from skell_sound_match.wav_only.battle_feedback_v2 import validate_v2


def payload():
    def group(gid, count, **kwargs):
        candidates = [dict(letter=chr(65+i), identity=f'{gid}-{i}', sha256='a'*64, status='EXPERIMENTAL') for i in range(count)]
        return dict(group_id=gid, preset=gid, reviewable=True, submitted=False, winner='', eliminate='', rating=None,
                    verification='EXPERIMENTAL', reference_sha256='b'*64, notes='', candidate_versions=candidates,
                    survivors=[v['identity'] for v in candidates]) | kwargs
    return dict(schema='skelly.sound-battle-feedback.v2',session_id='now',previous_sessions=['old'],results=[
        group('a',3,submitted=True,winner='B',eliminate='C',survivors=['a-0','a-1']),
        group('gate',1,submitted=True,rating=4),group('speakerz',0,reviewable=False),
        group('deuce',2,reviewable=False),group('draft',3,winner='B',eliminate='A',survivors=['draft-1','draft-2']),
        group('pair',2,submitted=True,winner='A'),group('tie',3,submitted=True,winner='tie')])


def test_current_feedback_keeps_exact_metadata_and_never_promotes_drafts():
    p=payload();plan=validate_v2(p,{'deuce'});a,gate,speakerz,deuce,draft,pair,tie=plan['groups']
    assert a['winner_identity']=='a-1' and a['eliminated_identity']=='a-2'
    assert a['candidate_versions']==p['results'][0]['candidate_versions']
    assert a['reference_sha256']=='b'*64 and plan['previous_sessions']==['old']
    assert gate['rating']==4 and gate['winner_identity'] is None
    assert speakerz['queue_state']=='recover_review_material' and deuce['queue_state']=='repair_reference_first'
    assert draft['winner_identity'] is None and draft['survivors']==['draft-0','draft-1','draft-2']
    assert pair['survivors']==['pair-0','pair-1'] and tie['survivors']==['tie-0','tie-1','tie-2']
    assert all(not g['listening_approved'] for g in plan['groups'])


@pytest.mark.parametrize('i,key,value',[(0,'reference_sha256','bad'),(0,'winner','C'),(0,'survivors',[]),
    (1,'rating',True),(1,'rating',6),(1,'rating',None),(2,'submitted',True),(3,'winner','A'),
    (6,'eliminate','C'),(0,'submitted','true'),(0,'eliminate',''),(0,'reviewable',False)])
def test_invalid_feedback_rejected(i,key,value):
    p=payload();p['results'][i][key]=value
    with pytest.raises(ValueError):validate_v2(p)


def test_candidate_hash_and_duplicate_history_rejected():
    p=payload();p['results'][0]['candidate_versions'][0]['sha256']='bad'
    with pytest.raises(ValueError):validate_v2(p)
    p=payload();p['previous_sessions']=['old','old']
    with pytest.raises(ValueError):validate_v2(p)
