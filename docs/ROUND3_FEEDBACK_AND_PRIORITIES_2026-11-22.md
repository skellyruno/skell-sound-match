# Listening lab round 3 — original outside voting, owner feedback, and next experiments

**Date:** 2026-11-22. **Repo line:** Sound Match draft PR #2. **Privacy:** the generated listening HTML contains private embedded FLAC and must NEVER be pushed to public Git. This document is safe to commit: it contains no raw vocals, audio-derived private models, or proprietary FST/FLP state.

## Owner's second-round feedback (verbatim meaning, not artificial winners)

| Round | Owner report | Correct research decision |
|---|---|---|
| Deuce / vocal sound | D and F seemed loudest; owner did not confidently choose a winner | D = protected historical D/Max, F = v2.4 Safe; loudness is a confound, NOT approval of D/F or a v2.5 transfer success |
| Alchemist / vocal sound | “idk” | No winner or approval; preserve Factory 43 and earlier B/D character observations |
| Speakerz / main tone + dynamics | Close but missing a little upfront presence and brightness | Investigate restrained upper-mid/air finishing changes with separate held-out evaluation; keep compression and gain as distinct listening criteria |
| Speakerz / full effects | No decision this round | No promotion; reference-main-assisted C remains undeployable, source-only alternatives still experiments |
| Speakerz / stereo separation | “not close” | High-priority failure; do NOT treat previous widened output as validated |
| Hop Out / main tone + dynamics | “getting close” | Continue incremental refit and future independent take review |
| Hop Out / full effects | “i dont know” | No vote; chorus/time-varying FX remain unmatched |
| Angelic / effect character | “incomplete” | Original FST chain known, but delay/creative FX not fully reconstructed |
| Muffle / main sound | “incomplete getting there” | Needs Love Philter/Convolver and gated timing/texture, not only static EQ |
| Wobbly / modulation | “i dont know” | Modulation unresolved and earlier dynamics trial regressed |
| Zaam / main sound | “incomplete so idk” | No approval; creative FX and envelope still absent |
| Club / MIC noise gate | “WINNER B, LOSER C — a works just make it a lil better but its exact” | **B is ORIGINAL gated reference, C is UNGATED raw source, A is reconstructed gate.** Owner says A sounds very close. Never interpret B beating C as A winning; preserve A for a controlled small refinement, not a risky DSP overhaul |

Uncertain answers are explicit **NO DECISION**; original references can no longer be picked as winners or losers.

## Measured Speakerz source-only tone refinement

The earlier privately rendered dry-input Speakerz main trial was compared with the original `speakerz main .wav` on one 23.995-second same-performance recording at 44.1 kHz. On 3–9 s (fit), a bounded grid selected a **+0.9 dB 1.1 kHz peak, Q 0.85**, followed by **+1.95 dB high shelf around 8.2 kHz**. Evaluation was on disjoint 12–20 s. Seven RMS-matched spectral bands: 120–300, 300–800, 800–1500, 1500–2800, 2800–5000, 5000–8000, 8000–14000 Hz.

| Same-take seven-band spectral MAE | Baseline (dB) | Finishing trial (dB) |
|---|---:|---:|
| Fit 3–9 s | 1.574 | 1.336 |
| Holdout 12–20 s | 1.374 | 1.181 |

The entire experimental render was capped against an approximate **4× interpolated −1.2 dBTP ceiling** using −0.206 dB output trim. This is not certified true-peak testing. Source-to-target sample alignment is not perfect (a short correlation check indicated about −84 samples and moderate inverted correlation); the metric is band-energy-only, **not** waveform null, exact sound matching, or independent-take proof. This finishing EQ is appended after the existing dry-source EQ/dynamics reconstruction; it is not a replacement for the original FL processing and has not passed listening approval.

The single private Round 3 HTML named `SKELLY_SOUND_MATCH_LISTENING_LAB_ROUND3_2026-11-22.html` includes **13 rounds / 38 FLAC clips**: all first 12 prior rounds have identical encoded audio, letter order and identities, plus one new Speakerz presence comparison. The new round uses 12–20 s at normalized loudness. The privately generated HTML, trial FLACs, and reports remain **outside Git**.

## Listening lab workflow correction

- The audio labeled `kind=reference` or `kind=reference-stage` appears only in a green **ORIGINAL / SOURCE REFERENCES** area; it never appears in candidate vote choices.
- When just one candidate exists, there is no forced winner/loser; use a **1–5 similarity score**, issue tags, uncertain option and notes.
- When 2+ candidates exist, original/reference clips remain separate, and only candidate letters are eligible for best/worst votes. Switching reference/candidate versions starts playback from 0, and only one round plays at once.
- Persistent votes move from the prior v2 storage namespace to v3, so a previous selection of an **original** cannot silently reappear as a candidate vote. Clip mappings and the lab session fingerprint still preserve prior audio identity for audit.
- New command `--remix` rebuilds the interface of a trusted private existing HTML, preserving all FLAC bytes and randomized letters without re-encoding. It refuses to overwrite existing outputs.

## Release gates and priorities

1. **Speakerz stereo separation:** measured reference-to-source-only width mismatch is user-reported significant; prioritize genuine side/mid or source-spatial reconstruction rather than simply turning up stereo width. Recheck sibilance/correlation and mono compatibility.
2. **Adlibs:** reconstruct moving modulation (Wobbly), Angelic effect tail, Muffle filter/convolution, and Zaam creative FX; use original chain maps and same-take WAVs. Previous failed fits remain failed.
3. **Club gate:** keep owner-near-approved A candidate and legacy-safe native gate draft. Only small, reversible gating/onset and release improvements with same-take audio and real VST3/host checks. Do not blindly add +1.65 dB reference makeup gain to every preset.
4. **Alchemist/Deuce:** preserve historical champions and native factory IDs. Deuce D/F being perceived louder is not objective v2.5 transfer approval; provide proper loudness-matched new native audition on an independent source. Alchemist trial character/brightness still open.
5. Keep public Sound Match PR #2 **draft**; no private user WAV/FLAC/HTML/NPZ/FST/FLP should be committed; no native Skell Preset parameters, saved state, factory index, or production merge changed by this offline listening UX update.
