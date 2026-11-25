# Audio-only matching: transfer to new vocals without source presets

Owner explicitly requests no dependency on supplied code or original dry vocals/FST. Three independent tracks: paired black-box identification (aligned dry/processed original), reference-only transfer (processed target and unrelated new raw vocals), engine-assisted analysis (original settings or owner-supplied implementation only when available). Prior engine results remain evidence and optional teachers, never mandatory. Rendered new vocal must contain only its own input and synthetic/model-generated FX; no reference excerpts mixed in. No unique original chain identification from unpaired recording; distinguish tone, pitch/formant, dynamics, stereo, temporal FX, performance and mic differences. No auto promotion from statistics alone.

Owner feedback session native-bank-convolver-stage-20261124: notes "b wins" Angelic isolated Bank B = Angelic-saved-Bank-on-processed-input; Muffle "none win". Both groups reviewable false, submitted false, empty winner fields: qualitative owner preference/rejection, not formal votes or full-preset approval. Preserve B exact render, all historical clips, prior liked Muffle anchor; do not promote Muffle partial chain or slot-mix trial. Preserve all nine protected original targets, ten provisional families separately.

## Code
reference_transfer.py: offline NumPy/SciPy-only profile of active-frame spectral-band distributions (6 bands, q25/50/75), centered RMS quantiles and side/mid width quantiles; shape score = tone + .5*dynamics + .2*width. Absolute level reported separately. Analysis standardized to 44.1k; no waveform comparison of unrelated content. Recipe has four bounded EQ-band gains, relative-input-level compressor/gate, short fixed stereo decorrelation, generic two-tap echo, deterministic synthetic .65s room IR and output gain. Relative input level calculated offline on each new source. Render accepts new audio and numeric recipe only, same-length output (tails truncated unless input padded); no real-time safety claim. Two coordinate sweeps, generic time grid 125/250/375/500/750/1000ms, mean/worst robust objective across training sources. No prior saved settings in final grid. First exploratory single-source grid included two previously known timing values; final multi-source grid deliberately excludes them. Independent source fits remain approximate, not original DSP or recovered knobs.

sparse_delay.py: paired aligned input/target only, causal correlation on training residual proposes up to five delayed stereo matrices (direct plus 3.5k LP basis, ridge fit), outputs compact transferable lag/matrix recipe. No copied reference audio, no supplied implementation. Same input sample rate for real tests, lag duration rescales on other rates. Offline, not exact feedback/filter/modulation identification. Reject invalid pair/recipe.

## Reference-only experiment
Nine target references: two historical excerpts (Deuce/Alchemist), original Club five prints, original Speakerz complete stereo print, Hop Out full print active region first 16s. Fit first <=60% (max six seconds) of each processed reference against 2–7s of unrelated Speakerz dry (Hop Out dry for Speakerz target) and Wait dry. No FST/raw original or supplied code during fit. Later 40% reference held out of fitting; UP dry 5–11s and Myers dry 4–10s never used for fit. Seven targets also tested on their withheld original dry, later portion; geometry checked. Still same reference performance, not independent target performance; sources were used in other historical research but not fit for these recipes. Preliminary single-source 8/9 lower UP score; final multi-source 783 candidate evaluations across two source bases. Independent source holdouts below, no promotions.

| Target | UP baseline -> trial | Myers baseline -> trial | UP / Myers peak dBTP |
|---|---|---|---|
| Deuce | 18.219 -> 10.414 | 14.349 -> 7.768 | -5.94 / -1.69 |
| Alchemist | 15.117 -> 4.778 | 13.428 -> 5.722 | -7.04 / -1.92 |
| Speakerz | 12.825 -> 13.469 | 11.158 -> 9.070 | -1.73 / -1.34 |
| Hop Out | 25.893 -> 12.410 | 22.152 -> 9.954 | -3.71 / -.55 |
| Angelic | 19.484 -> 7.202 | 15.896 -> 7.632 | -8.09 / -2.52 |
| Muffle | 22.473 -> 8.672 | 21.510 -> 7.928 | -10.40 / -8.40 |
| Wobbly | 16.787 -> 8.029 | 14.120 -> 9.181 | -8.18 / -5.09 |
| Zaam | 22.742 -> 7.624 | 19.501 -> 6.422 | -12.42 / -9.44 |
| Club Gate | 4.392 -> 4.864 | 6.854 -> 6.074 | -7.43 / -5.79 |

Seven lower composite on both sources, not seven accurate presets. Hop Out fails -1 dBTP on Myers; Speakerz and Club Gate fail UP. Wobbly tone/dynamics regress on Myers, Hop Out UP dynamics regresses, Muffle Myers dynamics slightly regresses. Width accounts for substantial portions of adlib gains; tone/dynamics and temporal character must be separately gated. Club Gate original dry later active profile .002, trial 1.454: active-only metric ignores quiet/onsets, cannot validate gate. No actual original gate replacement. Some recipes reach bounds and add incorrect echo (e.g. Alchemist) because timing not identified by objective. Do not use as production preset; improve temporal/tail, quiet/noise, phoneme/pitch-conditioned features, pitch/formant inference and per-metric rejection. Clip-safe matched previews only, no hidden limiting in recipes.

## Audio-only paired echo probe (first60/last40)
Actual UP, Speakerz, Hop Out and Angelic stage WAVs only, no FST or supplied engines. Direct linear matrix/LP baseline vs sparse model; later nonrail relative RMS:
- UP dominant 854.943ms, second 1709.909ms, .214111 -> .056018; peak +3.44 dBTP (unsafe).
- Speakerz 932.404ms and 1864.830ms plus smaller neighboring taps, .205994 -> .084560; peak +.42 (unsafe).
- Hop Out 779.229ms and 1558.458ms plus neighbors, .087405 -> .054519; peak -3.40.
- Angelic 925.692ms dominant candidate, .403932 -> .406653 (reject), downstream modulation and routing still confounded.
No claims of unique timing or exact algorithm. New code can implement own stereo matrices, filter, repeats; next fit feedback gain/decay/cutoff, time-varying delay, dynamic wet routing, independent take validation. Compare against supplied engines separately to diagnose which parameter law or structure is missing; no shared dependency for audio-only fit.

## Verification
Prior Windows run 45539974615 failed one checkpoint test (332 passed, 2 skipped), Windows zipfile normalizes backslash member path. Reject unsafe manifest path explicitly with clear diagnostic; regression simulates normalized member. 28 local pytest tests across checkpoint, reference transfer and sparse delay passed, includes multirate and synthetic new-source transfer. Full Windows CI for new head pending. Local JUCE fetch DNS failed; offline research only, no plugin build or UI claim. Private recipes, audio, source identities/hashes and feedback JSON kept outside public Git. Existing Sound Match draft only; no merge.
