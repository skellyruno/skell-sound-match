# Sound Match: bounded knob-search research + fif-ears diagnostics (2026-11-23)

## Source review and licensing

- Owner-supplied `vox_cloner-master.zip` was inspected: 15 ZIP entries, integrity OK. It is a **mono 44.1 kHz** 32-knob Pedalboard + CMA-ES research optimizer, with ~61 statistical tone/dynamics features. It compares the **first eight seconds of the input** against **features of the full target** and has no independent same-take holdout approval gate. Its archive contains no `LICENSE`; **no source code was copied** into the public Sound Match repository. The replacement implementation is original, limited, stereo-aware, and uses only the existing SciPy dependency. Optional effects use separately installed `pedalboard`, not the copied source.
- `fif-ears-master.zip`: 75 entries, integrity OK, Apache-2.0; 21 bundled tests passed locally. Sound Match already has `ears_gap_audit.py` for independently generated signal/expression report comparisons. The new knob runner optionally calls the **fif-ears signal layer only**, including stereo width, RMS, spectral centroid and clipping. **No tempo or key analysis was run**, as explicitly deferred by the owner. The other tool's code is not vendored.

## Implemented public code

- `vocal_knob_search.py`: offline deterministic bounded EQ + existing stereo finishing, optional Pedalboard compressor/chorus/delay/reverb chain, source-only rendering, local gain calibration on the **TRAIN section**, scored on a **non-overlapping HOLDOUT section** with no model selection on heldout. No reference audio is injected into a candidate. Saves private experiment WAV and detailed report, refuses overwrites, stores exact input hashes and stage/take metadata.
- Independent accept/reject guards: objective reduction, absolute error reduction, envelope no-regression, broad spectral error, true peak, **held-out level within 2 dB**, **stereo ratio within 6 dB**, band MAE within 4.5 dB, envelope MAE within 5 dB. These are internal research thresholds, not evidence of identical sound or an approved plugin. Rejected renders are diagnostics only and **must not be included as competing winners**.
- `stereo_phase_profile` quantifies L/R correlation, side/mid ratio, mono-fold-down loss and whether an original is strongly antiphase. Stereo width increase alone is not sufficient; time-varying/phase-warped effects are still needed.
- `vocal_knob_batch.py`: 1–250 explicitly verified same-take/source/target jobs per manifest, stable content-addressed cache by inputs/settings/revision, duplicate IDs rejected, no re-render of unchanged jobs, rejected or missing pair recorded as BLOCKED rather than cross-pairing audio silently. The manifest, index, private models and rendered audio remain outside Git.
- `tests/test_vocal_knob_search.py` and `tests/test_vocal_knob_batch.py`: 16 local regression tests passed (synthetic render, deterministic search, real optional Pedalboard runtime, train-only output gain, stereo/mono behavior, unknown pairing rejection, no false approval, cache and changed-hash invalidation, input and overwrite guards, and fif-ears signal-only binding).

## Real private-same-take research, NOT published

Source files: older standalone Speakerz and Hop Out source-only reconstructions paired against their full-effects prints; Club gated voice paired with the four supplied adlib prints. The R5/R6 protected winner binaries were **not used** and are **not available for direct cross-battle here**. Equal-length 44.1 kHz stereo WAV/FLAC were used; stage alignment and take match were declared from archive provenance. Small training windows and separate later validation windows were used. Search budgets were 32–55 evaluations. These are tiny same-take tests, **not independent performance verification**.

| Older diagnostic target | Pre-fit holdout weighted score | New fit holdout score | New candidate status |
|---|---:|---:|---|
| Speakerz full/stereo from standalone main | 5.075 | 4.977 | REJECTED: missing stereo phase/width, too small improvement on train |
| Hop Out full-effects from standalone main | 13.488 | 13.717 | REJECTED: heldout regression and missing effect character |
| Muffle gated-to-adlib | 13.303 | 10.873 | REJECTED: missing strong antiphase stereo, tone and envelope |
| Angelic gated-to-no-delay adlib | 13.088 | 9.784 | REJECTED: missing strong antiphase stereo, tone and envelope |
| Wobbly gated-to-adlib | 12.453 | 11.094 | REJECTED: missing strong antiphase stereo, moving pitch/Panagement character |
| Zaam gated-to-adlib | 15.644 | 11.979 | REJECTED: missing strong antiphase stereo, tone and delays |

