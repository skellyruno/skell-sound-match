import pytest
from skell_sound_match.effect_coverage import SavedSlot, RenderedSlot, audit_saved_slots
H = 'a' * 64

def test_exact_coverage():
    r = audit_saved_slots([SavedSlot(2,'EQ',H)], [RenderedSlot(2,'EQ',H)])
    assert r.replayed == (2,)
    assert r.all_saved_slots_accounted_for

def test_modulation_missing():
    r = audit_saved_slots([SavedSlot(0,'EQ',H),SavedSlot(5,'Chorus',H),SavedSlot(6,'Flanger',H)], [RenderedSlot(0,'EQ',H)])
    assert r.missing == (5,6) and not r.all_saved_slots_accounted_for

def test_approximation_not_replay():
    r = audit_saved_slots([SavedSlot(0,'Phaser',H)], [RenderedSlot(0,'Phaser',H,'approximation')])
    assert r.approximate == (0,) and not r.all_saved_slots_accounted_for

@pytest.mark.parametrize('effect,digest',[('Gate',H),('EQ','b'*64)])
def test_mismatch(effect,digest):
    r = audit_saved_slots([SavedSlot(0,'EQ',H)],[RenderedSlot(0,effect,digest)])
    assert r.mismatched == (0,) and not r.all_saved_slots_accounted_for

def test_unexpected():
    r = audit_saved_slots([SavedSlot(0,'EQ',H)],[RenderedSlot(0,'EQ',H),RenderedSlot(1,'Delay',H)])
    assert r.unexpected == (1,) and not r.all_saved_slots_accounted_for

@pytest.mark.parametrize('slot,effect,digest',[(True,'EQ',H),(-1,'EQ',H),(0,'',H),(0,'EQ','bad')])
def test_invalid(slot,effect,digest):
    with pytest.raises(ValueError): audit_saved_slots([SavedSlot(slot,effect,digest)],[])

def test_duplicate():
    with pytest.raises(ValueError): audit_saved_slots([SavedSlot(0,'EQ',H),SavedSlot(0,'EQ',H)],[])

def test_no_evidence():
    with pytest.raises(ValueError): audit_saved_slots([],[])

def test_unknown_mode():
    with pytest.raises(ValueError): audit_saved_slots([SavedSlot(0,'EQ',H)],[RenderedSlot(0,'EQ',H,'guessed')])
