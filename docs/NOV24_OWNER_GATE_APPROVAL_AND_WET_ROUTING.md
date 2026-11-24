# Owner feedback ec3659f808d5f4e07046f328 and wet routing continuation

All ten feedback group IDs, reference hashes, candidate identities and candidate hashes were matched to the previous private HTML. No elimination is inferred from an empty elimination field; ties with unfavorable notes are not approval.

## Decisions
- Alchemist: both sound good, keep both; no new challenger needed this round.
- Angelic no delay: A wins (angelic-no-delay-0.35-2.0-0.6); tone roughly correct, reverb wrong. Full Angelic both bad in delay.
- Club Gate: explicit text decision "b wins lets put it in" overrides the non-reviewable card's empty vote. Listening target is club_gate-nov23-excerpt-gate-40_0.25, SHA256 d5615054f281a521f6ece8a6a463e4df3a4314b3e848ede7fffdf6a0c107cec6. A preserved.
- Hop Out: A, hop_out-nov24-adaptive-excerpt-env0.65-6, wins and close.
- Muffle: A, muffle_adlib-nov23b, wins; owner estimates 75% close, subjective only.
- Zaam: delay still needs work; no winner.
- Wobbly: B, wobbly_adlib-nov24-ir-round-actual-ir-gated-stereo-0.08, wins, convolution almost there.
- Deuce: displayed ORIGINAL was the disputed R5 original, NOT the preferred offline v2.5 recreation. Exact v2.5 render or old HTML still needed.
- Speakerz: both close; user asks slightly quieter delay.

## Next private listening lab
Session 9ac4d66bbd55d00e37c51327, 10 groups, 28 FLACs, 6 reviewable. Original and retained candidate URIs unchanged. Previous rejected/alternate renders remain archived. New source-driven experiments are not independent-take proof or production promotion. Composite diagnostic scores (lower better, not % accuracy), first/later sections:

| Target | Anchor | New | Status |
|---|---|---|---|
| Angelic no-delay | 4.114/3.740 | 4.164/3.677 | 600 ms decay, 15 ms predelay, 3 kHz damping, .15 wet; mixed result |
| Angelic full | 2.932/3.981 (rejected A) | 3.277/3.598 and 3.314/3.595 | exploratory filtered 460 ms repeat variants; earlier section regresses |
| Muffle | 7.355/5.726 | 6.958/5.690 | actual IR, lowpass 2.8 kHz, .15 added wet |
| Zaam | 3.208/3.332 (rejected A) | 2.860/2.930 | 465 ms noncrossed, .65 feedback, 5 kHz damping, .55 wet; better than last round but not all historical trials |
| Wobbly | 6.653/4.529 | 7.447/4.807 | additional 1.2 kHz lowpassed IR .04 wet regresses, exploratory only; keep owner B |
| Speakerz | 1.812/2.172 | 1.817/2.170 | 8% estimated delay cancellation, exploratory, actual delay loudness change not verified |

Speakerz isolated MAIN to MAIN+DELAY print: fit causal regularized M/S IR on prefix, waveform relative error 0.205668 to 0.151616 on later interval. Cancellation attempt on candidate uses only candidate samples and the learned filter, not original samples; may introduce combing and not identical to lowering the true delay send. Do not call it confirmed quieter. Repeated same-take diagnostic intervals are not independent.

Audio audit 28 clips, exact URI hashes, source reference preservation, rate/frame count, estimated peak -1.4999995 dBTP (24-bit rounding), max within-round LUFS spread 0.000000193. Chromium playback clock for all 28, vote/reset/skip/export and mobile overflow passed; desktop/mobile images inspected. Physical listening remains unverified. Added reusable offline filtered echo and deterministic diffuse reverb primitives with 3 tests; local focused suite 25 passed. Full branch CI separate.

## Native Club gate trial
Skell Preset draft PR #94 commit b7728fa1df6cae6e0cfdb0487becf03b3ba1b8aa includes an opt-in compile-time native test finish (default OFF). No APVTS, factory identity, preset, or production changes. Portable local C++ tests passed at 44.1/48/96/192 kHz. Offline A/B first-section scores 0.168047/0.136056; causal trial applied to A 0.154070. Existing native gate on real raw 0.435413, plus trial 0.400170; later score unchanged 0.197552. This does not yet match B. JUCE dependency check failed DNS in local environment; no full native VST3/Quick4, pluginval or FL Studio result. Separator cleanup remains optional future integration, not a modification to model separation. Do not enable the experimental build as stable.

Keep both draft PRs unmerged. Private audio, learned filters, IRs, presets, and HTML stay outside public Git. Next: focus on independently reconstructing delay and reverb routing rather than score-only searches, and recover the exact Deuce v2.5 recreation.
