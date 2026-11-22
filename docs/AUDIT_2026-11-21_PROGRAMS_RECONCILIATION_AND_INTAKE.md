# Skell Preset + Sound Match — reconciliation and private audio intake
**Audit date:** 2026-11-21
**Source of truth:** [Skell Preset factory registry](https://github.com/skellyruno/skell-preset-vst/blob/main/Source/chain/FactoryPresets.h) (read blob SHA `e53e785079a2a6528fa02fb9a3e7b6e7629a1041`), [processor](https://github.com/skellyruno/skell-preset-vst/blob/main/Source/PluginProcessor.cpp), [Sound Match handoff](SOUND_MATCHING_HANDOFF_2026-11-20.md).

## What has been reconciled (verified from GitHub)
- [Skell Preset PR #88](https://github.com/skellyruno/skell-preset-vst/pull/88) **merged into main on 2026-11-21**, preserving production history and bringing current UI/DSP and opt-in SkellWorld presence. Its exact development head `106b36e4849c3977793fc98795b066af37275393` had successful portable-DSP and Windows-VST3 workflows (runs 44807369768 and 44807369802). A passing build is not an FL Studio host/audio A/B result.
- Old conflicting [PR #85](https://github.com/skellyruno/skell-preset-vst/pull/85) and [PR #86](https://github.com/skellyruno/skell-preset-vst/pull/86) are **closed and unmerged**, superseded by #88. Do not reopen or merge them.
- [PR #87](https://github.com/skellyruno/skell-preset-vst/pull/87) merged the opt-in presence port into the newer Settings-panel integration line; #88 carried that work into main.
- On current `main`, the factory registry declares **55 stable factory IDs, 0–54**; all 55 names are unique. Catalog bank declarations: **30 Main Vocals / 17 Adlibs / 8 Vocoding**. Those are internal bank labels, **not** the visible preset-browser contents.
- The Main Vocals browser displays only **Alchemist** (factory 43) and **Deuce** (factory 46); personal native `.skellpreset` files remain in **My Presets**. The host also has distinct **Empty Rack** and **Custom Rack** identities; they are not two additional factory definitions.
- [PR #89](https://github.com/skellyruno/skell-preset-vst/pull/89) is **open draft**, adding experimental factory **55** (56th entry) if eventually integrated. Its exact-head portable and Windows workflows passed (runs 44816061130, 44816061157), but it is **not** on main, does not have owner-approved audio, and its branch diverged from main (4 ahead, 2 behind at audit); do not merge or promote it without reconciliation and listening/host tests.
- [PR #8](https://github.com/skellyruno/skell-preset-vst/pull/8) is separate historic shared-AdlibFX development; it is not part of the consolidated #88 production baseline. Verify its module IDs/CPU/realtime/UI independently.
- [Sound Match PR #2](https://github.com/skellyruno/skell-sound-match/pull/2) remains a **draft** integration of archived research, recipes, and frozen Deuce v2.5 transfer audit. Its exact-head workflow 44794369411 reported success on Ubuntu and Windows. **Do not publish new recordings, FST/FLP binaries, or proprietary state to this public repository.**

## 55 frozen factory program identities (production main)
ID is the persistence key. Friendly browser/host names for 43 and 46 are **Alchemist** and **Deuce**, while the internal factory strings remain unchanged. Hidden trials and vocoder experiments are historical program definitions and must not be deleted, reordered, or automatically exposed in Main Vocals.

| ID | Internal factory name | Catalog bank |
|---:|---|---|
| 0 | Clean Lead | Main Vocals |
| 1 | Dark Trap Lead | Main Vocals |
| 2 | Airy Pop | Main Vocals |
| 3 | Gritty Rap | Main Vocals |
| 4 | Warm R&B | Main Vocals |
| 5 | Bright Radio | Main Vocals |
| 6 | Bedroom Intimate | Main Vocals |
| 7 | Aggressive Hook | Main Vocals |
| 8 | Demon Adlibs | Adlibs |
| 9 | Ghost Echo | Adlibs |
| 10 | Radio Adlib | Adlibs |
| 11 | Wide Stack | Adlibs |
| 12 | Stutter Throw | Adlibs |
| 13 | Alien Pulse | Adlibs |
| 14 | Whisper Trail | Adlibs |
| 15 | Distorted Shout | Adlibs |
| 16 | Robot Chorus | Vocoding |
| 17 | Harmony Pad | Vocoding |
| 18 | Talkbox Glide | Vocoding |
| 19 | Neon Droid | Vocoding |
| 20 | Chrome Choir | Vocoding |
| 21 | Digital Formant | Vocoding |
| 22 | Phase Broadcast | Vocoding |
| 23 | Spectral Glow | Vocoding |
| 24 | Skell Vocal Polish | Main Vocals |
| 25 | Skell Live Lead | Main Vocals |
| 26 | Broadcast Throw | Adlibs |
| 27 | Digital Bones | Adlibs |
| 28 | Three-Band Silk | Main Vocals |
| 29 | VoxRack Velvet | Main Vocals |
| 30 | VoxRack Chamber | Adlibs |
| 31 | Wide Choir Adlib | Adlibs |
| 32 | Phantom Sweep | Adlibs |
| 33 | Alien Ring | Adlibs |
| 34 | Rider Ready | Main Vocals |
| 35 | Ducked Echo | Adlibs |
| 36 | Skell Flutter | Adlibs |
| 37 | Eight-Band Air | Main Vocals |
| 38 | Opto Punch | Main Vocals |
| 39 | Smooth Edge | Main Vocals |
| 40 | Noise Guard | Main Vocals |
| 41 | Formant Sketch | Adlibs |
| 42 | Studio Six | Main Vocals |
| 43 | Alchemist (Native Preview) | Main Vocals |
| 44 | Deuce D/Max (Native Trial) | Main Vocals |
| 45 | Alchemist Refined (Trial) | Main Vocals |
| 46 | Deuce v2.5 (Native Trial) | Main Vocals |
| 47 | Alchemist Peak Guard (Trial) | Main Vocals |
| 48 | Alchemist Tone Match (Trial) | Main Vocals |
| 49 | Alchemist Lighter Dynamics (Trial) | Main Vocals |
| 50 | Alchemist Fast Compressor Blend (Trial) | Main Vocals |
| 51 | Alchemist Smooth Compressor Blend (Trial) | Main Vocals |
| 52 | Alchemist Serial Dynamics (Trial) | Main Vocals |
| 53 | Alchemist Low-End Contour (Trial) | Main Vocals |
| 54 | Alchemist Serial Dynamics Blend (Trial) | Main Vocals |

## Unresolved release / correctness gates
1. **Deuce**: owner prefers offline **v2.5**; the live factory 46 is still a native approximation lacking the full v2.3 Sustained Air stage. D/Max stays rollback. No valid *independent* new-performance original REC→MAIN target pair has been verified. Do not promote merely because the same-take metrics improve.
2. **Alchemist**: preserve factory 43, all seven original MAIN.fst effect slots, and historical trials 44–54. New candidates need aligned owner-WAV renders, independent peak checks and synchronized listening before promotion.
3. **Windows/host**: real FL Studio state recall/automation, hosted third-party plugins, actual audio A/B, CPU/latency on release hardware, local Quick4 current-editor screenshots and visual inspection remain distinct gates. Production integration does not imply those tests passed.
4. **Licensing**: Skell Preset README describes a Studio Chorus port from GPL-3.0-or-later code; resolve compliant release packaging/source obligations before commercial/public distribution. Also review the provenance and public-access scope of historical Sound Match archive artifacts before merging PR #2.
5. **PR hygiene**: preserve every source/host identity and successful work. Keep unverified work draft. No force merge, no history rewrite, and no automatic experimental preset promotion.

## Four separate vocal reference collections (user clarification 2026-11-22)
The owner is building **four distinct vocal sound-matching targets**, not one interchangeable dataset. Keep each performance/chain's original dry, REC, MAIN, FX-only, full-wet, trial, and preset evidence labeled separately. Do not compare across songs as if they were same-take dry/wet pairs.

| Target | Intake status | Scope and verification |
|---|---|---|
| **Deuce** | Existing archive/research | Original Deuce REC→MAIN references and offline v2.5 preferred sound. Native Skell Preset factory 46 remains a trial; a *new independent Deuce performance* transfer pair is still needed. |
| **Alchemist** | Existing archive/research | Original seven-slot MAIN.fst and REC-printed/main processed reference. Factory 43 protected. Separate historical controlled trials are not owner-approved. |
| **Speakerz** | New upload, 2026-11-22: `sound matching.zip` | Nine WAV stage prints (dry/main and effect variations), reported 24 s stereo PCM24/44.1 kHz. Identified as its *own* target, not an independent Deuce test. Uploaded audio remains private. |
| **Hop Out** | New upload, 2026-11-22: `HOP OUT MAIN REV.zip` | Six WAV stage prints (dry-main, delay, reverb, chorus, combined variations), reported 51.4 s stereo PCM24/44.1 kHz. Identified as its *own* target, not an independent Deuce test. Uploaded audio remains private. |

**Intake convention:** register each as `target_id` = `deuce`, `alchemist`, `speakerz`, or `hop_out`, with `take_id`, `stage_role`, `source_zip`, SHA-256, format, exact sample count, alignment, and source-provenance confidence. Do not confuse separate per-effect exports with the original full MAIN reference. Claim stage matching only for verified same-performance pairs; reserve owner approval for actual auditioned, native plugin candidates.

The November 22 Speakerz/Hop Out upload measurements come from a separate private analysis and have not been incorporated as raw files into this public repository. They do not establish Deuce v2.5 generalization.

## Incoming files — private, repeatable intake protocol
- Accept **batches of ZIPs or directories** containing WAV/FLAC, FLP, FST, Skell Preset packages, screenshots and optional project notes. Inspect in a private workspace. Never add raw vocals, proprietary states, original FLPs, or binary presets to the public repository by default.
- Enumerate archive members with size/decompression guards; compute SHA-256 for every retained candidate; index nested archives and embedded offline-player audio with their origin paths. Reuse cached evidence by content hash and record prior run provenance.
- Label dry, REC-printed, v2.3 candidate, v2.5 trial, and original REC→MAIN references separately. **Filename and player caption alone do not verify provenance**. Reject cross-song/cross-performance scoring and record missing provenance as **UNVERIFIED**.
- Group by performance/session and pair only after same source, channels, sample rate, count/start offset and synchronization are established. Measure time alignment explicitly. Preserve source audio untouched.
- For each genuinely new Deuce take: acquire (1) original dry/source; (2) the same take through frozen **v2.3** (already-rendered candidate); (3) original FL Studio **REC→MAIN** processed target. Use `python -m skell_sound_match.deuce_transfer_audit candidate.wav --target original_rec_main.wav --output new_v25_trial.wav --report trial_report.json`. The target is scoring-only; the algorithm cannot refit to it.
- Analyze spectral bands, 20/50/200 ms dynamics, voice activity, sibilance, consonants, onset/transient integrity, loudness, estimated true peak and block invariance; supplement with matched-level blind/listening A/B. Keep positive and negative findings, sample identities and conditions in report JSON. A true-peak estimate is not certification.
- Preserve original recordings and manifests, compare incremental batches by SHA-256, and use separate **CONFIRMED / USER-REPORTED / PLANNED / IN PROGRESS / UNVERIFIED / BLOCKED** statuses. Never infer an exact proprietary plugin setting from serialized raw numbers.

## Experimental four-target audio matching update (2026-11-22)
**Local evidence only — no audio uploaded to this public repo, no released/native plugin modified.**

- **Speakerz (new 24-second same-take source→main pair):** 8-band bounded static-EQ candidate + stereo-linked original causal envelope leveler. Fit on 1–9 s, evaluate without parameter refit on disjoint 11–21 s. Held-out average 7-band spectral MAE changed **2.830 → 1.297 dB**; 200 ms envelope MAE **2.504 → 1.326 dB**. Final PCM24 preview independently re-decoded; measured 4× reconstructed peak approximately **−1.2 dBTP**, not BS.1770 certification. The reference itself exceeds a conservative peak ceiling; the safe preview cannot automatically match its loudness.
- **Hop Out (new 51-second prints, active vocal primarily first 15 s):** fit on 0.7–6.5 s, disjoint evaluation 8–14.5 s. Held-out 7-band spectral MAE **5.533 → 2.159 dB**, 200 ms envelope MAE **2.022 → 0.864 dB**. Safe PCM24 preview 4× reconstructed peak approximately **−5.08 dBTP**. Hop Out's isolated REV/DEL/CHORUS/ALL variants remain *unmatched* by the dry-main tone/dynamics trial.
- **Alchemist:** archival 2026-11-14 compiled three-way lossless 15 s A/B establishes historical target/earlier/newer native renders, *not* current factory 43 exact-head evidence. In the later 5–15 s excerpt, earlier compiled vs original measured **0.670 dB band MAE / 1.740 dB 200 ms envelope MAE**, later compiled vs original **0.812 / 1.156 dB**, illustrating tone/dynamics tradeoffs rather than a universal winner. Preserve Factory 43 and owner reference; no promotion.
- **Deuce:** historical embedded 15-second player compares original to v1.4 in lossy OGG, *not* the owner-preferred v2.5, and cannot be used as a native v2.5 transfer pass. The frozen offline v2.5 and missing causal v2.3 native port remain separate. No independent new Deuce source-through-v2.3-and-original-REC→MAIN pair has been verified.
- **Local verification:** experimental Python matcher + existing intake tools passed **18/18** tests, including finite output, stereo-linked whole-vs-127-sample block equality, safety ceiling, holdout separation and no-overwrite checks. These are **not** GitHub CI, real JUCE `processBlock`, Windows VST3 or FL Studio host tests.
- **Next gates:** owner blind/matched-level listening; chain settings and same-performance reference provenance; independent performances; reproduce native causal processing/state/automation/latency/CPU; local actual-JUCE Quick4 UI inspection; Windows VST3/FL Studio validation. Do not call any one of the four presets perfectly matched.

## Frozen decisions
- Main Vocals user-visible choices: Alchemist (43) and Deuce (46), only.
- Factories 0–54, host APVTS/automation IDs, original old presets, imported My Presets and startup rack behavior stay compatible.
- Deuce offline v2.5 is the preferred listening target; neither the independent transfer nor the factory 46 native approval is established.
- Do not merge PR #89, #8, or Sound Match #2 solely from this metadata audit.
