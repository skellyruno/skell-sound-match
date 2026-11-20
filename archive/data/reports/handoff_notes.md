# Skelly Vocal Match: Handoff

Everything built in this working session, what was verified, what was not, and where to go next.
Read section 1, then jump to what you need.

## 1. TL;DR

Two independent pieces of work:

| | What | Where | Status |
|---|---|---|---|
| **A** | `vocal_match.py`: a CLI tool that compares a raw vocal with a mixed vocal and estimates a plugin-chain preset (HPF/LPF, gate, de-esser, saturation, compressor, 8-band EQ, delay, reverb, flanger/chorus, output gain, limiter), plus analysis of pitch correction, key and stereo | `1_vocal_match/` | Works on synthetic vocals. **Never run on real recordings.** |
| **B** | `vocalmatch_refine.py`: a post-stage that learns a small correction (loudness contour, optional multiband and EQ) from a previous Deuce render plus the reference. Built and scored on your Deuce files | `2_skelly_refine_v1_8/` | Experimental, **not listened to**. Small, measured gains on v1.7 |

Also included: `3_research_scripts/` (the experiments behind the findings) and `CHECKSUMS.sha256`.

**Most important things to know**
1. Nothing here has been listened to. All accuracy claims are measured numbers, not audio judgment.
2. For Deuce, v1.7 is already close to the best any gain/EQ/filter correction can reach (section 3.3). Gains from Part B are modest, and the "max" profile trades spectral accuracy for waveform accuracy.
3. Part A's test data was processed with the tool's *own* effect code, so real-world accuracy will be lower than the synthetic numbers.
4. I did not touch any of your files. Everything here is new.

## 2. Part A: `vocal_match.py`

### What it does
`python vocal_match.py analyze raw.wav mixed.wav -o preset.json --render preview.wav`

Outputs JSON on stdout (progress on stderr, exit code 1 plus `{"error": ...}` on failure). Chain modelled, in order:
`hpf -> lpf -> gate -> de-esser -> saturation -> compressor -> 8-band EQ -> modulation -> delay + reverb (parallel) -> gain -> limiter`.
Reported but not rendered in previews: pitch correction / transposition / key guess, stereo width / Haas delay.

Other commands: `apply RAW PRESET OUT [--target MIXED]`, `export PRESET [--format json|text]` (plugin-style settings sheet), `schema` (function-calling tool definition for AI agents).
Flags: `--skip a,b` (deesser, saturation, delay, reverb, gate, modulation, limiter, hpf, lpf, pitch, stereo), `--quality off|fast|normal|high`, `--bpm N` (adds delay note values).
Needs numpy, scipy (soundfile optional; scikit-learn not needed). About 1,450 lines.

### How it works (two stages)
1. **Statistical first guesses:** spectral EQ match, loudness curve, an impulse response between the processed-dry signal and the mix (delay taps, reverb tail), sibilance spread, harmonic detail, f0 tracks, stereo analysis.
2. **Analysis-by-synthesis refinement** (only when raw and mixed are the same take): renders the chain, compares multi-resolution log-spectrograms against the mix, tests each optional effect on/off, and tunes parameters by coordinate descent. An effect is kept only if it lowers the error by at least 1 %; the size of that improvement becomes its `confidence`. A same-take score (level- and EQ-independent spectral-pattern correlation, threshold 0.45) gates this stage.
   If the files are different takes, nothing time-aligned is claimed (verified: same-take score 0.01, no optional effects, pitch skipped).

### Test results (synthetic vocals; truth in brackets)
| Case | Result |
|---|---|
| Delay + reverb | Delay 376 ms (375), -11.1 dB (-10); reverb pre-delay 10 ms (10), RT60 1.54 s (1.6), -15.7 dB (-15) |
| Slap delay | 109 ms, -8.75 dB (110, -8) |
| High-pass | 100 Hz (100) in the stress test; 202 Hz (150) in another |
| De-esser | right band (6450 Hz), ratio 3.6 (5), threshold -30.9 dB (-30) |
| Saturation | tanh drive 4.0 (4.0) |
| Flanger | 0.40 Hz (0.4), base 2.06 ms (2.0), depth 1.52 ms (1.5); wet level 0.5 (0.7) |
| Gate | threshold -18.3 dB (-17), range 17 dB (20) |
| Limiter | detected (flat-topped peaks) |
| Pitch | hard tuning detected exactly; +3 and -5 semitone transposition and key recovered |
| Stereo / tempo | 12 ms Haas delay found; 469 ms read as dotted 1/8 at 96 BPM |
| Dry vocal | no false effects |

