import pytest
from skell_sound_match.chain_evidence import StageEvidence, check_stage_order, evaluate_evidence

def m(score=4., tone=1., dynamics=1., width=1., band=1.):
    return dict(score=score,tone_db=tone,dynamics_db=dynamics,width_db=width,band_width=band)

def check(**kw):
    return evaluate_evidence(m(5),m(4.95),m(7.55),m(7.45),estimated_true_peak_db=-3,
                             source_active=True,reference_active=True,compared_same_stage=True,**kw)

def test_chain_accepts_verified_slots():
    assert check_stage_order((StageEvidence(1,'eq2','a'*64,True),StageEvidence(6,'conv','b'*64,True)))==()

def test_chain_rejects_duplicates():
    assert any('out-of-order' in x for x in check_stage_order((StageEvidence(6,'conv'),StageEvidence(6,'reverb'))))

def test_missing_state_is_not_claimed_native():
    assert any('no verified' in x for x in check_stage_order((StageEvidence(8,'reeverb2',None,True),)))

def test_unavailable_stage_is_visible():
    assert any('unavailable' in x for x in check_stage_order((StageEvidence(1,'compressor'),)))

def test_invalid_sha():
    assert any('checksum' in x for x in check_stage_order((StageEvidence(1,'eq','deadbeef',True),)))

def test_experimental_not_promotion():
    v=check();assert v['experimental_pass'] and not v['eligible_for_preset_promotion']

def test_requires_all_independent_evidence():
    v=check(independent_performance=True,untouched_holdout=True,owner_listening_approved=True)
    assert v['experimental_pass'] and v['eligible_for_preset_promotion']

def test_inactive_partition_rejected():
    v=evaluate_evidence(m(5),m(4),m(7),m(5),estimated_true_peak_db=-3,
        source_active=True,reference_active=False,compared_same_stage=True)
    assert not v['experimental_pass']

@pytest.mark.parametrize('metric',('tone_db','dynamics_db','width_db','band_width'))
def test_later_regressions_rejected(metric):
    old=m(7.55);new=m(7.4);new[metric]=1.26
    r=evaluate_evidence(m(5),m(4.9),old,new,estimated_true_peak_db=-3,
        source_active=True,reference_active=True,compared_same_stage=True)
    assert not r['experimental_pass']

@pytest.mark.parametrize('value',(float('nan'),float('inf'),-3.))
def test_invalid_measurements_rejected(value):
    new=m(7.45);new['dynamics_db']=value
    with pytest.raises(ValueError):
        evaluate_evidence(m(5),m(4.9),m(7.55),new,estimated_true_peak_db=-3,
            source_active=True,reference_active=True,compared_same_stage=True)

def test_peak_ceiling():
    v=evaluate_evidence(m(5),m(4.9),m(7.55),m(7.45),estimated_true_peak_db=0,
        source_active=True,reference_active=True,compared_same_stage=True)
    assert not v['experimental_pass']

def test_train_score_must_improve():
    v=evaluate_evidence(m(5),m(5),m(7.55),m(7.4),estimated_true_peak_db=-3,
        source_active=True,reference_active=True,compared_same_stage=True)
    assert not v['experimental_pass']

def test_strict_bool_flags():
    with pytest.raises(ValueError):
        evaluate_evidence(m(5),m(4),m(7.55),m(7.45),estimated_true_peak_db=-3,
            source_active=1,reference_active=True,compared_same_stage=True)
