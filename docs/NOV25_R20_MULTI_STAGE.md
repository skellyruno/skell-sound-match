# R20 — multi-stage native DSP and feedback integrity

This is an additive research checkpoint after R19. CI for R19 at `a138a56cd7bcd194f0f9e4845717b2db3b69296d` succeeded before this update. Private history and audio are not committed. Draft PR stays unmerged.

## Scope and results
- R19 partial feedback import: 26 reviewed and one unreviewed group. The private archive validates exact reference and candidate hashes, preserves every selection and rejects promotion without stronger evidence. Original user feedback remains private.
- Recovered private source for ChorusFx Classic, Hyper and Vintage and the original native Delay 2/3 offline adapters from earlier checkpoints. Isolated Linux C++17 native builds passed. Twenty additional native rate/engine partition checks at 44.1/48/96/192 kHz had finite samples and identical tested 127/512/1024 output; supplied Delay 2/3 regression test passed.
- In the isolated Hop Out chorus experiment, the previous listening-selected native Flangus render has R19-preview error 9.221; fitted native Vintage Chorus 1.790 and Classic Chorus 2.709. The newer engines' settings are experimental, not verified original preset states or user-selected replacements.
- Native Delay 2 saved-state experiments on two Overtime stage exports reduce R19-compatible errors 39.374→8.639 and 44.713→8.889. Distortion has a project state without independently verified track routing and slightly worse waveform NRMSE, so it remains listening-only.
- Inferred native Delay 2/3 wet sends added to the retained Hop Out full-effects reference A worsen R19 preview error 4.455→4.926/5.124, not numerical passes. Separate sparse echo fitting found negligible Hop Out wet tap weights; delay recovery is incomplete.
- A bounded offline approximation of Fruity Limiter's noise-gate *branch*, applied after the retained Club Gate B, gives stronger attenuation but slight score regressions (0.831→0.866 and 0.975). It is not a full Limiter emulator or an approved preset.
- New `stage_tools.py` and tests cover sample-count causal decay and stereo two-tap echo for offline research only, with no plugin-callback safety or FL Studio parity claim. No source, audio, fitted parameters, DAW states, or feedback are checked in.

## Verification and limitations
- 84 R19 preview SHA-256 checks passed. New 20 lossless audio clips had verified hashes and 4x-oversampled estimated true peaks ≤−1.49 dBTP, private only.
- 49 focused Python tests passed: 16 new and 33 prior. New 5-group HTML lab tested in real Chromium desktop/mobile for playback/reset/filter/export with no JS errors or overflow; screenshots inspected. No real Windows VST3 host/FL Studio A/B, CPU profiling, independent held-out validation or owner votes for R20. Prior approved presets and all R19 listening winners remain unchanged.
- Maintain all 57 R19 target/stage coverage entries; rejected and unreviewed items stay in backlog. Next: reconcile complete effect ordering and saved states, user-prioritized native chorus/delay/gate; rebuild independent validations; continue other full effects/adlib and main-vocal targets. Do not merge.
