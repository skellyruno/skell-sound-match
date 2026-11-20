import numpy as np
import pytest
from skell_sound_match.onset_review import review_onset_edit

SR = 16000

def fixtures():
    t = np.arange(2*SR)/SR
    ref = (.18*np.sin(2*np.pi*165*t))[:,None]
    ref[:SR//3]=0
    base = ref.copy()
    base[SR//4:SR//3] += .015  # synthetic pre-echo
    trial = base.copy()
    trial[SR//4:SR//3] = 0
    return ref,base,trial


def test_one_edit_improves_reference():
    ref,base,trial=fixtures()
    r=review_onset_edit(ref,base,trial,SR)
    assert r['event_count']==1
    assert r['whole_clip_reference_error']['trial_minus_champion_db'] < -20
    assert r['events'][0]['local_evidence']=='improvement'


def test_identical_is_not_promoted():
    ref,base,trial=fixtures()
    r=review_onset_edit(ref,base,base,SR)
    assert r['event_count']==0 and r['modified_sample_fraction']==0
    assert r['recommended_decision']=='keep_current_champion_until_blind_listening'


def test_regression_detected():
    ref,base,trial=fixtures()
    r=review_onset_edit(ref,ref,base,SR)
    assert r['events'][0]['local_evidence']=='regression'
    assert r['whole_clip_reference_error']['trial_minus_champion_db']>20


def test_stereo_and_dry_source():
    ref,base,trial=fixtures()
    r=review_onset_edit(np.repeat(ref,2,axis=1),np.repeat(base,2,axis=1),np.repeat(trial,2,axis=1),SR,dry=np.repeat(ref,2,axis=1))
    assert r['channel_count']==2
    assert 'dry_rms_in_edit_dbfs' in r['events'][0]


def test_misaligned_rejected():
    ref,base,trial=fixtures()
    with pytest.raises(ValueError,match='sample aligned'):
        review_onset_edit(ref,base[:-17],trial,SR)
    with pytest.raises(ValueError,match='sample aligned'):
        review_onset_edit(ref,base,trial,SR,dry=ref[:-10])


def test_nan_and_bad_settings_rejected():
    ref,base,trial=fixtures()
    bad=trial.copy(); bad[1000]=np.nan
    with pytest.raises(ValueError,match='nonfinite'):
        review_onset_edit(ref,base,bad,SR)
    with pytest.raises(ValueError,match='Unsafe'):
        review_onset_edit(ref,base,trial,SR,edit_threshold_dbfs=0)


def test_input_arrays_not_mutated():
    ref,base,trial=fixtures()
    snapshots=[x.copy() for x in (ref,base,trial)]
    review_onset_edit(ref,base,trial,SR)
    assert all(np.array_equal(x,y) for x,y in zip((ref,base,trial),snapshots))


def test_merging_small_gaps():
    ref,base,trial=fixtures()
    trial[SR//4+120:SR//4+180]=base[SR//4+120:SR//4+180]
    r=review_onset_edit(ref,base,trial,SR,merge_gap_ms=8)
    assert r['event_count']==1