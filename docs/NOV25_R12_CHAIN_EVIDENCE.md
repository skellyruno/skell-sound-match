# R12 — native chain and evidence gates, 2026-11-25

Parent R11 `608de5fcffb28fd24ab3397798a1aa1ac3641239`, exact-head CI 45559937118 success. R11 archive and nested R10/Bank archives passed ZIP integrity. Continued existing draft PR; no owner listening votes or preset promotions.

## Recovered native chain
The saved Muffle Convolver slot-6 state was verified by SHA-256 and rendered through original recovered kernel code (R11 host-adapted version). Reeverb 2 runs afterwards, matching the documented slot-8 *order*, but the original saved Reeverb2 settings are not available; experimental settings are not asserted to be reconstructed FL state. Offline C++20 shared library with the recovered engines and a test-only Effects/zlib shim built with strict warnings, no FMA contraction. Real Muffle dry audio: at 44.1/48/96/192 kHz the Convolver→Reeverb2 chain produced **zero difference** across tested 127/512/1024 host blocks (input ~0.8 s per rate). No Windows/JUCE/FL Studio host or broad CPU profiling. WavPack still unavailable.

## Muffle matching — experimental, not independent
R9 retained Muffle baseline 4.9891 training / 7.5495 later error. Searched 72 full serial settings, then 576 training-side parallel-send combinations; 8 + 12 later-section checks. Serial processing lowered some later scores but regressed training dynamics/stereo. A low-level parallel chain passed previously defined experimental gates: training 4.9536; later 7.4730; estimated 4x true peak -10.04 dBTP, but tiny later improvement .0765. Repeated inspection of the later segment invalidates its use as untouched validation. Source and reference are **different performances**, with different durations. No owner listening result or protected preset changes; the candidate is listening-only.

## Provenance audit and safety
All nine R1 dry/reference pairs checked at 44.1 kHz using a 40-ms frame activity threshold anchored to each training section. 8/9 pairs eligible. Deuce reference's later partition has zero active frames; quarantine old Deuce full-effects later scores. R12 adds `chain_evidence.py` with explicit ordered-slot/state-hash validation, finite metric gates, peak gate and separate flags for independent performance, untouched holdout, verified stage and owner listening approval. 18 new local regression tests passed. This code does not alter presets or automation IDs.

## Listening lab
Private HTML compares original processed reference separately from R9 baseline A and R12 challenger B. Same-source A/B, original different performance, common preview active RMS -20 dBFS and estimated 4x true peak below -2 dBTP; no reference voting. Actual Chromium desktop/mobile snapshots inspected, mobile overflow absent; buttons, reset on switch, stop, feedback JSON download passed. Fixed timer decimal display and misleading approval phrasing, recaptured screenshots.

Private R12 checkpoint retains R11, supplied native code, saved state, evidence and metrics, tests, HTML, full lossless audio, and SHA-256 integrity. No private source/audio/fitted recipe in public Git. JUCE VST3, native host and fresh independent source/target recordings remain unverified. Keep draft; no merge.
