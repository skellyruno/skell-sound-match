# Punch-in-aware matching — offline research

**Status update (2026-11-20):** earlier v2.3-only and phrase-specific v2.4 trials are historical. The owner later approved the fixed v2.5 offline chain (v2.3 Sustained Air + continuous 7 kHz presence repair). Do not present v2.4 Gentle/Safe phrase corrections as the current champion.

Some final vocals contain multiple recorded punch-in takes. Mic position, input gain, articulation and noise can change between segments even when the same REC→MAIN chain is active.

detect_regions finds candidate separated vocal activity regions using the dry source only. These are not confirmed recording edits. Verify edit boundaries in the FL Studio playlist/comp when possible. blend_regions uses approved render candidates and manually reviewed weights on active regions, with transitions only in silent gaps. It never uses reference audio during rendering and never changes the original audio. Do not reuse timestamp-specific weights on unseen takes or export them as universal plugin presets.

The historical 15-second Deuce preview covered four candidate vocal regions (offset +0.94s relative to its full take): approximately 0.52–3.23, 3.98–6.82, 7.42–10.01 and 10.91–13.58s. The user identified the third phrase as weak in v2.3; continuous v2.5 was subsequently preferred. D/Max remains the protected rollback.

For a new take, use frozen v2.3 → v2.5 without refitting and compare against that same performance through the original REC→MAIN target. Check per-phrase consonant (4.5–7.9 kHz), air (9–14 kHz), onset integrity, envelope, punch-ins, true peak and matched-loudness listening. This Python research is offline, not native VST3 DSP.