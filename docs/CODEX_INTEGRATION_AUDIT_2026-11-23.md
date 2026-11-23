# Integration audit and nine-target stereo measurements

Continues verified commit d0dd506 on draft PR #2. Owner R5/R6 winners and survivors retain their identities. No new listening preferences were inferred.

## Fixes

- Recheck decoded output loudness and estimated true peak after the full-render safety trim. A peak outside the fitting/holdout windows can otherwise attenuate the delivered comparison enough to invalidate the earlier eligibility result.
- Bind cached renders to SHA-256 of their actual bytes. Tampered, incomplete or invalid cached filenames are blocked for review. An engine revision change invalidates old cache keys.
- Reject nonfinite training/window bounds before optimization.
- Require held-out L/R correlation error within 0.2 alongside the existing width gate. This is a research screening tolerance. The separate phase test prevents a width-only feature improvement from hiding a large channel-correlation discrepancy.
- Record active 200 ms correlation ranges in private signal-only reports, making changing spatial relationships visible alongside global width and mono fold-down measurements.

## Real reference diagnostics

Existing supplied recordings were measured without fitting or replacing a protected winner. Correlation ranges use active 200 ms windows.

| Target | Global L/R correlation | Active-window minimum | Active-window maximum | Next sound task |
|---|---:|---:|---:|---|
| Deuce | 1.000 | 1.000 | 1.000 | Repair reported missing-effects reference before scoring R5 C |
| Alchemist | 1.000 | 1.000 | 1.000 | Retain B/C and resolve REC/main character |
| Speakerz | 0.768 | -0.570 | 0.975 | Match changing wet side path against protected R6 C |
| Hop Out | 0.934 | -0.385 | 0.975 | Separate chorus movement and delay/reverb |
| Angelic | -0.623 | -0.809 | -0.384 | Reconstruct spatial chorus and delay |
| Muffle | -0.399 | -0.657 | -0.051 | Reconstruct modulation and reduce excessive delay |
| Wobbly | -0.510 | -0.868 | 0.375 | Fit changing phase and pitch modulation |
| Zaam | -0.703 | -0.856 | -0.419 | Reconstruct bright tone and multi-tap/spatial routing |
| Club MIC Gate | 1.000 | 1.000 | 1.000 | Preserve three R6 versions and evaluate onsets/noise |

Deuce's available main print remains UNVERIFIED_REPAIR_REQUIRED as a desired full-sound reference. These measurements describe available archive references, not performance of inaccessible protected render binaries. The named Speakerz R6 winner render was not found in the current private workspace search, so no substitute was presented as that winner.

## Verification

Regression checks cover output-trim level rejection, changed cache bytes, NaN windows and changing channel correlation, alongside the existing knob, batch, finishing and signal-report tests. The optional Pedalboard runtime test is skipped in this local environment because that dependency is unavailable. Core SciPy processing and mocked fif-ears signal binding are exercised. No tempo/key benchmark was run.

The Python wheel is built locally. Exact-commit GitHub CI is recorded separately. Native VST3, Quick4, FL Studio and real-browser screenshots remain unverified in this batch. JUCE 8.0.12 was found locally, while this repository's build target remains the offline Python package.

No new challenger was demonstrated to beat the protected winners in this audit. No listening HTML was generated for rejected or unverified contenders. Next development remains actual time-varying spatial processing across the nine-target queue, with frozen source-only replay, private model storage and held-out rejection checks.
