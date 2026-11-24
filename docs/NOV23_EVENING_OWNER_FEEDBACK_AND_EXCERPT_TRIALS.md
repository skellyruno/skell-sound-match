# Nov 23 evening listening continuation — owner session fb79649faec7517fe49d9452

Continues draft PR #2. The original uploaded metadata was validated against the recovered exact private HTML manifest (all nine reference and candidate mappings). The private original and protected renders were not changed. All decisions below are relative listening preferences, not release approvals.

| Preset | Owner decision | Work |
|---|---|---|
| Alchemist | B: alchemist-nov23c; drop alchemist-r5c-phase-finish | Protect B, retain alchemist-main-r5-matched-dynamics-finish. |
| Angelic | B: angelic_adlib-nov23d-tail; drop angelic_adlib-full_effects-r5-battle1-1-parallel-finish-width | Keep parallel-width anchor A; brighter, more delay, less reverb. |
| Club MIC Gate | 4/5 similarity, club_mic_gate-nov23c | Keep this exact render; no forced winner. |
| Hop Out | C: hop_out-nov23g-geometric-echo; drop hop_out-full_effects-r5-battle1-1-parallel-finish-width | Retain parallel-width A; brightness and wet effects. |
| Muffle | A: muffle_adlib-nov23b; drop muffle_adlib-full_effects-r5-battle1-2-parallel-finish-width | Retain battle1-3-parallel-finish-width; close. |
| Zaam | C: zaam_adlib-full_effects-r5-battle1-3-parallel-width; drop zaam_adlib-full_effects-r5-battle1-1-parallel-width | Retain nov23d-tail; more delay and wet. |
| Wobbly | None wins, keep all three original R5 attempts | Time-varying movement still missing. |
| Deuce | No vote; reference issue | Owner hears wet in recreations versus original. Repair complete-effects same-stage reference first. |
| Speakerz | No vote; protected R6 audio unavailable | Recover exact C/B, never substitute R5. |

## Private excerpt finishing experiment

Recovered exact session HTML from Library, not full dry source or full-length chains. Seven new source-candidate-only excerpt experiments were rendered: first 60% selected by diagnostic score; last 40% diagnostic checked. These are short same-take postprocessing trials, **not** independent holdout, not dry-input chain reconstruction, not native DSP and not final approvals. Original and retained URI bytes preserved; no reference samples mixed into outputs. Selected settings and last-section composite error (lower better, not perceptual accuracy):

| Target | Trial | Anchor | New |
|---|---|---:|---:|
| Alchemist | high-frequency +1.2 dB blend | 4.039 | 3.803 |
| Angelic | +3 dB HF blend, bounded quiet tail attenuation, 100 ms echo mix .08 | 5.403 | 4.606 |
| Club Gate | -40 dB relative threshold, .25 attenuation strength | .198 | .198 |
| Hop Out | +1 dB HF blend, 390 ms echo mix .12 | 4.084 | 3.856 |
| Muffle | -3 dB HF blend, +.25 dB side | 5.726 | 5.158 |
| Zaam | retained B source, +1.5 dB HF blend, 160 ms echo mix .14 | 9.821 (winner C), 4.323 (B) | 4.013 |
| Wobbly | 2.5 Hz moving-delay taps, 1.5 ms depth, mix 1.1, side +6 dB | 12.592 (base A) | 10.591 |

Gate earlier-section score .168 to .136; later unchanged. Muffle original stronger side boost rejected on stereo correlation, smaller side change passes. Wobbly improves against all three R5 anchors but ~10 dB envelope error remains; explicitly experimental. Two historical Wobbly anchors selected for next comparison, all three remain archived; no fabricated elimination.

Private lab session 41189f1507e06d4f22044787: nine groups, 31 real audio clips, seven reviewable. All 31 FLACs decode at 44.1kHz, exact crop frames, estimated peak <= -1.5 dBTP within 24-bit rounding and within .000001 LUFS per group. Actual Chromium headless markup rendering (file navigation blocked; page content test), FLAC decode/playback clock, switching/reset, tie, two-candidate no-forced-elimination, blocked skip, JSON export, desktop/mobile screenshots and no horizontal overflow passed. Physical listening/audio-device output remains unverified. Full source, learned models, embedded HTML, and private renders are not committed.

## Compatibility fixes
Current UI exports v2, but prior importer accepted only v1. Added strict v2 validation and dispatch without changing legacy v1 handling. Preserve candidate SHA-256, reference SHA-256, status, previous sessions, rating and eligibility; ignore unsaved votes for actual decisions. 14 focused local validator tests passed; actual nine-group input and browser-generated export validated. Add regression coverage for two-way comparison and clear blocked UI. Full branch CI remains separate. No native preset changes, no VST3/FL Studio/Quick4 evidence.

## Next
Collect owner votes on new private excerpt lab. Recover full source/archive and protected Speakerz R6 clips, rebuild Deuce reference, then use same-take full-length dry/REC and isolated wet stages for Wobbly/Angelic/Hop Out/Zaam. Refit actual chorus/modulated delay and echo/reverb chain and test independent paired performance; do not promote excerpt finish to factory preset.
