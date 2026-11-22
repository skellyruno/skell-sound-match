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

## WAV-only standalone source-to-effects reconstruction (2026-11-22)
The owner confirmed **Speakerz and Hop Out original FL Studio presets and projects are unavailable**. Treat this as an expected source-only reverse-engineering workflow, **not a blocker**. The previously uploaded dry/main/stage WAV prints are sufficient to fit and test offline approximate processing. All original WAVs remain private and untouched.

**Implemented and verified locally (private package `SKELLY_WAV_ONLY_PRESET_RECREATION_2026-11-22.zip`):**
- Extracted independent causal stereo echo kernels: Hop Out first echo **779.229 ms**, Speakerz **932.404 ms**, both three echo groups and separate L/R weights.
- Fit regularized linear wet-only FIRs for reverbs plus partial static approximations of Speakerz convolution and Flangus; LTI regularizer mode chosen by **inner-validation within the training section**. Outer evaluations are separate later portions of the *same* performances, previously examined during exploratory development, **not blind independent-take evidence**.
- Relative wet residual RMS error of fitted stage versus **no effect (1.0 baseline)** on later sections: Hop Out DEL **0.4375**, REV **0.1487**; Speakerz DEL **0.3795**, REV **0.3204**, convolution **0.5221**, partial Flangus **0.6701**. **Hop Out CHORUS 1.0271 and direct ALL 1.0809 failed** and are explicitly omitted from the selected standalone chain; do not report these as successful matches.
- Frozen **original-dry-input** offline Speakerz/Hop Out chains use earlier train-fitted 8-band EQ and stereo-linked leveler, plus learned FX and train-only mixer gains. On exploratory later same-take windows, against the total desired effect print: Speakerz seven-band RMS-matched spectral MAE **1.428 dB**, 200ms envelope MAE **1.130 dB**; Hop Out **2.347 dB** and **0.835 dB** (chorus still missing).
- Created a standalone **apply-preset** program that needs only new dry audio, a saved JSON recipe and its fingerprint-checked NPZ models: **no original target, plugin preset or FLP is required at application time**. 44.1 kHz matched models, effectively mono input guard, conservative 4× estimated true peak and no overwrite. Reapplying both base chains and Speakerz widened reproduced the original generated PCM **bit-for-bit**.
- Created matched-loudness private A/B excerpts and 24-bit FLAC preview renders; **15** selected output FLACs re-decoded, had finite stereo samples, and passed the conservative 4×-estimated true-peak guard. The extracted ZIP passed CRC and per-file SHA-256 checks. **23/23 local Python tests passed again from the fresh extracted ZIP**, and the extracted Speakerz recipe replay was bitwise equal. These are offline tests, NOT Windows VST3, FL Studio, Quick4, processor/UI or CPU/latency validation.
- The learned NPZ audio models and private A/B clips remain only in the user's private downloadable chat ZIP; **do not publish or copy those derived models or original vocal snippets into public Git** without owner authorization. No production factories/parameters were changed and no unverified work was merged.

**Next actual DSP bottlenecks:** solve time-variable Hop Out chorus and Speakerz Flangus rather than falsely using a static IR; verify the recipes on a different vocal take; then port compact causal, RT-safe algorithms into opt-in native Skell Preset trials with accurate host/FL Studio/UI validation. Preserve Deuce offline v2.5 and factory 46 trial, Alchemist factory 43, the historical 55 program identities and existing My Presets.

## Club adlibs and Speakerz FST evidence (2026-11-22)
The newly supplied PRIVATE `club.zip` has **four FL Studio .fst files, one .flp, and seven 44.1 kHz / 24-bit / stereo WAV prints** from the same 11.971 s source. Do not include these binaries or owner-derived learned filter models in public Git. Safe generic effect-name parsing is now in `wav_only/flstudio_preset_catalog.py`, available as `skelly_bulk_match fst-catalog`. Chain names/order are evidence only; exact third-party knob and bypass states are not reconstructed.

- **Angelic Adlib**: original FST names include Fruity Chorus, two Parametric EQ 2, Fruity Limiter, Maximus, Fruity Compressor, Soundgoodizer, Fruity Delay Bank, Fruity Flangus and Fruity Reeverb 2. Both with-delay and no-delay same-source exports exist. Static main trial heldout spectral MAE **6.53→2.00 dB**, envelope **4.24→2.96 dB**. A measured ~0.928 s echo exists but a sparse static-stereo-delay trial performed worse on heldout wet residual and was rejected.
- **Muffle Adlib**: Fruity Love Philter, two EQs, Fruity Compressor, Soundgoodizer, Fruity Convolver, Fruity Flangus, Fruity Reeverb 2, Fruity Delay 3. Static main trial heldout spectral **7.47→3.58 dB**, envelope **3.94→2.85 dB**.
- **Wobbly Adlib**: three EQ 2 instances, Fruity Limiter, Soundgoodizer, Fruity Chorus, Fruity Flanger, Fruity Phaser, Fruity Convolver, Fruity Wrapper, Panagement 2. Static EQ+linked leveler trial improved tone **4.32→2.60 dB** but **worsened envelope 2.15→2.48 dB**. Do not promote; a time-varying modulation model is required.
- **Zaam Adlib**: Fruity Chorus, two EQs, Fruity Limiter, Soundgoodizer, Fruity Flangus, Fruity Reeverb 2, Fruity Delay 2. Static main trial heldout spectral **8.97→3.34 dB**, envelope **5.98→5.27 dB**.
- **Club noise gate reference**: club raw→club gate. A standalone causal stereo-linked gate fit (train first section, evaluate later on the same take) selected threshold **−46 dB**, attack **2 ms**, hold **25 ms**, release **40 ms**, hysteresis **4 dB**; heldout envelope MAE **19.26 dB ungated → 2.18 dB**. The gated reference also has ~**+1.65 dB of open-vocal makeup**, which the gate itself must **not** silently apply to every preset.
- **Speakerz screenshot**: visible slots in order: Parametric EQ 2, DeEsser Stereo, EQ 2, Fruity Compressor, Soundgoodizer, Fresh Air (green/on); Fruity Reeverb 2, Fruity Flangus, Baby Comeback, Fruity Convolver (dark/off in capture). EQ UI labels include approx 56 Hz −16.9 dB, 1.5 kHz +2.2 dB, 8 kHz +1.0 dB. This is screenshot-state evidence, not the entire automation/mix history.
- **Skell Preset integration**: [draft PR #94](https://github.com/skellyruno/skell-preset-vst/pull/94) appends an independent MIC Noise Gate page/automation and calibrates its newly selected factory preset defaults to the Club gate; old host states and native packages remain gate-OFF. No production preset has been changed yet.

Four Club adlibs are **additional targets** beside original Deuce/Alchemist and newer Hop Out/Speakerz (eight total). All new audio trials are private and unapproved. The external host, local Quick4 screenshots and exact-head Windows VST3 still require verification.

## Frozen decisions
- Main Vocals user-visible choices: Alchemist (43) and Deuce (46), only.
- Factories 0–54, host APVTS/automation IDs, original old presets, imported My Presets and startup rack behavior stay compatible.
- Deuce offline v2.5 is the preferred listening target; neither the independent transfer nor the factory 46 native approval is established.
- Do not merge PR #89, #8, or Sound Match #2 solely from this metadata audit.
