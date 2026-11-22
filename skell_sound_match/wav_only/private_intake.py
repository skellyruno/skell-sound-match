"""Persistent private intake using the existing scanner and SHA-256 object cache.

No watcher or network service is started. Repeat the command for new batches.
Filename grouping remains a hypothesis; this never approves or trains presets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .skelly_bulk_match import open_db, scan_archives, items, materialize, write_catalog

TARGETS = ('deuce', 'alchemist', 'speakerz', 'hop_out', 'angelic_adlib',
           'muffle_adlib', 'wobbly_adlib', 'zaam_adlib')


def assert_private(workspace: Path) -> Path:
    workspace = workspace.expanduser().resolve()
    for parent in (workspace, *workspace.parents):
        if (parent / '.git').exists() or ((parent / 'pyproject.toml').exists()
                                         and (parent / 'skell_sound_match').is_dir()):
            raise ValueError('Private intake must be outside a source repository')
    return workspace


def intake(inputs: list[Path], workspace: Path) -> dict:
    workspace = assert_private(workspace)
    for source in inputs:
        source = source.expanduser().resolve()
        if source.is_dir() and (source == workspace or source in workspace.parents):
            raise ValueError('Intake folder must not contain its own workspace')
    db = open_db(workspace)
    try:
        scanned = scan_archives(inputs, workspace, db)
        rows = items(db)
        # Eagerly retain every verified audio object, including ZIP members.
        # Old uploads may disappear; materialize() can still replay cached objects.
        cached = {r['sha256']: str(materialize(r, workspace).relative_to(workspace))
                  for r in rows}
        catalog = write_catalog(workspace, db, scanned)
        previous_path = workspace / 'PRESET_REGISTER.json'
        previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else {}
        records = previous.get('presets', {})
        for target in sorted(set(TARGETS) | {r['target_id'] for r in rows}):
            group = [r for r in rows if r['target_id'] == target]
            old = records.get(target, {})
            records[target] = {**old, 'references': [
                {'sha256': r['sha256'], 'role_hint': r['role'], 'object': cached[r['sha256']],
                 'source': r['archive'], 'member': r['member'], 'frames': r['frames'],
                 'sample_rate': r['sample_rate'], 'channels': r['channels']}
                for r in group],
                'candidate_versions': old.get('candidate_versions', []),
                'measurements': old.get('measurements', []),
                'listening_results': old.get('listening_results', []),
                'unresolved': old.get('unresolved', ['Verify stage roles and same performance',
                    'Independent performance validation missing', 'Owner listening approval missing']),
                'status': old.get('status', 'REFERENCES_INDEXED' if group else 'NEEDS_REFERENCE')}
        register = {'schema': 'skelly.private.preset-register.v1', 'presets': records}
        payload = json.dumps(register, indent=2, ensure_ascii=True) + '\n'
        # Immutable snapshots preserve candidate history across repeated intake.
        digest = hashlib.sha256(payload.encode()).hexdigest()
        history = workspace / 'register_history'
        history.mkdir(exist_ok=True)
        snapshot = history / (digest + '.json')
        if not snapshot.exists():
            with snapshot.open('x', encoding='utf-8') as f:
                f.write(payload)
        temp = previous_path.with_suffix('.partial')
        temp.write_text(payload, encoding='utf-8')
        temp.replace(previous_path)
        return {'schema': 'skelly.private.persistent-intake.v1',
                'indexed_files': len(rows), 'unique_objects': len(cached),
                'duplicate_entries': len(rows)-len(cached), 'scan': scanned,
                'targets': [{'id': t['target_id'], 'status': t['status']} for t in catalog['targets']],
                'register_snapshot': snapshot.name,
                'independent_performance': 'UNVERIFIED'}
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=Path, nargs='+')
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(intake(args.inputs, args.workspace), indent=2))


if __name__ == '__main__':
    main()
