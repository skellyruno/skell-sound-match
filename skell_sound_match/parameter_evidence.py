"""Preserve verified versus inferred plugin-setting evidence without unsafe conversions."""
from __future__ import annotations
from copy import deepcopy

STATUS = {'confirmed', 'estimated', 'unknown'}
ORIGIN = {'screenshot', 'fst_serialized', 'measured_audio', 'user_statement'}

class EvidenceError(ValueError):
    pass

def validate_evidence(document: dict) -> dict:
    """Validate local, potentially private preset annotations without unit guessing."""
    if not isinstance(document, dict):
        raise EvidenceError('Document must be an object')
    doc = deepcopy(document)
    stages = doc.get('stages')
    if not isinstance(stages, list) or not stages:
        raise EvidenceError('Nonempty stages required')
    for stage in stages:
        if not isinstance(stage, dict) or not isinstance(stage.get('name'), str) or not stage['name'].strip():
            raise EvidenceError('Stage needs a name')
        slots = stage.get('slots', [])
        if not isinstance(slots, list):
            raise EvidenceError('Stage slots must be a list')
        indices = set()
        for slot in slots:
            i = slot.get('slot')
            if type(i) is not int or i < 1 or i in indices:
                raise EvidenceError('Slot indices must be unique positive integers')
            indices.add(i)
            if not isinstance(slot.get('plugin'), str) or not slot['plugin'].strip():
                raise EvidenceError('Plugin name missing')
            names = set()
            for p in slot.get('parameters', []):
                name = p.get('name')
                if not isinstance(name, str) or not name.strip() or name in names:
                    raise EvidenceError('Parameter names must be unique nonempty strings')
                names.add(name)
                if p.get('status') not in STATUS or p.get('origin') not in ORIGIN:
                    raise EvidenceError('Status/origin must be explicit')
                if not isinstance(p.get('source'), str) or not p['source'].strip():
                    raise EvidenceError('Every parameter needs a source')
                unit = p.get('unit')
                if not isinstance(unit, str) or not unit.strip():
                    raise EvidenceError('Parameter unit must be explicit')
                val = p.get('value')
                if val is None and p.get('status') != 'unknown':
                    raise EvidenceError('Only unknown parameters can have missing values')
                if isinstance(val, (dict, list, bool)):
                    raise EvidenceError('Parameter value must be scalar or unknown')
                if p['origin'] == 'fst_serialized' and unit != 'raw' and not p.get('mapping_verified', False):
                    raise EvidenceError('Cannot convert serialized value to physical units without verified mapping')
                if p['status'] == 'confirmed' and p['origin'] == 'measured_audio':
                    raise EvidenceError('Audio-derived knobs are estimates, not confirmed settings')
    return doc
