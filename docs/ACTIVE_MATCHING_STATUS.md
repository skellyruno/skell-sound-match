> **Round 3 update (2026-11-22):** Owner requires ORIGINAL outside candidate voting and notes that stereo Speakerz is **not close**, while Club Gate candidate A is **very close** to original B (raw C is not a recreation). The public lab generator now uses reference-only playback, 1–5 similarity rating for single-candidate rounds, issue tags, and a `--remix` mode that reuses all existing private encoded clips. The new private Round 3 HTML has 13 rounds/38 audio clips, with the extra Speakerz presence/air trial; seven-band same-take held-out spectral MAE improved 1.374 → 1.181 dB, NOT independent-take or owner approval. See [full second-round feedback and Round 3 gates](ROUND3_FEEDBACK_AND_PRIORITIES_2026-11-22.md). No owner audio/filters in public Git. Latest exact-head GitHub CI remains to be confirmed.

# Skelly Sound Match — active status / compact handoff

**Updated:** 2026-11-22. **Primary repository:** `skellyruno/skell-sound-match`, draft PR **#2**, branch `feature/deuce-v25-listening-approved-20261115`. Native Skell Preset gate remains in its separate draft PR **#94**. This file is the latest compact work-in-progress status; the historical handoff and source audits remain preserved rather than overwritten.

## Current listening feedback and latest page (2026-11-22)

Read [Round 2 feedback, blind-letter mappings and priorities](ROUND2_FEEDBACK_AND_PRIORITIES_2026-11-22.md) before tuning a candidate. The new HTML generator can append clips without recompressing old audio, restarts switching versions from 0:00, safely scopes the saved votes to a session, and has too-close-to-call, a quick-jump navigator and a review counter. A new `--externalize` mode creates an offline lightweight HTML plus local FLAC asset folder, avoiding repeated 68 MB page parsing; both formats preserve the same session and exact clips. A **private** expanded lab with 12 groups (Deuce, Alchemist, Speakerz, Hop Out, Angelic, Muffle, Wobbly, Zaam, MIC Gate) was generated and checked. No private audio or FST/FLP/NPZ filters were added to public Git. Do not treat user uncertainty as a positive audio endorsement.

## Verified baseline / preservation

- Skell Preset production PR **#88 merged 2026-11-21**, preserving 55 factory IDs **0–54** and stable host automation IDs. Main Vocals browser still shows **Alchemist index 43** and **Deuce index 46**. Imported/saved user presets remain in My Presets. Open draft factory **55** in Preset PR #89 is a hypothetical **56th** internal program, NOT an approved production sound.
- Sound Match public PR #2 contains the offline Deuce/Alchemist research archive, bulk WAV-only matcher, private external recipe support, FST chain scanner, blind pairwise A/B preparation and source-only Speakerz/Hop Out analysis. **No new private vocals/FLP/FST/NPZ filters** should be published to the public branch.
- **New:** `html_listening_lab.py` and synthetic browser/test coverage produce a privacy-contained single HTML A/B lab for arbitrarily many same-take variants. Generated HTML embeds private audio and MUST stay outside public Git.

## Vocal targets and quality gates

| Target | Current reference and candidate status | Main limitation / next action |
|---|---|---|
| **Deuce** | Owner-preferred offline v2.5 is protected. D/Max rollback preserved. New blind HTML includes original/D-Max/v2.3/v2.4 historical MP3 clips plus an EQ-finishing-only experiment. | **Not** a verified full native v2.5; native v2.3 Sustained Air stage and a genuinely new-performance paired original REC→MAIN target are still needed. Do not confuse historical MP3 with lossless approved v2.5. |
| **Alchemist** | Factory 43 baseline protected. Archived original FL, older native and later compiled native comparisons. A new post-render EQ/dynamics experiment regressed on held-out metrics. | Ask owner to choose preferred sound from blind A/B; then refine current exact-head factory with same-performance, gain-matched references. Do not promote the regressed trial. |
| **Speakerz** | Original screenshot evidences active: EQ2, DeEsser Stereo, EQ2, Fruity Compressor, Soundgoodizer, Fresh Air; later reverb/flangus/delay/convolver effects are visually bypassed in the capture. Nine stage WAVs and standalone dry-input EQ/dynamics/delay/reverb approximations are available privately. | Use screenshot only as *ordering/active-state evidence*, not exact plugin knob data. Compare main, full, and +47% stereo separately; complete modulation/level/peak safety and independent-voice A/B. |
| **Hop Out** | Six stage WAVs, first strong delay ~779 ms, approximated standalone dry-input main/effects. | Chorus and full-chain single LTI modeling failed held-out tests; model chorus as time-variable, audition at matched LUFS on new vocal. |
| **Club Angelic, Muffle, Wobbly, Zaam** | Four original `.fst` chains plus paired Club RAW/GATE WAVs and source project recovered privately. Separate gate estimate. | Wobbly EQ/dynamics worsened envelope; Angelic delay attempted model failed. These are experimental until listened/validated. Native mic gate is a draft, not yet production. |

## Listening milestone 2026-11-22

- Private, single self-contained HTML: **7 groups / 23 FLAC versions**, estimated true peaks checked against −1.2 dBTP (4× reconstruction). Render and browser functionality were tested with synthetic UI fixtures; actual owner listening remains pending.
- Seven comparisons: Deuce historical vocal; Alchemist historical vocal; Speakerz main-only; Speakerz full; Speakerz stereo; Hop Out main-only; Hop Out full.
- Each group supports synchronized blind switching, best/worst vote, free notes, optional reveal, copy, and JSON feedback export. The original WAVs, converted clips and the resulting HTML are **never pushed publicly**.
- Local synthetic generator unit tests passed; keep *exact-commit GitHub CI* separate. Real Windows VST3, Quick4 JUCE editor captures and FL Studio session replay are **unverified** for the offline matcher.

## Next short loop (keep branch/PR count low)

1. User auditions the HTML and returns winners/losers or feedback JSON. Tag owner preferences as **USER-REPORTED**, not measurement-based champion until correlated with objective QA.
2. Fix biggest *identified* DSP differences (Deuce full v2.3 presence, Alchemist dynamics, Speakerz compressor/de-esser/stereo, Hop Out modulated chorus). Freeze a new candidate per preset, never overwrite an approved reference.
3. On each new audio ZIP: scan, SHA-256 dedupe, group by recording; check same-take dry/processed alignment and provenance; run fit/holdout on unmodified audio; prepare private HTML A/B; run independent-take transfer when possible.
4. Update **this** status register plus `docs/BULK_MATCHER.md`, source/provenance reports and PR #2. Batch code changes, keep PR #2 in draft, do not merge without CI and listening. Keep Skell Preset DSP/native changes separate under the current gate PR #94 or one future consolidated draft when justified.

**Rules:** preserve ALL original file versions and 55 factory identities. Never push raw owner audio, original project/preset binaries, protected source, embedded-audio HTML, private training models or evaluation-only performance waveforms to public GitHub. Never claim perfect match or release-ready VST3 based on offline numeric metrics alone.
