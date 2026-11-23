# R6 owner feedback and R7 optional fif-ears feature audit — 2026-11-23

## Why the previous listening HTML had only two battles

It was a *focused* Club Gate + Speakerz experiment, not a replacement for the nine-target battle queue. The latest owner-approved R5 private candidate files cannot all be accessed here. We must not create duplicates from earlier R3 audio and pretend those are R5 contenders. Retain the nine-target queue; next listening HTML should bundle several real new challengers rather than numerous tiny files.

## New owner decisions from SKELLY_R6_BATTLE_PICKS.json

- **Speakerz full-effects/stereo**: winner **C** = `speakerz-r6-full`; eliminated **A** = `speakerz-old-source`; surviving **B** = `speakerz-r6-gentle`. Freeze C. B survives.
- **Club MIC Gate**: **no winner/no elimination**. R6 A `club-r6-new`, B `club-r4-old`, C `club-r6-guard` all survive. Owner heard slight gated noise at the beginning, some also present in original. Investigate quiet-region onset and tail with localized audio, not global average EQ.

These choices are relative to the correctly paired original; no native preset or previous R5 winner was overwritten.

## fif-ears integration

The owner supplied `fif-ears-master.zip` (Apache-2.0). Bundled tests were **21/21 passing locally**. The optional, public-code-only `skell_sound_match.wav_only.ears_gap_audit` **reads signal and expression features only**, from externally produced PRIVATE fif-ears report JSON. No fif-ears library is copied into this repository. The report comparison refuses mismatched declared takes, output stages, duration, sample rates, missing required layers, or unverified processed original references. Seven synthetic tests passed locally; separate actual private R6/R7 reports successfully compared seven pairs.

Minimal PRIVATE manifest:

```json
{"schema":"skelly.fif-ears-pair-audit.v1","pairs":[{"group_id":"vocal",
  "candidate_id":"trial-version-id","original_report":"private-original-report.json",
  "candidate_report":"private-candidate-report.json",
  "reference_take":"same-verified-take","candidate_take":"same-verified-take",
  "reference_stage":"full_effects","candidate_stage":"full_effects",
  "reference_verified":true}]}
```

Run only in the private working directory:

```sh
python -m skell_sound_match.wav_only.ears_gap_audit private-pairs.json --output private-feature-gaps.json
```

No automatic listener winner from a score. Tempo/key-versus-Skell-Key benchmark explicitly **DEFERRED** at owner's request, no Skell Key code or state changed.

## Quantified R6 → experimental R7 Speakerz direction

R6 original full/stereo versus candidates using **fif-ears measured feature differences**:

| version | brightness below original | side/mid relative width dB |
|---|---:|---:|
| older source-only A, eliminated | 34.31% | -6.43 |
| R6 gentle B, survivor | 27.62% | +0.66 |
| R6 full C, owner-preferred | 24.58% | +0.68 |
| R7 experimental high-shelf trial | 14.95% | +0.65 |

A bounded additional high-frequency finishing pass on R6 C reduced a private same-take seven-band RMS-matched held-out MAE from **0.763 dB** to **0.565 dB** (train selection on 0–4.4 s, heldout 4.4–10 s). New R7 4x estimated true peak about -1.84 dBTP. **This does NOT establish better sound, independent-take transfer, or missing time-varying FX accuracy**. Keep old C untouched and use the new R7 trial as a challenger only after frozen R6 B and C are available. Keep fitted audio and private parameters out of public Git.

## Historical archive triage — not newest R5

Ten historical Round 3 groups, 11 reference/candidate comparisons were checked. Legacy static approximations measured brightness below their respective originals: Speakerz full ~35%, Hop Out full ~26%, Angelic ~35%, Wobbly ~21%, Zaam ~28%; Muffle was ~25% brighter and still lacked stereo content. Historical results show where to investigate but cannot be used to eliminate the more recent protected R5 owners' survivors. Deuce is still on hold because the original was reported missing effects.

## Hard limits and next steps

- Club gate: time-local noise at the beginning, noise onset and release; global `fif-ears` metrics are near-identical across R6 candidates and insufficient.
- Speakerz: target brightness, dynamics and **time-varying stereo texture**, not side/mid amplitude alone.
- Continue Hop Out chorus and Muffle/Angelic/Wobbly/Zaam moving effects. Respect protected Alchemist/Deuce identities.
- Do not run Skell Key tempo or key comparison until the owner asks.
- User private source audio, original FL Studio projects, private reports, experiment filters and audio-embedded HTML were NOT published. No Windows VST3 or independent paired-vocal match claim. The current branch remains a **draft PR**.
