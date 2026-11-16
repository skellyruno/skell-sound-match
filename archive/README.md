# Skell Sound Match — research archive

The owner explicitly chose to publish the matching data in this GitHub repository. **It is public** and should be treated as a public research archive; deleting or changing the repository later cannot revoke existing copies.

## Contents

- `data/deuce/`: 4 original 24-bit audio stages (dry, recording-only, main-only, combined), recording/main `.fst` states, protected v1.4/v1.7, 15-second A/original, D/Max champion and E/onset experiment, plus 14 configuration screenshots.
- `data/alchemist/`: 4 original-stage exports, `MAIN.fst`, the v0.3 Hybrid candidate and v0.7 experimental render. The input recording already includes printed tracking effects and is **not fully dry**.
- `data/reports/`: objective measurements and source handoff notes.
- `recipes/deuce.json`, `recipes/alchemist.json`: versioned, evidence-tagged effect-chain recipes intended as *future inputs* to Skell Preset and Skell AdlibLab. These **are not native VST3 presets** and must not be represented as exact proprietary plugin emulations.

To avoid failures with GitHub's binary connector, some larger audio files are stored in ordered, SHA-256-verified chunks under `archive/chunks/`; smaller files are in `archive/data/`. `archive/manifest.json` provides the original name, 24-bit FLAC sample metadata, SHA-256 hash and reconstruction path for each asset.

## Restore

On checkout (Python 3.10+):

```powershell
python scripts/materialize_archive.py --verify
python scripts/materialize_archive.py --restore --output "local_sound_archive"
```

No extra packages are required to verify/restore the FLAC and `.fst` bytes. FLAC is lossless; for WAV conversion use a dedicated sample-preserving converter (`soundfile` can restore PCM_24). The tool never overwrites differing existing files.

## Reusing a recipe

```python
from skell_sound_match.recipe_export import read_recipe, create_integration_plan
recipe = read_recipe('recipes/deuce.json')
plan = create_integration_plan(recipe, 'skell-preset', {})
assert not plan['ready']  # Native DSP algorithms + automation IDs are NOT yet implemented
```

Only promote integration plans after implementing the target processors and checking real audio, latency, CPU, automation recall, and FL Studio runtime behavior. `skell-adliblab` is also a supported *planning target*, not an implemented sound port.

## Approval

- Deuce: D/Max was the latest listening favorite; v1.9, v1.7, v1.4 preserved in available forms.
- Alchemist: Hybrid v0.3 was strongly preferred; v0.7 is experimental, with later status not conclusively approved.
- The Deuce D/Max **full-length WAV is not recovered from the provided artifacts**. The exact 15-second lossless A/B export is archived. Do not invent a full-length version.
