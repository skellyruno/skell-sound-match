# R6 focused sound experiments — 2026-11-22

## Scope and preservation

These trials were run **outside** the public Git repository against the owner's private aligned same-take WAV/FLAC archive. The newer Codex R5 winner audio was **not available in this container**; no owner-preferred R5 champion was overwritten or assumed recreated. The exported private R6 listening HTML has **two rounds with three candidates each** (Club gate, Speakerz full effects/stereo) and a separate original reference per round. The final HTML, source WAV, FLP/FST, fitted parameters, and derived audio are private and must NOT be committed.

R5 listening was received: Deuce C / drop A, Alchemist B-C tie / drop A, Club Gate B / drop A, Muffle A / drop B, Zaam tie / drop C, Hop Out C / drop A; Angelic/Wobbly/Speakerz have no elimination. Deuce original was reported as missing effects, so reference pairing must be repaired before native promotion. Exact R5 versions are in the preserved battle-feedback importer and results register.

## Real same-take findings

| Trial | Earlier / baseline | New R6 | Measured distinction |
|---|---:|---:|---|
| Club gate reconstructed 5 ms gain envelope absolute error (5.25 s through end) | 0.0264 | 0.0148 | ~44% lower with new fit; additional 70/30 onset-guard blend scored 0.0165 |
| Speakerz original full+47% stereo vs dry-input standalone, held-out 11–21 s RMS-loudness-matched seven-band MAE | 1.3876 dB | 0.7781 dB | ~44% lower; mid tonal shape much closer |
| Speakerz side-channel seven-band spectral MAE, same held-out window | 8.92 dB | 1.77 dB | ~80% lower side-spectrum error |
| Speakerz side/mid ratio (full clip) | −15.29 dB | −8.17 dB | Reference is −8.81 dB; level alone does NOT establish accurate stereo texture |

The Club target shows a near-constant open gain of +1.65 dB. Its R6 detector was tuned against the original gate's opens/closes on 0–5.25 s only; evaluation used 5.25 s to 11.97 s, the **same recording**. The main waveform RMS error changed only slightly despite the improved switching envelope, because differences are concentrated in quiet periods and transitions. No gain or model from the reference is injected into rendered candidate playback.

Speakerz R6 applies three bounded static EQ sections and an M/S side gain to an **earlier source-only reconstruction**, not to the original processed main. The reference is explicitly "speakerz everything + 47% stereo separated", the same processing stage and performance as the evaluated candidates. Its three versions are archived prior standalone, gentle finishing and full finishing. Static side scaling cannot synthesize missing chorus/flanger/reverb components. The trial is for listening, not for native approval.

## Verification / limitations

- Verified: 8 FLAC clips decoded round-trip; sample rates all 44.1 kHz stereo, sample-aligned within each round, LUFS equalized within each round, estimated 4x peaks no higher than −1.5 dBTP.
- Verified: actual 12.7 MB private HTML loaded into headless Chromium in-memory; reference→candidate→candidate switch resets near zero, same-letter pause/resume retains position, switching groups stops old audio, JSON exports mapped candidate IDs correctly, desktop/mobile screenshots inspected and no horizontal overflow on 390-px viewport.
- Environment limitation: direct file:/// URL navigation is blocked by browser policy; the exact HTML bytes were loaded with `page.set_content` as the fallback. End-user double-click playback on Windows was not independently validated.
- Verified: 7 local synthetic DSP audit tests passed for `stereo_finish_audit.py`. This module only contains generic DSP and measurements; all fitted parameters remain private.
- NOT VERIFIED: private R5 trial sound superiority, new independent performances, real-world audible improvement, FL Studio re-import, JUCE/Quick4, Windows VST3, realtime CPU/latency.
- Next: collect R6 winner/loser notes, then model Speakerz actual time-varying side components rather than further width multiplication. Deuce comparison reference must be repaired. Keep Angelic/Wobbly/Zaam stage recreation active even without new ratings.
