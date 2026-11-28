"""Battle UI for private full-sound attempts. No original receives a letter."""
import json
import hashlib
from pathlib import Path
from .html_listening_lab import make_lab


def build(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    temporary=output.with_suffix('.encoding.html')
    qa=make_lab(Path(manifest),temporary)
    text=temporary.read_text(encoding='utf-8')
    prior=json.JSONDecoder().raw_decode(text.split('const LAB = ',1)[1])[0]
    groups=[]
    for g in prior['groups']:
        refs=[c for c in g['clips'] if c['kind']=='reference']
        choices=[c for c in g['clips'] if c['kind']=='candidate']
        if len(refs)!=1 or len(choices)!=3:raise ValueError('Battle needs one original and three recreated contenders')
        groups.append({'id':g['id'],'title':g['title'],'note':g['note'],'reference':refs[0]['audio'],
                       'candidates':[{'letter':chr(65+i),'identity':c['identity'],'audio':c['audio']} for i,c in enumerate(choices)]})
    doc={'previous_sessions':[prior['session_id']],'groups':groups}
    write_lab(doc, output)
    temporary.unlink()
    return qa


def write_lab(doc, output):
    """Bind feedback to the actual audio mapping, retaining prior session IDs."""
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    groups = doc.get('groups', [])
    if not groups or len({g['id'] for g in groups}) != len(groups):
        raise ValueError('Expected unique comparison IDs')
    fingerprint = hashlib.sha256()
    for group in groups:
        candidates = group['candidates']
        group.setdefault('reviewable', bool(candidates))
        group.setdefault('verification', 'EXPERIMENTAL - not independently validated' if candidates else 'UNVERIFIED - reference only')
        if not candidates and group['reviewable']:
            raise ValueError('Reference-only group cannot be reviewable')
        if len(candidates) > 3 or [c['letter'] for c in candidates] != list('ABC'[:len(candidates)]):
            raise ValueError('Up to three consecutive candidate letters required')
        if len({c['identity'] for c in candidates}) != len(candidates):
            raise ValueError('Candidate identities must be distinct')
        for clip in [dict(audio=group['reference']), *candidates]:
            if not clip['audio'].startswith('data:audio/flac;base64,'):
                raise ValueError('Self-contained FLAC required')
        group['reference_sha256'] = hashlib.sha256(group['reference'].encode('ascii')).hexdigest()
        for candidate in candidates:
            candidate.setdefault('status', 'EXPERIMENTAL_UNVERIFIED')
            candidate['sha256'] = hashlib.sha256(candidate['audio'].encode('ascii')).hexdigest()
        fingerprint.update(json.dumps(group, sort_keys=True).encode('utf-8'))
    doc = {**doc, 'session_id': fingerprint.hexdigest()[:24]}
    payload = json.dumps(doc, ensure_ascii=True).replace('<', '\\u003c')
    output.write_text(TEMPLATE.replace('/*DATA*/', payload), encoding='utf-8')
    return doc['session_id']


from .battle_ui import TEMPLATE
