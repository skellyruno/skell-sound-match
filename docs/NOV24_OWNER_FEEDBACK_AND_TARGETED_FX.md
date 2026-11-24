# Owner feedback and targeted FX reconstruction (2026-11-23 ET / 24 UTC)

Owner session d98289e49b398450f7ffc24c was checked against the exact prior private HTML (reference and version hashes). These are relative owner preferences, not release approval.

- Alchemist: C, alchemist-nov24-adaptive-excerpt-env0.65-3, wins; B eliminated; retain A.
- Angelic: all three rejected; archive them, no current champion.
- Club MIC Gate: both sound good; freeze both versions and stop gate tuning. The inspected Club ZIP contains raw, gate, and four adlib prints, but no standalone main-vocal print. Do not infer one from the adlibs.
- Hop Out: C, hop_out-nov24-adaptive-excerpt-env0.65-6, wins; A eliminated; B remains.
- Muffle: A, muffle_adlib-nov23b, wins; C eliminated; B archived as alternate. Owner explicitly needs reverb, delay and convolution improvement.
- Zaam: all three rejected; no champion. Preserve historical versions.
- Wobbly: C, wobbly-nov24-rhythmic-moving-delay-8.675-1.0, is the sole active baseline. The free-text instruction explicitly eliminates BOTH A and B, superseding the export's single-elimination survivor list. Keep the historical audio archived.
- Deuce: restore the established offline v2.5 preference dated Nov 15; D/Max rollback remains protected. R5 comparison mismatch is separate from v2.5. Do not mislabel R5 excerpt as v2.5 or claim the native Sustained Air stage is complete.
- Speakerz: C, speakerz-nov24-adaptive-excerpt-env0.65-6, wins; A eliminated; B remains. Prior R6 audio recovered.

## Effects investigation and new experiments

Club source ZIP verified at 44.1 kHz, identical recording lengths. FST UTF-16 names corroborate Angelic Chorus, Delay Bank, Flangus and Reeverb 2; Muffle Love Philter, Convolver, Flangus, Reeverb 2 and Delay 3; Wobbly Chorus, Flanger, Phaser, Convolver and Panagement 2; Zaam Chorus, Flangus, Reeverb 2 and Delay 2. Names do not establish exact settings.

Angelic no-delay / full-stage same-take comparison: strongest late residual waveform correlation around 925–928 ms; envelope lag around 920 ms (correlation 0.708). Zaam has strong source correlation around 463–465 ms and envelope peak around 470 ms. These are measured lag hypotheses, not confirmed host tempo or exact settings. An isolated Angelic linear delay IR attempt worsened later relative waveform error 0.3882 to 0.4067 and is rejected as an exact stage model.

New private trials fit on the prefix before the excerpt where source stage audio was available, using the actual gate print as input; no reference samples are mixed into new renders. Repeated same-take excerpt scores are research diagnostics, not unseen holdout or independent transfer. Lower composite error is better; not percentages of accuracy.

| Target | Comparison baseline | New first/later score | Decision |
|---|---|---|---|
| Angelic | previously rejected C 3.194 / 3.837 | separated 925 ms echo 2.864 / 3.071 | new experimental comparison; second stage trial 2.725 / 3.466 |
| Wobbly | owner C 4.744 / 4.645 | 4.687 / 4.325 | new linked/independent mid-side LFO refinement, 8.675 Hz retained |
| Muffle | owner A 7.355 / 5.726 | 5.641 / 5.029 | new structured early path, moving taps, diffuse convolution-style reverb and echo |
| Zaam | rejected C 2.596 / 2.407 | 2.969 / 2.859 | exploratory explicit 465 ms echo; not a measured improvement |

Wobbly new challenger needed challenger-only offline oversampled peak-gain correction for loudness fairness; score recalculated after correction, original owner C unchanged. Several Muffle hybrid variants and other Zaam/Angelic trials were inferior; not promoted.

Private targeted lab session a9c37db262dc5c8bca5ab591: 9 groups, 24 clips, 4 reviewable (Angelic, Wobbly, Muffle, Zaam). All decoded with exact rate/frame/URI digest checks, estimated true peak <= -1.5 dBTP within rounding and max group loudness spread 0.0752 LUFS. Chromium headless markup, audio playback clock for 24 clips, reset, selection, single-rating, blocked skip, export, desktop/mobile screenshots passed. Physical playback and independent performance remain unverified. Deuce disputed reference is marked diagnostic and ranking disabled, rather than substituting historical audio.

Reusable adaptive envelope and periodic-gain primitives added, with five focused tests. Local available subset 19 passed (including prior v2 feedback tests). Private experiment scripts/rendered audio, fitted coefficients, HTML, source WAV/FST and other assets are not committed. New exact-head CI pending. PR remains draft; no native preset or production identity changed.

Next: owner audition targeted effects; recover exact v2.5 listening artifact and paired REC→MAIN source before Deuce testing; request Club main paired print if available. Keep owner-selected Alchemist/Hop Out/Speakerz and Wobbly C frozen, and avoid treating prior rejected Angelic/Zaam renders as winners. Independent matched performance, FL Studio, native VST3 validation still required.