These scores are a **weighted internal feature objective** with loudness matching for spectral/envelope comparison, not a percentage of perceptual accuracy. The winning tests' actual output is separately calibrated to training-target level; the listed scores cannot certify similarity. In early exploratory tests, four adlibs appeared to pass when only the combined loss mattered. That **false-positive was fixed** by requiring absolute level, spectral, stereo and dynamics checks. No test audio or listening rounds from these rejected experiments are promoted.

## Stereo phase findings (private Club WAVs)

| Source/reference | Left/right correlation | Side/mid ratio |
|---|---:|---:|
| Club gated input | +1.000 | dual-mono |
| Original Muffle adlib | −0.399 | +3.66 dB |
| Original Angelic adlib (no delay) | −0.623 | +6.33 dB |
| Original Wobbly adlib | −0.510 | +4.84 dB |
| Original Zaam adlib | −0.703 | +7.59 dB |

This is a strong **measured spatial requirement**. Mono input plus ordinary stereo width is fundamentally insufficient. Investigate actual chorus/phaser/Panagement and stereo phase routing with independent validation; do not solve it by just inverting one channel or risk mono-cancellation without checking.

## How to run with private audio (EXAMPLE only)

Install offline research dependency when using the FX mode: `pip install '.[knob_fx]'`. For optional fif-ears signal report, separately install the user's Apache-2.0 fif-ears package in the **private environment**; do not vendor it and do not run its complete tempo/key report.

```powershell
python -m skell_sound_match.wav_only.vocal_knob_search C:\SkellyPrivate\speakerz_standalone.wav C:\SkellyPrivate\speakerz_full.wav C:\SkellyPrivate\trials\speakerz1 --take-id speakerz --source-stage standalone-main --target-stage full-effects --train 1 3.8 --holdout 11 14 --budget 55 --fif-signal
python -m skell_sound_match.wav_only.vocal_knob_batch C:\SkellyPrivate\verified_pairs.json C:\SkellyPrivate\knob_cache
```

Example manifest (private, not for Git):

```json
{
  "schema": "skelly.vocal-knob-batch.v1",
  "pairs": [{
    "id": "speakerz-v1", "source": "speakerz_standalone.wav",
    "reference": "speakerz_full.wav", "same_take": true, "take_id": "speakerz",
    "source_stage": "standalone-main", "target_stage": "full-effects",
    "train": [1.0, 3.8], "holdout": [11.0, 14.0],
    "budget": 55, "seed": 17, "effects": false, "fif_signal": true
  }]
}
```

## Next high-value tasks

1. Stereo **phase and time-varying modulation reconstruction** for Angelic/Wobbly/Zaam/Muffle. Preserve current R5 winners and defer promotion until accurate original-versus-candidate stereo phase/tails are recreated; evaluate mono fold-down safety.
2. Upgrade Speakerz full-effects stage by reconstructing actual wet side channel and same-stage time effects, not simply widening the mono main print. Preserve owner R6 winner C.
3. Keep Hop Out chorus/delay/reverb stage-separated and add transient/noise protection; current constrained EQ optimizer failed heldout, so do not promote.
4. Deuce original was reported as missing effects: repair full original-stage pairing before further winner selection. Preserve protected offline v2.5 and D/Max. Alchemist needs prior brightness/character balancing with stable Factory 43.
5. Club noise gate user's onset-noise complaint remains unaddressed by this optimizer; retain R5/R6 gate states and compare actual open/close/hold with quiet consonants before native changes.
6. Integrate the new verification and cached batch runs with the existing battle-royale HTML **only for experiments that pass**, with originals unlettered. Do not fill all nine battles with older archived versions or failing trials just to have three candidates.
7. Independent paired performances, actual Quick4/FL Studio/Windows VST3 remain UNVERIFIED for this offline analysis. Tempo/key comparison against Skell Key remains explicitly DEFERRED.

**Verification scope:** This report records local synthetic tests and private real-audio experiments. Windows CI at the new commit must be checked separately. This offline research doesn't implement a native VST3 or prove audible improvement.
