# Round 4: persistent intake and measured source-only trials

Continues draft PR #2 from `9329859f897edbb9ef1f732935cc6ff9f5d0c7e0`.
Historical research, approved sounds, factory programs and automation IDs are unchanged.
No private recording, fitted model, proprietary preset or generated lab belongs in this repository.

## Implemented

- Private eager intake builds on the existing SQLite scanner and SHA-256 cache. Every indexed audio object is materialized and verified immediately, so deleting an upload does not invalidate retained audio. Duplicate provenance remains in the catalog. Repository-contained outputs and recursive self-intake are rejected.
- A private preset register retains references, candidate versions, measurements, listening results and unresolved issues. Immutable register snapshots preserve history across repeated intake.
- Observed owner export names now group under Deuce, Alchemist and the four Club adlibs. Negated effects such as "no chorus" and "no rec" become reference context, not isolated wet targets. Alchemist's no-main-effects print remains REC-printed. Cached inference is versioned, so old database labels refresh after these fixes.
- Listening playback supports synchronized same-position switching by default and optional restart from zero. Native player controls also enforce exclusive playback. Originals remain outside votes; single-candidate rating behavior is preserved. Unknown clip kinds are rejected.
- Added a bounded causal moving-delay stereo hypothesis with train-only model selection, comparison against a train-selected static-delay baseline, separate temporal holdout and explicit rejection status.

## Private real-audio run

72 indexed entries, 65 unique audio objects, 7 duplicate entries; initial scan had no warnings. Audio objects and all fitted coefficients remain private. Alchemist still needs a verified untreated dry print for a true dry-to-main claim. Unnamed recordings from Club are retained for review and never automatically paired to another performance.

The private Round 4 HTML is a new eight-target chapter: **8 rounds / 24 PCM24 FLAC clips**, approximately 18.6 MB. Earlier Round 3 audio/letters and historical champions are untouched. Each target compares EQ-only and EQ-plus-linked-dynamics hypotheses with its original. The adlib hypotheses are explicitly incomplete, not reconstructed creative effects. Levels are matched per round and share a common estimated-peak attenuation; all embedded FLACs passed round-trip and 4x estimated peak checks. Session: `da8710ff2f3b43e8b414325b`.

### Disjoint same-take holdout metrics

Numbers compare the supplied source with the new EQ-plus-dynamics candidate, against the supplied processed print. Spectral errors use seven RMS-matched bands; envelope errors use 200 ms windows. Lower is better. These are not comparisons against protected historical champions, perceptual approval, or independent-performance matching.

| Target | Band MAE source → trial, dB | Envelope MAE source → trial, dB | Decision |
|---|---:|---:|---|
| Deuce | 6.400 → 3.305 | 5.129 → 4.188 | Experimental main-only trial |
| Alchemist | 4.578 → 1.929 | 2.870 → 1.576 | REC-printed-input trial only |
| Speakerz | 2.758 → 1.332 | 2.631 → 1.314 | Main-only trial |
| Hop Out | 5.630 → 1.997 | 2.069 → 0.906 | Main-only trial |
| Angelic Adlib | 6.852 → 2.480 | 5.763 → 4.401 | Incomplete creative chain |
| Muffle Adlib | 7.364 → 3.673 | 4.166 → 2.927 | Incomplete filter/convolution |
| Wobbly Adlib | 4.273 → 2.369 | 2.338 → 2.469 | Envelope regression; not promoted |
| Zaam Adlib | 9.017 → 2.996 | 6.008 → 5.392 | EQ-only band error is lower (2.421); no winner |

The generic Club gate fit worsened band error 0.015 → 0.064 dB and envelope error 0.050 → 0.065 dB. It remains rejected; the earlier near-approved gate is protected.

### Stereo / modulation failures preserved

The supplied Speakerz main and main-plus-47%-separation prints are effectively mono. The full-effects recordings contain side content, so a width multiplier on the main cannot reconstruct the missing effects.

The moving-delay search did **not** pass the predeclared 5% held-out improvement gate in both stereo and side error:

| Stage | Static → moving stereo relative RMS | Static → moving side relative RMS | Status |
|---|---:|---:|---|
| Speakerz full stereo | 0.406590 → 0.406589 | 1.001850 → 1.003023 | REJECTED_ON_HOLDOUT |
| Hop Out chorus | 0.205119 → 0.204691 | 1.019341 → 1.017064 | REJECTED_ON_HOLDOUT |

Both failed models remain private research records and were excluded from listening candidates. Neither simple width nor this short opposing-delay hypothesis explains the missing stereo texture. Next: separate long delay/reverb from modulation and check stage alignment before expanding the modulation model.

## Verification and limits

- Windows Python package wheel build passed. This is an offline Python package, not a native VST3 build.
- Local package tests passed; the restored local source snapshot omits the historical binary archive and its three archive/materialization test files. Exact-head full GitHub CI must independently verify those inherited archive gates.
- Synthetic moving-delay regression verifies frozen-model replay on another random input. Real fixed-main-chain stress renders were finite and peak-guarded on a different source for seven targets. There is **no independently paired processed target**, so sound transfer remains UNVERIFIED. The Deuce self-source stress case is not independent.
- Real browser inspection was attempted. The in-app browser could not reach the local server; the native browser remained minimized after launch/restore. Visual screenshots, actual browser playback and physical audio output remain UNVERIFIED. JavaScript tests use synthetic DOM/audio objects and are not a substitute.
- JUCE 8.0.12 was located locally; this repository has no native plugin target. Quick4, FL Studio, VST3, realtime CPU and latency remain UNVERIFIED. Preserve factories 43/46, 55 production identities and historical D/Max and v2.5.

Keep PR #2 draft. Do not merge or promote any trial based on these numbers alone.
