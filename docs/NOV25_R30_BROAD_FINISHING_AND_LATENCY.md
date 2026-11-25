# R30 — broad finishing and isolated stage checks (Nov 25)

Continuation of R28/R29, not a reset. R30 private archive contains recipes, renders and exact source hashes; no audio, fitted models or proprietary code here. 18 archived comparison groups, 180 bounded finishing evaluations, 45/25/30 chronological fit/selection/final split. Baselines: previous owner pick (B research fallback for neither), optionally prior dynamics trial selected on training, compared against both raw and train-calibrated gain-only. Objective composite combines 10-band absolute spectral error, synchronized active-window envelope difference, normalized waveform residual, stereo side/mid and correlation. Accept only >=5% final score reduction, component limits, estimated 4x true peak <= -1 dBTP, exact export recheck. All comparisons are same-take archived, repeatedly explored; not independent performance evidence.

| Comparison | Baseline final score | Challenger final score |
|---|---:|---:|
| Nobody full | 3.722 | 3.393 (native 4x saturation follow-up) |
| Nobody reverb | 2.442 | 2.233 |
| UP main | 2.191 | 2.008 |
| Overtime main | 2.146 | 1.929 |
| Speakerz main | 2.464 | 2.300 |
| Hop Out main | 9.417 | 8.464 |
| Muffle base | 7.060 | 6.570 |

Seven pass initial broad gates. Nobody full exploratory soft clip replaced for listening with native oversampled follow-up; follow-up not independent. Hop Out and Muffle width edits do not reconstruct real modulation. Other eleven fail or lack eligible final challenger. Deuce, Alchemist and protected Club Gate not included in this recovered R28 18-comparison archive; preserve exact picks, do not substitute unrelated clips. No new listening feedback.

Eight same-take isolated effects checked with sparse causal stereo taps, six fixed candidate sizes per pair. Overtime distortion delay final RMS residual 0.6726 -> 0.0689 vs train-calibrated gain-only, estimated peak -4.878 dBTP; only pass. Myers delay 0.1503 -> 0.1191 but peak +1.365 dBTP, reject. Both Uh Huh delay pairs show 670 ms envelope correlation lag and weak correlation; inspect wet-only / routing alignment before fitting. Other four not improved under gates. Sparse taps are a restricted fixed stage model, not full delay/modulation plugin parity.

SkellCore draft #47 opt-in aligned formant commit 72993340: measured legacy wet peak 1024 samples vs neutral 768; aligned revision 1024 both. 30 native local checks and ASan/UBSan passed, 5 rates; old presets/engines unchanged. Uh Huh formant shape score 2.516 -> 2.371 dB, but +0.77 dBTP, reject. Need unvoiced/consonant, automation and independent transfer tests. SkellyTune Playground still returns GitHub 404, unknown rename/authorization; do not change Classic/Crystal. Local JUCE DNS blocked; no new VST3 or Quick4 evidence.

Next: recover exact missing protected references; correct Wobbly/Zaam stereo signal routing, Angelic wet stages, Uh Huh stage geometry, Deep Voice character; no generic width promotion. Keep all prior artifacts. Private lab 8 comparisons (31 clips), common safety trim, original outside voting; browser navigation blocked in this runtime, verify on user's machine before relying on it.
