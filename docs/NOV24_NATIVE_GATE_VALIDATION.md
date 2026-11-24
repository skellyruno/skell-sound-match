# Native gate reliability and Windows validation - 2026-11-24

Continues Sound Match draft PR #2 from b8f39ed. Shared DSP remains the exact SkellCore PR #47 commit 92b03b753c59583b6b6063228c2d630ef94daf59; no DSP fork, preset identity, automation ID or approved listening sound changed. Skell Preset PR #94 remains experimental and unmerged.

## Fixed root causes

- The previous fixed >0.05 training mask was empty for quiet vocals, forcing an arbitrary -24 dB trim. Calibration now adapts to available signal level; digital silence and non-positive aligned target gain fail explicitly. A quiet +6.0206 dB synthetic target recovers that trim through the actual Windows native fitter.
- Binary identity is checked before/after version and each render. Source/target hashes bind the bytes actually decoded, and changed files are rejected before completing a report or replay.
- Fitting and replay now share exact native output-byte/frame validation, finite sample/metadata checks, zero declared transport latency, parameter bounds and renderer version verification. Truncated/extra output, invalid frame metadata, nonfinite timing, fractional finish settings and invalid blocks are rejected.
- Each candidate and the selected report now expose validation eligibility from peaks, block identity and train/later non-regression. Selection stays strictly training-only: a later section cannot choose a different fallback. Existing v1 report replay remains supported. No later section is labeled independent performance.

## Actual Windows native checks

The exact header, CLI and C++ test input files were checked against all three pinned Git blob IDs. An isolated verification CMake harness built the unchanged C++ with MSVC 19.51, Release, /W4 /WX and /EHsc. Initial configuration failed C1902 (debug database manager mismatch); embedded debug information with the modern CMake debug-format policy fixed that toolchain failure. No warning was disabled. Both executables built; CTest 1/1 passed. This is a native audio CLI build, not a VST3 plugin build.

Native replay on synthetic signals is sample-exact at 44.1/48/96/192 kHz across 1,64,256,511,1024 sample blocks for both finish states. Reported transport latency is zero samples; envelope attack/release is not a claim of instantaneous gate response. Binary/source/render-hash tampering and output overwrite were rejected.

Actual supplied raw-to-original-gate recording: 527,928 frames at 44.1 kHz; first 60% for fitting, remaining section diagnostic. Windows binary identity and private reports are retained locally. The table uses normalized active/quiet sample-domain error, not the older composite objective or percent similarity.

| Native variant | Baseline train | Fitted train | Baseline later | Fitted later | Peak dBTP estimate | Block exact |
|---|---:|---:|---:|---:|---:|---|
| Gate only | 0.028753 | 0.016955 | 0.018176 | 0.012888 | -6.477 | True |
| With finish | 0.027856 | 0.018829 | 0.015885 | 0.011809 | -6.477 | True |

Training-selected variant: gate only. Its FLOAT WAV replay exactly reproduced the recorded native sample hash. Its reported DSP processing time was 0.019235 seconds for 11.97 seconds of audio, excluding process launch and I/O; this is not host CPU certification.

The larger search is exploratory continuation on the same take. It is not independent transfer proof or owner approval. It targets the supplied original gate recording, **not** the exact approved B excerpt. The earlier GNU compiler fit is historical context; compiler-specific binary/sample identities must not be silently interchanged.

## Convolution handoff

Re-verified the actual embedded stereo assets from the private FST containers: Muffle 44.1 kHz / 50,782 frames; Wobbly 48 kHz / 136,241 frames. Private container/sample hashes were recorded without publishing IR data or learned values. Native convolution rendering is still not implemented or claimed by this gate CLI. Preserve the IR sample rates and both channels; a 48 kHz IR cannot simply be replayed as 44.1 kHz. Actual original convolution routing/mix remains unverified.

## Validation scope and next work

- Available local full suite: **302 passed, 1 skipped** with SKELL_NATIVE_GATE_RENDERER set to the compiled Windows executable. Includes real native quiet-fit/FLOAT-WAV replay; the optional Pedalboard runtime is unavailable. A prior 20-test focused native/IR/wet-routing run and wheel build passed.
- Exact-commit GitHub CI is separate and checked after publishing. Without a supplied compiled renderer, the portable native-transport unit tests still run, and the explicit native integration test skips honestly.
- JUCE 8.0.12 is present locally. Full Skell Preset wrapper equivalence, Windows VST3/pluginval, FL Studio, new physical listening and independent paired performances remain unverified. No UI changed; no new screenshot claim.
- All private audio, IRs, native fit parameters and reports stay outside public Git. No new offline-only listening round is presented as production native progress.
- Next: test the actual Preset wrapper against the pinned renderer with matching smoothing, trims, routing, reset, bypass and state; compare the exact owner-approved B artifact separately. Then migrate authorized Muffle/Wobbly convolution into shared native DSP with sample-rate/channel/latency tests. Continue stage-specific Angelic/Zaam/Speakerz wet effects and recover exact Deuce v2.5.
