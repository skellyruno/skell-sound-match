import math
import pytest
from skell_sound_match.chain_evidence import StageEvidence, PairProvenance, check_pair_provenance, check_stage_order, evaluate_evidence

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

def provenance(**overrides):
    data=dict(source_take_id="take7",reference_take_id="take7",candidate_take_id="take7",
        source_sha256="a"*64,reference_sha256="b"*64,candidate_sha256="c"*64,
        source_rate=44100,reference_rate=44100,candidate_rate=44100,
        reference_stage="full-effects",candidate_stage="full-effects",
        source_offset_samples=0,reference_offset_samples=0,candidate_offset_samples=0,
        offsets_verified=True,evidence_origin="export_manifest")
    data.update(overrides)
    return PairProvenance(**data)

def test_requires_all_independent_evidence():
    v=check(independent_performance=True,untouched_holdout=True,owner_listening_approved=True,
            pair_provenance=provenance())
    assert v['experimental_pass'] and v['eligible_for_preset_promotion']

def test_approval_flags_cannot_bypass_missing_pair():
    v=check(independent_performance=True,untouched_holdout=True,owner_listening_approved=True)
    assert v['experimental_pass'] and not v['eligible_for_preset_promotion']
    assert 'source/reference take provenance missing' in v['reasons']

@pytest.mark.parametrize('override,expect',[
    ({'source_take_id':''},'take ID missing'),
    ({'reference_take_id':'other'},'take IDs disagree'),
    ({'reference_stage':'stereo-only'},'processing stage mismatch'),
    ({'reference_sha256':'bad'},'checksum missing or invalid'),
    ({'candidate_rate':48000},'sample rates disagree'),
    ({'offsets_verified':False},'offsets not independently verified'),
    ({'candidate_offset_samples':2.5},'offsets not independently verified'),
    ({'evidence_origin':'user_guess'},'evidence not verified'),
])
def test_pair_provenance_blockers(override,expect):
    v=check_pair_provenance(provenance(**override))
    assert any(expect in r for r in v)
    result=check(independent_performance=True,untouched_holdout=True,owner_listening_approved=True,
        pair_provenance=provenance(**override))
    assert not result['eligible_for_preset_promotion']

def test_pair_provenance_no_audio_similarity_override():
    assert check_pair_provenance(None)
    assert not check_pair_provenance(provenance())

def test_inactive_partition_rejected():
    v=evaluate_evidence(m(5),m(4),m(7),m(5),estimated_true_peak_db=-3,
        source_active=True,reference_active=False,compared_same_stage=True)
    assert not v['experimental_pass']

@pytest.mark.parametrize('metric',('tone_db','dynamics_db','width_db','band_width'))
def test_later_regressions_rejected(metric):
    old=m(7.55);new=m(7.4);new[metric]=1.26
    r=evaluate_evidence(m(5),m(4.9),old,new,estimated_true_peak_db=-3,source_active=True,reference_active=True,compared_same_stage=True)
    assert not r['experimental_pass']

@pytest.mark.parametrize('value',(float('nan'),float('inf'),-3.))
def test_invalid_measurements_rejected(value):
    new=m(7.45);new['dynamics_db']=value
    with pytest.raises(ValueError):evaluate_evidence(m(5),m(4.9),m(7.55),new,estimated_true_peak_db=-3,
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
    with pytest.raises(ValueError):evaluate_evidence(m(5),m(4),m(7.55),m(7.45),estimated_true_peak_db=-3,
        source_active=1,reference_active=True,compared_same_stage=True)
