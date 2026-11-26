"""Private reference routing: stage identity first; acoustic rank advisory only."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import numpy as np
import soundfile as sf
from .vocal_retrieval import descriptor, prototypes, rank_prototypes
from .assistant_preview import preview_files

STAGES = frozenset(('main','complete','adlib-base','delay-return','doubler-return','reverb-return','isolated-modulation','isolated-delay','isolated-wet'))

@dataclass(frozen=True)
class Reference:
    key: str
    take: str
    family: str
    stage: str
    path: str
    sha256: str
    reviewed: bool


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def resolve(root, entry):
    p=Path(root).resolve(); q=(p/entry.path).resolve()
    if not q.is_relative_to(p) or not q.is_file() or digest(q)!=entry.sha256:
        raise ValueError('unverified reference bytes or path')
    return q


def validate(entries):
    rows=list(entries)
    if len({e.key for e in rows})!=len(rows):raise ValueError('duplicate reference key')
    for e in rows:
        if not all(isinstance(v,str) and v.strip() for v in (e.key,e.take,e.family,e.path,e.sha256)) or e.stage not in STAGES or type(e.reviewed) is not bool or len(e.sha256)!=64 or any(c not in '0123456789abcdef' for c in e.sha256):
            raise ValueError('invalid reference metadata')
    return rows


def choose_exact(root, entries, *, take, stage, family):
    """Only reviewed, unique, exact metadata may route a fitting job."""
    if stage not in STAGES or not take or not family:raise ValueError('explicit take/family/stage required')
    rows=[e for e in validate(entries) if e.reviewed and (e.take,e.stage,e.family)==(take,stage,family)]
    if len(rows)!=1:raise ValueError('missing or ambiguous reviewed same-take reference')
    return rows[0],resolve(root,rows[0])


def suggest(root, entries, audio, rate, *, stage, family=None):
    """Acoustic shortlist of reviewed exact-stage entries; never enables fit."""
    if stage not in STAGES:raise ValueError('explicit processing stage required')
    rows=[e for e in validate(entries) if e.reviewed and e.stage==stage and (family is None or e.family==family)]
    if not rows:return []
    bank=[]
    for e in rows:
        p=resolve(root,e); info=sf.info(p)
        if not 32000<=info.samplerate<=384000 or info.channels not in (1,2) or info.frames<info.samplerate:raise ValueError('unsupported reference geometry')
        x,sr=sf.read(p,frames=min(info.frames,12*info.samplerate),always_2d=True)
        bank.append((e.key,prototypes(x,sr)))
    return rank_prototypes(descriptor(audio,rate),bank)


def fit_exact(root,entries,source,output,*,source_sha256,take,stage,family,alignment_confirmed=False):
    if alignment_confirmed is not True:raise ValueError('caller must confirm alignment and candidate stage')
    e,p=choose_exact(root,entries,take=take,stage=stage,family=family)
    return preview_files(source,p,output,source_sha256=source_sha256,reference_sha256=e.sha256,take=take,stage=stage,pair_confirmed=True)