### Known weaknesses (be aware of these)
- **Multi-voice chorus is not detected.** A single-voice chorus test was also missed; phaser, vibrato and tremolo render but are never detected. Flanger and constant short delays work.
- **Plate-style reverb** came back with RT60 too long in an earlier run (1.36 s vs 0.8 s true), and I did not re-verify that case after the final changes.
- **Compressor and saturator overlap** (both squash peaks), so ratio/drive are approximate. A heavy de-esser can be hidden by the compressor estimate.
- **Low-pass** was not detected in my test (my test vocal had almost no energy above 9 kHz).
- **Partial pitch correction is ambiguous:** a constant offset left in the mix looks identical to a different tuning reference. The output says so (`reference_offset_cents`, `note`).
- Echoes or chorus on the mixed vocal can confuse the f0 tracker; the tool detects disagreement and refuses to call correction.
- Pitch and stereo are not rendered in previews.
- Runs about 20-30 s per file at `normal` quality.
- Two ideas I tried and removed because they did not work: coherence-based tuning of the compressor, and IR-leakage-based tuning.

### Test harness
`1_vocal_match/test_harness/`: `mk.py` (synthetic vocal), `scen3.py` (scenarios A-L), `show.py` (summary printer). Hard-coded to run from a folder containing `vocal_match.py`. Because the test audio is rendered by the tool's own effects, treat results as "can it recover what it can render", not real-world accuracy.

## 3. Part B: Skelly / Deuce work

### 3.1 What you sent and what I did with each zip
| Zip | What I did |
|---|---|
| `Skelly_Sound_Matching_v0_6_Alchemist` | Unpacked and read README, report, code. **Did not improve it.** I could not run its tests (no `soundfile` in the sandbox) and my SHA-256 manifest check was inconclusive. Summary only. |
| `Skelly_Deuce_SoundMatch_v1_0_Complete` | Reproduced all published v0.9/v1.0 metrics **exactly**, analysed where v1.0's error lives, ran honest cross-validated experiments (section 3.3). Contains the full reference (18.75 s) but **no dry vocal**, so I could not re-run your fitting pipeline. |
| `Skelly_Deuce_v1_7_Complete` | Verified the 7 s reference excerpt is exactly samples 7.2-14.2 s of the v1.0 reference (correlation 1.0000) and the full v1.7 experiment aligns at lag 0, then scored v1.7 against the full reference and built the Part B tool on top of it. v1.4 (your approved benchmark) is **not** scored: only a 7 s excerpt is in that zip. |

### 3.2 Scoreboard (full reference, v1.0 metric code, middle / late passage)
| Candidate | Correlation | Spectral dB | 20 ms env dB | 200 ms env dB | Whole-file residual |
|---|---|---|---|---|---|
| v1.0 | 0.958 / 0.962 | 0.73 / 0.90 | 1.47 / 1.30 | 0.76 / 0.51 | -11.14 dB |
| v1.7 experiment | 0.972 / 0.974 | 0.64 / **0.45** | 1.23 / 1.05 | 0.66 / 0.35 | -12.58 dB |
| v1.8 safe (out-of-fold) | 0.972 / 0.975 | 0.63 / 0.46 | 1.11 / 0.97 | 0.50 / 0.32 | -12.59 dB |
| v1.8 max (out-of-fold) | **0.974 / 0.977** | 0.69 / 0.58 | **1.06 / 0.91** | **0.49 / 0.27** | **-12.99 dB** |

"Out-of-fold" = each ~3 s block was predicted by a model trained on the other blocks (0.25 s gap), then crossfaded. Full data: `2_skelly_refine_v1_8/reports/Deuce_v18_Scoreboard.json` and `.png`.

- **safe** (contour only): envelope errors improve in both held-out windows, nothing else moves; gate passes.
- **max** (contour + multiband + gentle EQ): more waveform accuracy and best envelope numbers, but late spectral error worsens 0.45 -> 0.58 dB; gate fails and needs `--force`. Pick by listening.
- Pitch-shift stress test (+1 / +3 semitones): safe neutral, max still helps, so neither profile is memorising the melody.

