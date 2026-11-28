# Audio-only R2: dynamics and temporal guard

Continue the three-track program, no supplied DSP or FST in this fit. Parent 6ea6b4e7e770f8e03c5935d4d33cdcf6e9f4d77c Python CI success. Owner requested continued development, no new vote. All nine original sounds and ten provisional families preserved; Angelic saved Bank B qualitative preference and Muffle rejection remain as recorded. No factory changes.

## Independent reference-only transfer
Added temporal_transfer.py: relative 10 ms RMS quantiles, internal pause fractions and 10/50 ms envelope differences; exclude arbitrary external file padding. These are performance-dependent proxies, not exact noise, articulation, or delay/reverb identification. Two-source bounded refinement, guarded per training source vs frozen initial recipe. Can only reduce previous synthetic echo/room, not infer new timings from unpaired audio. 388 candidate evaluations across nine targets using original training sources/reference split. Plan/Overtime 2–8s not used in earlier reference-only fit or R2 fit; UP/Myers earlier holdouts. Target reference still same previously examined performance. Lower guarded score better; not comparable to prior score definition.

| Target | Plan prior -> R2 | Overtime prior -> R2 | UP prior -> R2 | Myers prior -> R2 |
|---|---|---|---|---|
| Deuce | 8.774 unchanged | 15.433 unchanged | 17.866 unchanged | 20.337 unchanged |
| Alchemist | 9.823 unchanged | 7.179 unchanged | 7.927 unchanged | 9.831 unchanged |
| Speakerz | 13.922 -> 14.154 | 11.287 -> 11.458 | 16.133 -> 17.074 | 19.412 -> 19.417 |
| Hop Out | 15.151 unchanged | 13.846 unchanged | 14.234 unchanged | 18.049 unchanged |
| Angelic | 7.920 -> 8.696 | 6.404 -> 6.267 | 7.596 -> 7.383 | 13.814 -> 13.291 |
| Muffle | 13.679 unchanged | 15.134 unchanged | 15.630 unchanged | 18.748 unchanged |
| Wobbly | 22.094 unchanged | 17.607 unchanged | 17.085 unchanged | 18.544 unchanged |
| Zaam | 6.877 unchanged | 6.807 unchanged | 7.958 unchanged | 12.461 unchanged |
| Club Gate | 14.879 -> 14.443 | 5.111 -> 4.508 | 6.326 -> 6.034 | 12.122 -> 11.650 |

Six choose unchanged, three training-selected. Reject Speakerz/Angelic R2 based on source transfer regression. Club Gate aggregate improved all four but Plan dry 13.834 and UP dry 5.850 still better; UP dynamics error regresses .308 dB. Club R2 changes spectral controls, not validated gate itself. Experimental only, no promotion. Hop Out still exceeds peak gate on Overtime/Myers.

## Independent paired dynamics
paired_dynamics.py: linked causal max of two exponential detectors, bounded downward expansion and optional compression curve, output gain. No supplied engine. Gate-only fitting 180 training evaluations, 20 final population validation candidates; Club full aligned original raw/gate same performance: 40% fit, 20% selection, last 40% diagnostic. Gain-only baseline fitted on first section. Later normalized MSE active .000241203 unchanged; quiet .331142540 -> .019911914 (93.99% lower); onset .000012059 unchanged. Estimated -6.4867 dBTP. Active/quiet/onset counts later 103103/71331/59; initial threshold 100 onset samples rejected validation with 55; relaxed explicitly to 40 onset-only, 106/55/59 samples, limited confidence. No comparison win vs existing protected gate, no independent performance or compressor fit, no exact FL equivalence. Fit requires aligned source/target, not reference-only. No reference waveform used in rendering.

Local subset 36 pytest passed including eight new cases, mono/rates 32–192k, causality, stereo link, quiet metric, invalid input, unchanged recipe. Private research scripts and exact hashes/recipes, 36-row metrics CSV, 11-clip FLAC HTML, and checkpoint (21 member hashes verified) retained outside public Git. HTML decoded clip finite and peak verification plus Node JS syntax passed; playback/visual inspection unverified. Local pinned JUCE fetch failed DNS; no VST3 or Quick4 screenshot. No private source, audio or settings published. Next: fit independent compressor on verified isolated stage, phoneme/pitch-conditioned spectrum, matched dynamic wet routing/echo and reverberation, independent same-style recordings, and implement native streaming dynamics only once validated. Preserve all earlier checkpoints.
