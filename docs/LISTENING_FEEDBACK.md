# Listening feedback and current experimental versions

**Owner feedback:** No new listening results submitted. Earlier Round 2/3 observations are preserved in their existing documents. Do not infer approval from numeric improvements.

## Main and gate experiments

| Target / version | Held-out waveform error: prior → new | Band MAE: prior → new (dB) | Envelope MAE: prior → new (dB) | Status |
|---|---:|---:|---:|---|
| deuce R5C | 1.144 → 0.667 | 3.305 → 3.331 | 4.188 → 4.151 | Experimental holdout pass |
| alchemist R5C | 1.220 → 0.552 | 1.929 → 1.929 | 1.576 → 1.573 | Experimental holdout pass |
| speakerz R5C | 1.129 → 0.487 | 1.332 → 1.305 | 1.314 → 1.278 | Experimental holdout pass |
| hop_out R5C | 1.405 → 0.543 | 1.997 → 1.996 | 0.906 → 0.912 | Experimental holdout pass |

R5C uses a private train-derived phase-only filter after the earlier R4 source-only chain. Declared latency is 2048 samples (46.44 ms at 44.1 kHz), compensated explicitly in the listening crop. Alchemist input remains REC-printed, not untreated dry. The separate Alchemist R5B candidate is also retained for character/brightness review. No native preset, host parameter or factory identity changed.

Club Gate R5 quiet-region heldout MSE decreased from 4.723e-7 to 1.494e-7 versus raw bypass (68.4% reduction). Active error stayed essentially unchanged. The historical near-approved gate was not replaced.

## Adlib recreation research

The original FST metadata indicates chorus, nonlinear dynamics, filters, convolution, reverb/delay and (for Wobbly) flanger/phaser/Panagement. This evidences names/order only; settings and bypass states remain unverified. R6 introduces nonlinear delayed features and a periodically varying filter, with rate/ridge selection on nested TRAIN validation only. Wobbly selected 0.4 Hz; the other three selected the static control. All initial R6 and finishing R6B trials failed the combined quality gate. R6C blends are selected using training audio only.

| Target / R6C | Band MAE (dB) | Envelope MAE (dB) | Waveform relative RMS | Outcome |
|---|---:|---:|---:|---|
| angelic_adlib | 2.547 | 4.371 | 1.372 | REJECTED_REGRESSION |
| muffle_adlib | 3.770 | 2.191 | 1.060 | RESEARCH_HOLDOUT_PASS |
| wobbly_adlib | 2.716 | 2.560 | 1.202 | REJECTED_REGRESSION |
| zaam_adlib | 3.897 | 5.289 | 1.227 | REJECTED_REGRESSION |

Muffle R6C improves envelope and waveform error while band error rises by about 0.097 dB, within the declared 0.1 dB tradeoff tolerance. It is an incomplete filtered/effects recreation, not a completed modulation chain. Its corresponding original adlib print is used; the card remains UNVERIFIED because required creative stages are incomplete. Failed Angelic/Wobbly/Zaam candidates are preserved privately and excluded from voting.

## Verification boundaries

- Local package regression suite: 219 passed (including synthetic DOM/audio playback tests and train/holdout isolation tests). The local partial checkout omits three historical archive/materialization test files; full exact-head GitHub CI is separate.
- Local Python wheel build passed. This is not a VST3 build.
- All embedded clips are decoded back, peak-estimated at 4x and checked for comparable integrated loudness. Hashes bind actual source, reference and candidate versions; candidate timing is checked against its processed reference.
- Real in-app browser access to the listening server timed out even after the server reported listening. Actual browser screenshots, mobile interaction and physical device playback remain UNVERIFIED. Synthetic runtime tests are not browser inspection.
- Four frozen main chains passed finite/peak safety checks on a different source. No independent paired processed target was available, so transfer sound accuracy remains UNVERIFIED. Offline CPU timing and declared latency are recorded privately; no realtime/native CPU claim.
- Native Windows VST3/Quick4/FL Studio validation remains UNVERIFIED. JUCE 8.0.12 was located locally; Sound Match is an offline Python project.
- Never publish owner vocals, embedded HTML, FST/FLP state, private model coefficients or source-derived filters. Keep PR #2 draft; do not merge.