### 3.3 Findings (the reasoning behind the design)
1. **Ceiling:** an oracle that sees the reference every frame reaches only -14.3 dB residual on v1.0 (LTI filter -12.2, per-frame gain -12.4 to -13.0). v1.7 at -12.6 dB is already close; remaining error is fine harmonic structure.
2. **Not pitch, not timing:** reference vs v1.0 pitch median 0.0 cents (94 % of frames within 5 cents); sub-sample delay jitter about 0.1 sample.
3. **Fine EQ memorises the melody.** Same-song CV rewards 1/24-octave EQ (-12.36 dB), but after a 3-semitone pitch shift it is *worse than doing nothing* (-10.15 vs -11.02). Default is 1/4 octave. (The stress test is pessimistic because resampling also shifts the chain's response.)
4. **Rejected:** a ridge FIR + band-dynamics stage looked good in-song (-11.77 dB) but failed the shift test (-10.74 dB).
5. On v1.0 the stack contour -> multiband -> EQ went -11.14 -> -12.63 dB; most of that disappears on v1.7, which already captures it.
6. A bug I made and fixed during this work: an even-length FIR kernel shifts the signal half a sample and wrecks high-frequency matching (it initially made results look terrible).

### 3.4 `vocalmatch_refine.py`
```bash
python code/vocalmatch_refine.py cv  --previous prev.wav --reference ref.wav --out-dir cv_out --profile safe
python code/vocalmatch_refine.py fit --previous prev.wav --reference ref.wav --out model.json --profile safe --report cv.json
python code/vocalmatch_refine.py apply --previous new_render.wav --model model.json --out refined.wav
python tests/test_refine_v18.py      # 8 portable tests, synthetic data
```
Safety: never overwrites files; `fit` refuses to write a model unless the CV gate passes (`--force` overrides); verifies same take (envelope correlation >= 0.58, lag <= 5 ms); local true-peak guard at -1 dBTP; models are JSON (trees stored as data, no pickle). Needs numpy, scipy, scikit-learn (fit only).

Audio in `2_skelly_refine_v1_8/audio/`: `*_OutOfFold_*` are the honest audition renders (numbers above come from these); `*_FullFit_*` have seen every block (optimistic); `v18_*_7sec.wav` match your A/B excerpt position (7.2-14.2 s) and level.

## 4. Verification status
**Run and passing:** the 8 refine-tool tests; reproduction of your published v1.0 metrics; the synthetic scenarios in section 2; end-to-end CLI checks (apply, export, schema, error exits, overwrite refusal).
**Not done:**
- No real vocals tested with `vocal_match.py`.
- **No listening.** The Skelly audio was only measured.
- v0.6 tests not run; its SHA-256 manifest not verified.
- v1.4 full file not scored (not provided).
- The test sandbox lacked `soundfile` and `pyloudnorm`. The refine tool has a built-in WAV fallback, so it ran; for LUFS I used a stand-in that differs from real pyloudnorm by about 0.05 dB (scripts only, not deliverables).
- Same-take blocks are not a new vocal, and the middle and late passages were looked at repeatedly across versions, so nothing here is a blind test.
- The FST chain map in the v1.7 zip was not used.

## 5. Suggested next steps (in order)
1. **Listen** to the safe and max out-of-fold files against your v1.4/v1.7 A/B excerpts. That decides whether any of Part B matters.
2. Run `cv` on the **full v1.4 render** against the full reference (needs the full file).
3. Test on a **truly unused vocal take**: the only real test of generalisation.
4. For Part A, run it on a few real raw/mixed pairs you know the chain for, and compare to the truth; fix the multi-voice chorus and plate-reverb cases first.
5. If a causal/VST3 version is wanted, replace centred smoothing and zero-phase filters in Part B with causal equivalents and re-measure.

## 6. File map
```
HANDOFF.md                      this file
CHECKSUMS.sha256                SHA-256 of every file in the package
1_vocal_match/vocal_match.py    Part A tool (v3 internal numbering)
1_vocal_match/test_harness/     synthetic test generator and scenarios
2_skelly_refine_v1_8/           Part B: README.md, code/, models/, audio/, reports/, tests/
3_research_scripts/             exploratory experiments + test-only shims (see its README)
```
