# Skelly Sound Match — owner round-1 listening feedback + round-2 handoff

**Date:** 2026-11-22. **Status:** USER-REPORTED subjective listening plus CONFIRMED private v1 HTML label mapping. The private HTML and audio recordings MUST NOT be committed to this public repo. **Do not merge unverified DSP into a factory or approve a candidate from this page.**

## Round-1 votes decoded from the actual first HTML

| Round | Owner's statement | Actual version(s) in that private listening session | Development interpretation |
|---|---|---|---|
| Deuce vocal | D beats ?, but hard to distinguish | D = protected D/Max historical; E = original reference; other letters historical 2.3/2.4/finishing-only | Not a decisive preference. Keep D/Max rollback and offline v2.5 target protected. The original A/B was **not** a full current v2.5 native validation. |
| Alchemist vocal | B is close but too bright and misses a certain sound; D almost has it; others okay | B = later native compiled `b2d6c86b`, D = earlier native historical, A = original FL target, C = rejected EQ/dynamics trial | Preserve B's clarity while auditioning D-like body/character; avoid excessive upper-band brightness. The missing character is not proven to be an EQ-only fault. Original factory 43 remains protected. |
| Speakerz main tone | no winner | A = original MAIN, B = fitted EQ + linked dynamics | Do not promote either as a listening winner. |
| Speakerz full effects | A beats B; C sounds best; D sounds good and is perhaps less bright | A = original EVERYTHING; B = dry-only widened; C = original-MAIN-assisted reconstruction; D = dry-only standalone | C is a **reference-assisted research ceiling** and is **not deployable from dry input**; improve D toward C without reading the original processed main at render time. Preserve the clean source-only deployment path. |
| Speakerz stereo | no preference | A = original separated EVERYTHING, B = reconstructed widened | No winner. |
| Hop Out main | B brighter | A = dry-input fitted EQ+dynamics, B = original MAIN DRY stage print | Original high-band character is brighter than the prior trial. Test upper-band balance and sibilance against the stage target without simply raising fullband gain. |
| Hop Out full | no preference | A = original ALL, B = source-only chain missing chorus, C = original-MAIN-assisted | Keep unsolved chorus/time-varying modulation separate. |

No original user preference was assumed for rounds left blank. Favor **controlled same-take, held-out render metrics + equal-loudness owner listening** and then independent performances. The archived Alchemist/Deuce clips represent historical compiled versions, not current exact-head native releases.

## Round-2 private listening page

**12 rounds / 35 clips**: reuses the earlier **7 rounds / 23 FLAC clips** byte-for-byte and with the same random A/B/C lettering; adds four adlibs and a separate gate test. The new five groups:

- **Angelic** — original full WITH delay vs original NO-delay stage vs experimental EQ/dynamics approximation. Delay matching remains incomplete; do not assume stage equivalence.
- **Muffle** — original reference vs static EQ/dynamics trial. Love Philter and other stages not fully recreated.
- **Wobbly** — original reference vs static trial, flagged as dynamics regression and missing moving chorus/flanger/phaser. Do not promote.
- **Zaam** — original reference vs incomplete static trial.
- **Club MIC gate** — original gated print vs fitted gate preview vs raw reference. The gate-reference gain offset is separate from actual gating. Native Skell Preset gate remains draft PR #94 and requires Windows VST3, Quick4 and FL Studio validation.

The private HTML works offline with source-only self-contained FLAC, *but is not stored here*. Keep output generation and owner feedback in a private workspace, with a source SHA256 manifest and review round session ID. The exported JSON's `session_id` must accompany future blind-letter votes; the new v2 feedback format supports `uncertain: true`.

## Work queue ordered by audible evidence

1. **Alchemist:** make protected, reversible B-brightness and D-character trials using actual reference, compare 3–5 kHz and 6–12 kHz and short/medium dynamics, plus independent 4× true-peak safety, without altering Factory 43 or earlier renders.
2. **Speakerz:** isolate which characteristics make the original-main-assisted C sound better; carry only train-derived causal processing into the standalone dry-input D chain. Don't use C's reference audio at render time.
3. **Hop Out:** refine brightness and reconstruct **time-varying chorus** instead of fitting a static FIR; test delay/reverb individually and as part of the complete effects print.
4. **Deuce:** use an actual full offline v2.5 comparison and a genuinely independent same-performance dry-v2.3/original-REC→MAIN trio before porting the missing sustained-air native stage or claiming equivalence.
5. **Adlibs + MIC gate:** work from known FST effect order plus Club same-performance WAVs; restore modulation/filters explicitly and use the gate as the sound-matching front end without modifying previously saved FL Studio state.

**Validation:** UI/HTML code/tests are not a VST3/Quick4/FL Studio test. Owner decisions aren't scientific estimates. Don't merge Sound Match PR #2 into public main unless public archive provenance/licensing and all review gates are separately cleared. Never upload new proprietary FLPs/FSTs/raw vocals/derived audio models to public Git.
