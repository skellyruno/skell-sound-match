# Punch-in-aware matching — offline research

Some final vocals contain multiple recorded punch-in takes. Mic position, input gain, articulation and noise can change between segments even when the same REC→MAIN effects chain is active.

The new `detect_regions` method finds **candidate separated vocal activity regions using the dry source only**. These are not confirmed recording edits. Verify edit boundaries in the FL Studio playlist/comp when possible. Use `python -m skell_sound_match.punch_in "dry.wav"` to print the region list locally.

`blend_regions` uses approved render candidates and manually reviewed weights on each active region, with weight transitions only in the silent gaps. It never uses reference audio during rendering, changes the original audio, or imports guessed automation IDs. Do not reuse timestamp-specific weights on unseen takes or export them as universal plugin presets.

Deuce's 15-second research preview covers four detected vocal regions (offset +0.94s relative to its full take): approximately 0.52–3.23, 3.98–6.82, 7.42–10.01 and 10.91–13.58s. The listener said v2.3's third phrase sounds wrong. A trial keeps 25% of the v2.3 air treatment there; a safe control completely restores D/Max. Both keep v2.3 for phrases two and four. D/Max remains immutable and approved; neither trial is approved.

For validation, check per-phrase consonant (4.5–7.9 kHz), air (9–14 kHz), onset integrity, correlation, null residual, overall loudness and true peak against the combined target. For Skell Preset/AdlibLab, replace this offline same-take renderer with verified portable, causal DSP and test on an entirely new recording; run real FL Studio, CPU, latency and compatibility tests before release.
