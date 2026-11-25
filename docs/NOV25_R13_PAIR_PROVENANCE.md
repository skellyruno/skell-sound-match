# R13 — source/reference identity gate and batch intake (2026-11-25)

**Continuity:** Draft Sound Match PR #2, branch `feature/deuce-v25-listening-approved-20261115`. Parent R12 `26e28d13696977407172c5607e67619ecab14e57`, exact-head CI run `45566352008` succeeded. R12 ZIP 65 entries CRC passed. No previous candidate, approval, private audio or automation identity changed.

## Root-cause fix

The R12 `evaluate_evidence` API permitted an `eligible_for_preset_promotion` return with manually asserted stage/independent/holdout/listening flags even though it had **no required source/reference take identity**. R13 adds an explicit immutable `PairProvenance` gate requiring take IDs, file SHA-256s, sample rates, matching processing stage, verified offsets, and manifest/session provenance before *exact same-take* reconstruction can be promoted. Missing provenance now defaults to promotion rejection. A cross-performance experimental metric pass can still be reported, separately. This is an intentional stricter safety behavior; existing positive promotion-gate tests were updated to supply trusted synthetic metadata, while negative tests cover all omitted/mismatched fields.

`audio_alignment.py` supplies an amplitude-invariant six-band log-spectral lag correlation diagnostic over up to ±1 s. Scores **never certify identity**, even when identical audio returns ~1.0. `pair_intake.py` audits local manifests, checks expected hashes, signal activity and alignment, and reports *pair-provenance eligibility separately from release/preset promotion* (the intake alone always reports no promotion approval). Manifest fields must not be inferred from matching scores or filenames. Caller supplies source/reference/candidate file paths, verified take IDs, stage, offsets, export checksums and provenance only when actually documented.

## Real recovered corpus check

The R12 9-source/9-reference corpus was audited. All nine had different file hashes and different durations; **none** has session-verified same-take metadata. Eight references have sufficient training and later activity; Deuce reference fails the later-section activity gate. Source/original log-spectral similarity ranges 0.242–0.391, compared with 0.541–0.988 on five recovered known source-generated candidate examples; similarity scores are *not* percentages or proof of different takes, but reinforce the need to correct the original pairing. The new batch intake reported `0/9` verified provenance and `0/9` eligible for promotion. This is a truth-in-evidence change, not a new sonic improvement.

## Tests, user review and remaining blockers

48 Linux local pytest assertions passed (`tests/test_chain_evidence.py`, `test_audio_alignment.py`, `test_pair_intake.py`), including variable sample rates 44.1/48/96/192 kHz, known delayed synthetic audio, missing metadata, hash tampering, silence and negative promotion cases. Browser checks with real `/usr/bin/chromium` passed on desktop 1360×860 and mobile 390×844: 9 selectable targets, 4 source-aligned candidate examples, original outside candidate voting, player reset on target/candidate switch, verdict/stage/note preservation, JSON feedback export and no horizontal overflow. Inspected both captures, fixed mobile nav selected-item visibility and re-inspected. Screenshots are private lab UI, not VST plugin UI.

Private R13 checkpoint contains the full original R12 ZIP, the real R13 audit output and private audio review lab, source/tests, screenshots and SHA-256. No private audio, proprietary DSP, fitted controls or HTML go into GitHub. Windows VST3, FL Studio exact-state parity, genuinely untouched validation takes, official session take metadata and actual owner listening approval remain unverified. Do not merge.

## Repro

`python -m pytest -q tests/test_chain_evidence.py tests/test_audio_alignment.py tests/test_pair_intake.py`

`python -m skell_sound_match.pair_intake /path/to/manifest.json --output /path/to/report.json`

Private examples and helper scripts are in R13 ZIP. Do not treat R12's repeatedly evaluated later-section score or the R13 reviewer's subjective pairing verdict as an untouched independent holdout.
