import copy
import pytest
from skell_sound_match.parameter_evidence import validate_evidence, EvidenceError

BASE = {'stages': [{'name': 'main', 'slots': [{'slot': 3, 'plugin': 'Synthetic Compressor', 'parameters': [
    {'name': 'attack', 'value': 12.9, 'unit': 'ms', 'status': 'confirmed', 'origin': 'screenshot', 'source': 'synthetic_ui.png'},
    {'name': 'amount_raw', 'value': 503, 'unit': 'raw', 'status': 'confirmed', 'origin': 'fst_serialized', 'source': 'synthetic.fst'},
]}]}]}

def test_valid_evidence_unchanged():
    result = validate_evidence(BASE)
    assert result == BASE and result is not BASE

def test_reject_unverified_raw_percent_conversion():
    value = copy.deepcopy(BASE)
    value['stages'][0]['slots'][0]['parameters'][1]['unit'] = '%'
    with pytest.raises(EvidenceError):
        validate_evidence(value)

def test_reject_duplicate_slots():
    value = copy.deepcopy(BASE)
    value['stages'][0]['slots'].append(copy.deepcopy(value['stages'][0]['slots'][0]))
    with pytest.raises(EvidenceError):
        validate_evidence(value)

def test_reject_guessed_physical_parameters():
    value = copy.deepcopy(BASE)
    value['stages'][0]['slots'][0]['parameters'][0]['origin'] = 'measured_audio'
    with pytest.raises(EvidenceError):
        validate_evidence(value)

def test_explicit_unknown_allowed():
    value = copy.deepcopy(BASE)
    value['stages'][0]['slots'][0]['parameters'].append({
        'name': 'release', 'value': None, 'unit': 'ms', 'status': 'unknown',
        'origin': 'screenshot', 'source': 'synthetic_ui.png'
    })
    assert validate_evidence(value) == value
