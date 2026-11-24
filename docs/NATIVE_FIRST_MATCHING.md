# Native-first Sound Match migration

Owner decision: do not create a separate DSP repo. SkellCore is the canonical implementation, Sound Match orchestrates optimization and listening, and plugins consume pinned shared DSP. Keep all historical listening winners, private IRs and original references intact. Existing offline approvals are not automatically native approvals.

## Phase 1: Club Gate
Core draft PR #47 commit 92b03b753c59583b6b6063228c2d630ef94daf59 contains shared ClubGate.h, CLI and portable tests. Skell Preset draft PR #94 commit a7f5edca521aeb87cde256d4520f488d4587d49a uses the exact header (SHA256 checked), with local classes aliased and shared clubGateGain invoked. Other pinned dependencies and factory parameters preserved. Experimental finish remains OFF by default. Local JUCE fetch failed DNS; full wrapper equivalence and Windows CI remain unverified.

Build renderer from the pinned core checkout:
    cmake -S SkellCore -B build-native -DSKELLCORE_BUILD_NATIVE_MATCH_RENDERER=ON -DSKELLCORE_BUILD_TESTS=ON
    cmake --build build-native --config Release
Then invoke from Sound Match:
    python tools/fit_native_gate.py /path/to/SkellCoreClubGateRender raw.wav gate.wav report.json --maxiter 8
    python tools/replay_native_gate.py /path/to/SkellCoreClubGateRender raw.wav report.json candidate.wav

The fitter sends float32 source only to C++; scores the paired reference in Python. Selection uses first 60% only; later part of the same take is diagnostic, not independent transfer. Records expected engine revision (operator must build the pinned source), exact binary/source/target/render hashes, parameters, level trim, block size, rate and score. Replay rejects mismatched binary, source, output fingerprint, unsafe peak and overwrite. A different compiler binary requires new verified evidence, not silently substituting it. Output trim is standalone calibration, not evidence that an entire VST chain matches.

Local GNU 14.2 targeted isolated CMake build with -Wall -Wextra -Werror and 1/1 CTest passed at four rates. The three C++ Git blobs were checked against local compiled inputs. 527928 real Club frames, 44.1 kHz, 316756 fit frames. Native gate baseline train/later 0.028753/0.018176, fit 0.016955/0.012888; finish baseline 0.027856/0.015885, fit 0.018829/0.011809. First variant selected on training only; both preserved. Score is active/quiet normalized sample-domain error, NOT previous composite score or percent accuracy. Estimated peak -6.477 dBTP. Both variants exact across 1,64,256,511,1024 sample blocks. Repeated search reproduced render hashes. Replay produced exact selected sample hash; tampered binary/source/render hashes and overwrite were rejected locally. New owner audition and actual full VST3 wrapper comparison pending. Local timing ~4.5ms / ~10ms for 11.97s audio, excludes host and I/O, not DAW CPU certification. Private report, audio, and fitted values not published.

## Promotion contract
1. Core shared code and tests, immutable revision.
2. Candidate render from that core, exact recipe and identity, held-out scoring and independent source where available.
3. Wrapper comparison with same input, reset state, parameters, gain, bypass/mix and full routing; test sample rate, block schedules, automation, PDC and recall. Do not substitute source-level identity for wrapper parity.
4. Owner listening decision using native candidate; only then promote approved config without altering legacy factory IDs.
5. Windows VST3/pluginval, FL Studio and CPU/latency gates.

Next migrate Wobbly/Muffle convolution and modulation using authorized IR hashes, then stage-specific Angelic/Zaam/Speakerz delay, and native main-chain EQ/dynamics. Deuce v2.5 remains protected; recover exact historic recreation before comparison. No more new offline-only candidates offered as production-ready. No automatic factory replacement or public private audio.
