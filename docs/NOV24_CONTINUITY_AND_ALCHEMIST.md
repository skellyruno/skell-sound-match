# Nov 24 — cross-chat checkpoint and Alchemist continuation

Owner requests repository updates as work proceeds and preservation across chats; new audio/DSP and listening feedback expected but not yet received. Continue all nine original targets; preserve ten provisional families separately. No new vote inferred.

## Verified exact repository checkpoints

- Sound Match PR #2, prior head 74da3caeeb0d310a6e65b98e96fe122903733a97, Python run 45539078346 passed.
- SkellCore PR #47 head 929c1b7f85f8d145e0e9dee3031c7197d5d0c117: portable 45529506308, Windows template 45529506386, headless JUCE 45529506352 all passed. Linux portable job 138921012670 logs confirm 20/20 tests actually executed, including tone finish, modulation and Deuce presence.
- Skell Flang PR #19 advanced in separate chat to dce069fb4f194edb8f047d3bfeec70d2ac49f0eb, Windows workflow 45536879479 passed. Private engine inclusion and host equivalence not established by workflow status alone.
- Skell Preset PR #94 head affb0faf4cc7e493b0cf2528a77a8df9365c6de9, Windows run 45328485600 passed. No wrapper edits or factory promotion in this pass.

All four were open drafts at inspection. No merge. Local pinned JUCE download failed DNS again; no Quick4 captures. Reran private Flangus adapter, Delay 2/3 and Bank/Convolver/EQ sanitizer executables with correct saved-state arguments; passed. Initial Bank test invocation without mandatory arguments failed argc assertion; corrected invocation passed 20 saved-state rate renders and invalid-input checks. Not new plugin build certification.

## Alchemist actual audio continuation

Recovered original Alchemist Factory54/55 same-take A/B ZIP, checked CRC and original SHA256SUMS for every listed member. Original 15-second native AudioProcessor renders and FL reference distinct from current owner B (7s excerpt postprocess). Original report estimated raw peaks factory54/55 -0.944 dBTP, misses -1 dBTP screen. No reclassification of old anchors.

84 bounded native high-band trials, 28 each across exact owner B and historical level-matched factory54/55. 40% train / 20% selection / 40% later same-take diagnostic. Only high-band attenuation and training-only loudness compensation; no altered dynamics or stereo. Baseline explicitly competes. All three selected unchanged baseline. Later composite owner B 4.460087, factory54 5.233732, factory55 5.229350; no diagnostic promotion. Predefined mild darker B 4.458291 vs 4.460087, below 2% improvement requirement; no guard regressions, optional experimental listening print only. Manual darker factory54/55 5.235470/5.231446, worse. Keep A/B and all old choices. The owner asked for less brightness, so retain the mild manual print separately rather than falsely claim an objective win. These are repeated historical comparisons, not independent takes or source-driven full chains.

## Durable handoff and integrity

Private file SKELLY_SOUND_MATCH_CONTINUITY_NOV24.zip (106004183 bytes) preserves 32 files plus manifest: previous research ZIPs unchanged, listening labs, original supplied C++/headers, exact owner feedback, recovered factory A/B archive, private intake manifest, new Alchemist render/metrics and scripts. Twenty original input paths and SHA256s are inventoried privately, not all raw originals embedded. All nested ZIP CRC checks and outer member SHA256 verification passed. Package not standalone build, scripts may need earlier local paths; original recordings must be retrieved and verified. Do not publish source, raw settings, IRs or vocal audio. Keep original archives as well.

New reusable public module and synthetic tests: python -m skell_sound_match.checkpoint_integrity <private archive>. Rejects missing/extra/duplicate/unsafe paths, mismatched sizes/hash and malformed schema. Verifies archive consistency, not authenticity against a replaced manifest. Twelve local pytest cases passed. The actual archive stays private; no private hashes or state contents committed.

Next: ingest new audio with original take/stage identity, source hashes, slot order/enable/mix; missing Reeverb2, Limiter/Compressor, Maximus/Soundgoodizer, other modulation and Love Philter implementations. Preserve exact Deuce recovery and all historical owner picks. Continue native shared integration only after source-specific rights and real-time tests. Do not restart or replace Skell Delay; Skellay separate.
