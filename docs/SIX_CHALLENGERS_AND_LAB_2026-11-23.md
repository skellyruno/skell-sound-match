# Six fresh challengers and restored nine-target lab - 2026-11-23

Continues existing draft PR #2 and protected owner decisions. No native preset, automation ID, FST/FLP or approved sound was changed. Private WAVs, learned models, source manifests and embedded-audio HTML remain outside public Git.

## Root causes and changes

- Fixed dynamics scoring near digital silence. Applying loudness gain to extracted envelope floors could reward a static level change. Both envelopes now share a reference-relative floor; gain-only silence regression tests pass. Batch cache revision v3 prevents stale decisions from being reused. Earlier numeric tables are historical and are not directly comparable to the corrected metric.
- Added stereo-linked peak compression, preserving inter-channel ratios and zero-lookahead behavior. It is a nonlinear offline experiment, not an antialiased native limiter; emitted output is separately true-peak estimated and safety-trimmed.
- Added deterministic causal diffuse tails. Angelic/Zaam moving-delay trials initially failed additional tail sections. The composed diffuse-tail versions pass the existing guards in both measured sections. They do not claim original plugin settings or exact delay topology.
- Diagnosed Hop Out finite-repeat truncation: a four-repeat echo fit missed the long original decay. Extended the train-derived tap decay geometrically, retaining the measured cross-channel tap shape. Its additional tail envelope error fell from 12.189 to 1.354 dB against the starting diagnostic. Original MAIN, DEL and REV stages were investigated separately; no reference samples are mixed into the render.

## Measured results

Scores below are internal weighted errors, lower is better, not percentages of perceptual accuracy. The primary interval is the existing audition section. Additional intervals test frozen renders; once inspected, they are repeated research diagnostics rather than pristine new holdouts. Independent paired performances are still unavailable.

| Target | Primary baseline | New score | Additional section | Disposition |
|---|---:|---:|---|---|
| Deuce | 7.278 | 7.216 | Not qualified | Reference repair required |
| Alchemist | 1.590 | 1.442 | 1.478 to 1.353; pass | Experimental two-section pass |
| Speakerz | 3.281 | 1.341 | Not qualified | Rejected: envelope mismatch |
| Hop Out | 1.971 | 1.272 | 15.063 to 1.754; pass | Experimental two-section pass |
| Angelic Adlib | 4.172 | 2.208 | 4.376 to 3.052; pass | Experimental two-section pass |
| Muffle Adlib | 2.762 | 1.529 | 2.612 to 2.433; pass | Experimental two-section pass |
| Wobbly Adlib | 6.225 | 4.383 | Not qualified | Rejected: envelope mismatch |
| Zaam Adlib | 5.993 | 2.274 | 5.614 to 3.672; pass | Experimental two-section pass |
| Club MIC Gate | 0.203 | 0.092 | 0.589 to 0.368; pass | Experimental two-section pass |

Exact new candidate identities: `alchemist-nov23c`, `angelic_adlib-nov23d-tail`, `muffle_adlib-nov23b`, `zaam_adlib-nov23d-tail`, `hop_out-nov23g-geometric-echo`, `club_mic_gate-nov23c`. No historical candidate is relabeled as new. Muffle/Alchemist/Hop Out/Zaam are compared with recovered exact R5 survivors from session `04ef2153d69dda2e7051355a`. Angelic retains two explicitly unresolved historical anchors; its third historical attempt remains archived, with no owner elimination inferred. Club gate is a standalone similarity trial, not a replacement for unresolved R6 A/B/C.

## Private HTML and playback

One current self-contained lab contains all nine target pages and 30 embedded FLAC clips. Alchemist, Angelic, Muffle, Zaam and Hop Out have two historical anchors/survivors plus one fresh contender. Wobbly retains all three unresolved R5 attempts; its new failed trial is excluded. Gate has one fresh trial and a 1-5 similarity rating. Deuce ranking is disabled pending its complete-effects reference repair. Speakerz exposes only its exact corresponding original full-effects +47% stereo print: protected R6 C/B audio is not present locally and is not substituted with R5 audio. Both R6 files were found but materialization failed at DNS.

The original has its own unlettered button. A single audio transport resets on every version/preset switch; same-version clicks pause/resume. New session hashes bind audio/version mappings. Tie clears a prior elimination; blocked groups cannot vote. Candidate identities stay hidden until a submission, and exports carry identity/audio hashes, ratings, eligibility and prior session identity. Prior HTML and feedback are retained separately.

All reference crops were numerically compared against their actual supplied prints at the declared offsets, allowing only loudness scaling and 24-bit quantization. Maximum identity residual was 3.45e-8 RMS. All 30 encoded clips round-trip decode at 44.1 kHz, with exact per-group frame counts and LUFS spread under 0.15 dB; estimated 4x true peaks are at or below -1.5 dBTP. These checks establish mapping/format/level, not complete perceptual accuracy or known original plugin routing.

## Verification and limits

- Local available package suite: **262 passed, 1 skipped** (optional Pedalboard runtime unavailable). Wheel build passed.
- Synthetic regression coverage includes envelope gain invariance around silence, causal/deterministic wet tails, source-only geometric echo continuation, stereo-linked peak behavior, exact mapping/session changes, switches/reset/pause/resume, tie clearing, blocked voting, single-candidate rating and identity export.
- The actual final HTML script passed simulated-DOM checks over all nine groups, all 30 clips and all seven reviewable groups. This is not a browser audio device test.
- In-app browser navigation to a listening local server again failed with connection timeout. Real browser playback, desktop/mobile screenshots and physical listening remain **UNVERIFIED**. Responsive CSS is implemented but not screenshot-approved.
- JUCE 8.0.12 dependency is present locally. This repository is offline Python; no Windows VST3, Quick4 editor, native CPU/latency or FL Studio validation was performed.
- Independent paired performances and audible artifact assessment remain open. Do not promote these candidates automatically. Preserve protected winners and keep PR #2 draft. Tempo/key benchmarking stays deferred.

## Next work

1. Recover protected Speakerz R6 C/B and Club gate R6 renders without substituting older previews; compare actual stereo modulation against the corresponding +47% original.
2. Repair Deuce complete-effects original identity/routing before any new full-effects ranking.
3. Reconstruct Wobbly time-varying vibrato/flanger/phaser; envelope error remains above the absolute guard despite a lower aggregate score.
4. Inspect actual browser desktop/mobile layouts and device playback when local-page access works; then obtain owner listening decisions without treating measured checks as approval.
5. Add an independent paired performance, freeze each complete chain and test transfer. Improve exact chorus/delay/reverb behavior and transient/aliasing artifacts before any native port.
