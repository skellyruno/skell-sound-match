# R59 — Editable native causal phase correction

Owner requested numerical convergence before listening tests. No listening lab, no separate installer, no production approval. Preserve all historical approvals and stable artist IDs.

Skell Preset draft PR #90 commit 10ab8de18c7bbd5f8bbe4addae5731c86e02887a adds native module ID 45 (Skelly Phase), frequency, Q, polarity and trim. Existing IDs and choice ranges unchanged, 16 independent fxExt12 flags appended. Older host snapshots without the flags default off. Phase-stage presets require a build with module 45; earlier plugin versions cannot load them. Do not deploy to an older binary. All 11 phase source/test blobs at that commit match the local tested files. Local render used verified recovered 6a4c7ff source plus the tested phase change, before newer browser/hosting fixes; existing cached artwork resources retained. No claim of full exact-head Windows certification.

## Real native matching

33 aligned paired source hashes verified, 33 R58 baseline renders bit-identical before changes at 44.1 kHz. Protected gate unchanged. 1,132 actual native evaluations (includes baseline, fitting, prefix stress, confirmation). Fit one to three causal all-pass stages from first 45%; rank candidate on middle 25% with training, phase/tone/envelope/stereo and peak guards; final 30% retrospective veto. In crowded racks tested ablation. Re-tested headroom-vetoed and earlier experimental seeds with more conservative trim/phase settings, choosing by middle region. No independent-take proof, no target samples in the replay path.

| Pair | R58 | R59 |
|---|---:|---:|
| Free Main | 5.024 | 4.164 |
| Nobody Main | 3.256 | 2.906 |
| UP Full | 3.800 | 3.535 |
| Wait Main | 5.038 | 4.292 |
| Plan Main | 4.902 | 4.638 |
| Plan Full | 4.275 | 2.683 |
| Overtime Main | 3.644 | 2.131 |
| Overtime Full | 4.071 | 3.161 |
| Speakerz Main | 3.547 | 3.307 |
| Speakerz Full | 3.983 | 3.433 |
| Hop Main | 3.851 | 2.942 |
| Hop Full | 4.774 | 3.919 |
| Club Muffle | 5.413 | 5.189 |

13 revised pairs, 20 retained. Mean 44.1k 5.313649 -> 5.032524; mean 48k 5.334026 -> 5.052244. Nominal estimated true peak worst -1.2762/-1.0211 dBTP; full-recording +6 dB stress at 48k/64 samples 0/33 overloads, worst -0.1257 dBTP (revised pairs freshly tested; retained R58 results for unchanged packages). No reported latency increase. Uh Huh Base candidate 9.154 from 14.990 failed waveform/components and peak/stress; not accepted. Uh Huh Full and several adlib chains remain unchanged. Do not claim exact formant/modulation reproduction. Target below 1.5 remains unmet for all but the protected gate.

## Verification

Generation 59: 35 stable artist entries, 138 immutable revisions, approved art and historical listening metadata unchanged. Native embedded bank install, byte identity, idempotence, upgrade, history, downgrade, local edit, collision and malformed bank tests passed. Local Linux VST3 and editor built. Portable C++ phase test 100 configurations at 32/44.1/48/96/192 kHz, max energy error 0.000361 dB, polarity null 0, channel isolation and bounded parameter automation. Actual processor smoke: appended flags, zero latency, native package and state roundtrip, missing legacy flags clear correctly. Real recovered-source Linux UI interaction smoke passed; initial Quick4 182 scenes, zero failures. Python catalog boundary + previous tests: 19 passed locally. Public code contains no private bank, audio, artwork or fitted settings. Previous Windows branch CI had 65/66 passed with one browser UI interaction failure; newer browser/hosting fixes were preserved during commit. New Windows/FL Studio and independent performance validation pending. Peak controls are not proof of aliasing-free overload behavior.
