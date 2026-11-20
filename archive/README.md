# Skell Sound Match — research archive

The owner explicitly approved the historical Deuce and Alchemist matching archive for publication in this public repository. Deleting a public file later cannot revoke copies already made. Preserve original source bytes, FSTs, protected candidates and checksums; do not add new private vocals, FLPs, FSTs or proprietary plugin states without separate explicit approval.

## Contents

- data/deuce/: original 24-bit audio stages (dry, recording-only, main-only, combined), REC/MAIN FST states, protected history and lossless A/original, D/Max and E/onset comparison excerpts, plus source screenshots.
- data/alchemist/: original-stage exports, MAIN.fst, protected Hybrid v0.3 / experimental v0.7 candidates, reports, legacy code and FST structures. The input recording already contains printed recording/REC effects; it is **not untreated dry vocal**.
- data/reports/: objective measurements and historical handoffs. The archived data/reports/handoff_notes.md is an older uploaded handoff; its date-specific status is superseded by docs/SOUND_MATCHING_HANDOFF_2026-11-20.md. Do not edit this checksum-backed archive copy.
- recipes/deuce.json and recipes/alchemist.json: evidence-tagged source-chain records and future integration planning inputs. They are **not** native VST3 presets or exact proprietary plugin emulations.

Larger FLACs are stored as ordered SHA-256-verified chunks under archive/chunks/; smaller assets are in archive/data/. archive/manifest.json records original names, sample metadata, SHA-256 hashes and reconstruction paths.

## Restore and verify

~~~powershell
python scripts/materialize_archive.py --verify
python scripts/materialize_archive.py --restore --output local_sound_archive
~~~

The restore tool refuses to overwrite differing existing files. FLAC reconstruction is lossless.

## Current approval register

- **Deuce:** offline v2.5 is the latest owner-preferred listening sound (explicit approval 2026-11-15). D/Max remains the protected rollback reference. Older v1.3A/v1.4/v1.7 and v2.3/v2.4 material stays archived; v1.4 contour and phrase-specific v2.4 are not approved replacements. Only the 15-second D/Max extract is in this archive; do not invent a full-length D/Max render.
- **Alchemist:** Hybrid v0.3 is a historically owner-preferred offline candidate. v0.7 and later native factories are experimental; the final latest preference has not been reconfirmed. Factory 43 is the protected native baseline; no Factory 45 or 47–54 candidate is approved.
- **Native integration:** recipes remain blocked from automatic native recall until every processor and parameter has a verified native mapping and actual same-take host audio validation.

Historical Python modules are preserved as research evidence, not trusted production DSP. Unclassified source screenshots remain unclassified; do not infer project association.