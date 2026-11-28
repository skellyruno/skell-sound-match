# Fresh spatial challenger batch

Continues commit 6681e1c on existing draft PR #2. All nine sounds received a new trial. Owner selections remain the protected comparison identities.

## Method

Added causal three-voice moving-delay processing. Rate, base delay, modulation depth and bounded dry/wet coefficients are selected on an internal validation window within TRAIN. Each channel retains its own direct signal with a nonnegative coefficient. Delayed wet paths use independent modulation phases. Training-only mid/side energy calibration adjusts the actual moving-path output. No reference samples are mixed into a render.

Finishing uses the existing bounded EQ/level optimizer on the fresh spatial output. The composed output must beat the original starting diagnostic anchor, meet absolute level/tone/envelope/width/correlation limits, and pass emitted-audio safety checks. This additional composed-chain check prevents a finishing stage from approving an output that only beats a weaker intermediate render.

## Same-take results

Scores use the existing weighted feature objective. The starting renders were initially treated as diagnostic baselines. The exact R5 audition excerpts were subsequently recovered from the private battle HTML and verified against owner-feedback session 04ef2153d69dda2e7051355a. Muffle A/C and Zaam A/B identities were checked directly against that session. Speakerz R6 winner audio remains unavailable in this local batch. Owner approval and independent-performance transfer remain open.

| Target | Starting score | Final trial score | Outcome |
|---|---:|---:|---|
| Deuce | 8.214 | 8.325 | Reference repair required |
| Alchemist | 2.053 | 2.010 | Emitted level mismatch |
| Club MIC Gate | 0.618 | 0.691 | Regression |
| Angelic | 4.172 | 3.036 | Tone regression against starting anchor |
| Muffle | 2.762 | 1.626 | Experimental diagnostic-anchor pass |
| Wobbly | 6.225 | 4.573 | Absolute envelope error too high |
| Zaam | 5.993 | 3.562 | Experimental diagnostic-anchor pass |
| Speakerz | 3.281 | 1.275 | Emitted level and envelope checks failed |
| Hop Out | 1.971 | 2.125 | Composed trial fails starting anchor |

Muffle emitted band/envelope errors are 2.169/1.885 dB, width error 0.297 dB, correlation error 0.019, level mismatch 1.199 dB and estimated peak -7.10 dBTP. Zaam emitted band/envelope errors are 4.374/4.396 dB, width error 1.437 dB, correlation error 0.070 and level mismatch 1.721 dB. Active-window spatial character and mono compatibility need further listening and independent-performance validation.

Exact-session excerpt comparison, RMS matched for shape scoring, gave Muffle protected A/C scores 2.762/3.007 versus new 1.626, and Zaam protected A/B scores 5.993/6.241 versus new 3.562. This confirms improvement in the measured objective against those specific survivor excerpts. The protected versions retain their ownership status until the user chooses otherwise. Full-render level checks above remain separate from the RMS-matched excerpt comparison.

## Verification and handoff

- Full available local package suite passed 255 tests with 1 optional Pedalboard runtime test skipped. Python wheel built. Three focused spatial tests were subsequently run after adding the composed-anchor regression check.
- Synthetic tests cover planted moving-delay recovery, frozen independent input, causal replay, training-only model/energy calibration and rejection against a stronger starting anchor.
- New WAVs, learned parameters, source hashes and experiment histories stay private. Each of the nine targets has a fresh report. Qualified Muffle/Zaam audio is packaged privately for later survivor review.
- Deuce reference repair remains required. Gate onset, Alchemist character/level, Speakerz full stereo/presence, Hop Out stage composition, Angelic chorus/delay and Wobbly moving phase/pitch remain active tasks. Tempo/key benchmarking remains deferred.
- A nine-target battle is deferred until enough fresh challengers and protected survivor files are available for accurate comparisons. No rejected trial is inserted to fill a slot.
- This batch changes offline DSP research. Native VST3/FL Studio verification and real-browser screenshots were not run. Exact-commit GitHub CI is separate.
