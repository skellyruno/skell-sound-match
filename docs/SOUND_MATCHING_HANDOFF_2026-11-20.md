# Skelly Sound Matching — Agent Handoff
**Updated:** 2026-11-20  
**Scope:** Deuce vocal chain, Alchemist vocal chain, and the separate Skell Master / Deuce Match bus. Read this file and AGENTS.md before making changes.

## Decisions that must not be lost

- **Deuce vocal:** owner explicitly preferred **offline v2.5** on 2026-11-15 ("v 2.5 sounds better"). This is the current listening target. Keep **D/Max** as protected rollback. v2.3 and v2.4 remain historical candidates. Approval is for offline audio, **not** the current native VST3 approximation.
- **Alchemist vocal:** Hybrid v0.3 was historically owner-preferred offline. v0.7 and later refinements are experiments; latest preference is not reconfirmed. Keep native Factory 43 as protected baseline. No newer native Alchemist trial is owner-approved.
- **Main Vocals browser:** show exactly **Alchemist** and **Deuce**. Intended factory identities: Alchemist 43, Deuce v2.5 46. Imported/saved .skellpreset files belong in **My Presets**. Keep internal historical factory/program identities for host compatibility; hide trials rather than deleting or renumbering.
- **Skell Master Deuce Match is a separate master-bus project.** Do not conflate its beat-containing master reference with vocal-only Deuce REC→MAIN.
- No candidate is automatically promoted from a metric. Owner listening, source provenance, true-peak safety and native-host verification are separate gates.

## Repositories and active lines

| Workstream | Repository / line | State |
|---|---|---|
| Offline archive/tools | skellyruno/skell-sound-match, branch feature/deuce-v25-listening-approved-20261115 | PR #2 integration line; now includes the transfer audit and consolidated handoff |
| Native vocal presets | skellyruno/skell-preset-vst, branch fix/main-vocals-alchemist-deuce-only-20261120 | PR #85 draft; exact-head Windows VST3/portable CI passed; history integration still blocked |
| Mastering / Deuce Match | skellyruno/skell-master-vst, branch tune/deuce-post-limiter-makeup-2p4db-20261120 | PR #33 draft; Windows + Linux CI passed; exact PR33 owner-WAV render/listening still required |

The sound-match repository is **public**. Its archive contains owner-approved historical data. Do not add new raw vocals, FLPs, FSTs, proprietary state or unreleased audio to public Git. Preserve the existing archive and its checksums. The archived data/reports/handoff_notes.md is an earlier uploaded handoff and is retained byte-for-byte for provenance; its status claims are superseded by this document.

## Deuce vocal chain

Original FST hashes:
- rec deuce.fst: 068911190350164db40955c0f111711fecd9cc7e194d3edb35fba861fa013168
- main deuce.fst: 989b263f5b720a70b0d3cc24b1a4a6be914f6b80c599d0621f15232ff0999f17

REC: Fruity Parametric EQ 2 → Fruity Limiter → Soundgoodizer Mode A / raw amount 43 → Fruity Limiter.

MAIN: Waves REQ 6 → SSLChannel → Fruity Compressor → DeEsser → Soundgoodizer Mode C / raw 503 → empty slot → Fresh Air → C6 → PuigTec EQP1A.

Known source facts:
- REQ 6: 92 Hz +0.1 dB/Q1.41; 206 Hz -4.4 dB/Q6.5; 414 Hz -4.3 dB/Q6.5; 3,487 Hz -4.3 dB/Q6.5; 7,828 Hz 0 dB/Q0.8; 11,232 Hz +3.7 dB/Q0.9.
- Fruity Compressor: threshold -37.7 dB, ratio 8:1, attack 12.9 ms, release 200 ms, makeup +13.7 dB (screenshot-derived).
- DeEsser serialized center 5,860 Hz and threshold-like value -29.9 dB; proprietary Waves/Fresh Air physical knob mappings are not fully decoded.
- Soundgoodizer values 43 / 503 / 169 are raw serialized integers, not percentages.

### Offline v2.5 preferred sound

v2.5 is the v2.3 Sustained Air candidate followed by a frozen causal repair:
- v2.3: candidate-only 7.9–15 kHz Butterworth band conditioner; amount 0.45, threshold -12 dB, knee 4 dB, attack 35 ms, activity floor -55 dB. Fitted on 0–4.8 s of the original 44.1 kHz take.
- v2.5: RBJ peaking EQ at 7,000 Hz, Q 0.75, +0.75 dB; fixed output trim -0.146714978 dB.
- No target waveform lookup or phrase timestamps during render. Python/SciPy implementation is offline research, not real-time DSP.

Same-take 15-second metrics (lower band MAE is closer for this metric only):
- Third phrase 7.4–10.0 s: 4.5–7.9 kHz 1.140 dB (v2.3) → **0.892 dB (v2.5)**; 9–14 kHz 0.839 → **0.809 dB**.
- Full clip, analysis-only loudness matched: 4.5–7.9 kHz **1.308 → 1.105 dB**; 9–14 kHz **1.153 → 1.111 dB**.
- v2.5: -19.9985 LUFS and approximately -4.027 dBTP by 4× reconstruction.
- Six-way synchronized lossless player was exercised in Chromium: tracks decoded, switching/third-phrase looping worked, no JS errors. Not blind ABX.

### Independent-vocal checks: safety only, not a transfer match

- 88.493 s independent vocal stem: fixed presence-stage test, block/whole output identical, estimated 4× TP -0.177 dBTP (input -0.103). This **fails** the -1 dBTP release threshold; CLI must refuse output.
- 42.602 s Alchemist recording input: this is the REC-printed Alchemist source, **not untreated dry and not a Deuce performance**. Estimated -1.686 dBTP after the fixed stage (input -1.707). Numerical peak gate passes, but there is no Deuce REC→MAIN target.

**No independent Deuce performance has yet been validated against its own original REC→MAIN target.**

### Transfer audit now in repository

Added:
- skell_sound_match/deuce_transfer_audit.py
- tests/test_deuce_transfer_audit.py
- docs/DEUCE_V25_NEXT_PRIORITY_VALIDATION.md
- reports/existing_deuce_repro_audit_15s.json
- reports/independent_vocal_stress_no_reference.json

Focused local suite: **26/26 passed**. Earlier exact-head Python CI passed on commit 7eb041a (workflow #43988265267); rerun GitHub CI on the new commit before merge.

For a new test, prepare two sample-aligned files from the same genuinely new Deuce performance:
1. new_v23_candidate.wav — same new dry take rendered through the frozen v2.3 candidate.
2. new_original_rec_main.wav — that exact source processed through the original FL Studio REC→MAIN chain.

Run:

~~~powershell
python -m skell_sound_match.deuce_transfer_audit new_v23_candidate.wav --target new_original_rec_main.wav --output deuce_v25_new_take_trial.wav --report deuce_v25_new_take_report.json
pytest -q tests/test_deuce_presence_repair.py tests/test_deuce_transfer_audit.py
~~~

The target is scoring-only. Matching sample rate, frame count, channels and start offset are required. Without a target the tool reports safety only. It refuses overwrites, path collisions, non-finite/sample-clipped output and estimated 4× TP above -1 dBTP. No automatic promotion.

### Native Deuce status

Skell Preset factory 46 is a 13-stage Deuce v2.5 **Native Trial**, built on a D/Max-inspired native REC/MAIN approximation with broad corrective EQ, the +0.75 dB / 7 kHz / Q0.75 bell and output calibration. The original v2.3 Sustained Air DSP has **not** been ported. Factory 46 is not an exact offline v2.5 port or owner-approved VST3 sound. Factory 44 remains the separate D/Max native trial. Preserve all factory indices, APVTS IDs, automation IDs and host states.

## Alchemist vocal chain

Source:
- input alchemist test vocals no main effects.wav: SHA-256 115c28f87f57fb13eaafce7e3c28a0fbaaba95c86bddaa89440b3c92d453d706
- target alchemist test main effects on .wav: SHA-256 e40d6abcb9b9a111c8a3be8be3445b21726c1d8b98e6e99e5a3613d6add4adbb
- MAIN.fst: SHA-256 66077b7a4e1695ab8817b6cbe74be7f098afa1fe8fee52ac4fa3e90065359424
- both WAVs 42.602 s, 44.1 kHz stereo PCM24. Input is already REC/recording-printed, not untreated dry.

Hash-verified MAIN.fst has seven slots (PR #77 corrected an earlier six-slot inventory):
1. Fruity Parametric EQ 2
2. Fruity Parametric EQ 2
3. Fruity Limiter
4. Waves CLA-76 Stereo
5. Waves CLA-2A Stereo
6. Soundgoodizer Mode A / raw amount 169
7. Fruity Limiter

Native Fruity EQ2 vectors and proprietary Waves knob mappings remain partially undecoded. Original input measured -16.959 LUFS; MAIN target -14.255 LUFS (+2.704 LU). Target estimated 4× peak is about +0.017 dBTP; do not copy unsafe overs.

Native candidates:
- Factory 43 is the protected seven-stage approximation with module IDs [1, 26, 2, 19, 33, 5, 31]: Classic EQ low-cut → Eight-Band EQ → Fast Compressor → Smooth Compressor → Skelldizer → Saturator → Alchemist Match Finish (ID 31).
- Hybrid v0.3 is historically owner-preferred offline. v0.7 correlation about 0.979 is restricted same-take offline evidence, not a native match.
- Native diagnostics: Factory 48 lowest spectral MAE (4.155 dB); Factory 54 better loudness/dynamics balance (-14.591 LUFS vs -14.261 target, 0.330 LU quieter; spectral 4.213 dB; 20/200 ms envelope MAE 2.318/1.336 dB). Factories 52/53 had lower spectral/envelope error but were about 2.35 LU quieter. None is owner-approved.
- 20 Hz low-end sweep had little overall benefit; -1/-2 dB cuts worsened 63/80 Hz residual. No production change justified.
- PR #79 exact-head: Windows CTest 41/41, portable CTest 32/32, Python diagnostics 17 + 3 tests passed. Renders use the plugin processor's processBlock, not FL Studio/external host.

## Skell Preset integration

Current branch fix/main-vocals-alchemist-deuce-only-20261120, head 68ae71414d28cc30fa89275c1104544c000d6cef.

- PR #85 is the current integration draft; PR #84 is the two-item Main Vocals browser change on the same head.
- Exact workflow #44719941231 passed portable tests, Windows x64 VST3, strict metadata, preset ZIP import/export/security, full-rack stress, external VST3 load/audio fixture and native factory recall/audio/PDC/state. Artifacts: Windows VST3 14622058081; Alchemist renderer 14622427347.
- Main Vocals shows only Alchemist (43) and Deuce (46). 55 internal factory identities (indices 0–54) remain; trials are hidden rather than deleted. My Presets remains separate.
- PR #85 is blocked by five production-main commits not reconciled into the development line. PR #86 tracks the delta and is itself dirty. Do not force-merge or discard production commits.
- PR #87 ports optional SkellWorld presence into Settings; exact Windows workflow #44720704961 passed. Still draft. Integrate without changing audio/DSP state.

## Skell Master — separate Deuce master-bus project

Source:
- deuce w beat.wav: SHA-256 38d3a4c82c640b5ed24ee5b61ec04ab33c80717618e1b97fe845a590e85da484
- deuce my master preset.wav: SHA-256 cfad397db8807f68b1b513653487721bdcb0daa7f3d5d204b9370f26c0b8b429
- master.fst: SHA-256 dcdb0f487b612e61c293bda574168188117c3b42b907428133f1e048c39d9e11
- 18.750 s, 44.1 kHz stereo PCM24. Input is beat-containing and vocal-REC processed; this is master-bus matching, not vocal-only Deuce.
- master.fst: API-2500 → Vitamin → L2 → API-550A. Vitamin crossovers 90/500/2,594/9,310 Hz; L2 threshold -2.8 dB, ceiling -1.1 dB, ARC on; post-L2 API-550A +2 dB around 5 kHz is screenshot-derived. Proprietary mappings are not fully decoded.
- Owner target is unsafe at about +2.5 dBTP. Match character/envelope/spectrum, not overs. Full-source target is about 31–32 samples (0.70–0.73 ms) later. A 294-sample offset in a later PR note is for a baked 15-second preview only, not the full WAV pair.

Current line: PR #33, branch tune/deuce-post-limiter-makeup-2p4db-20261120, head b072fd3554f494b7b23997e2dc84d39dced56ceb, stacked on PR #32.
- PR #32 true-peak guard: 257-tap / 4-phase Kaiser detector, 32-sample lookahead, stereo-linked gain, 85 ms release; margins 0.50/0.45/0.40 dB at 44.1/48/96 kHz. Independent 16× broadband checks passed; 96 kHz 20 kHz sine about -1.40 dBTP.
- PR #32 exact owner render: -9.995 LUFS, -1.443 dBTP, sample peak -1.500 dBFS; 5.27% one-core CPU; 105 samples latency, 1,024 tail frames. After alignment and attenuation-only match, 5-band spectral MAE 0.1879 dB; 20/50/200/400 ms envelope MAE 0.940/0.649/0.428/0.348 dB. This is PR32 binary, not PR33.
- PR #33 adds +2.4 dB smoothed post-limiter makeup only when Deuce Match is enabled; 12 ms mode smoothing; default/off and bypass unity; final TP guard downstream; no new parameter ID/factory value.
- Exact workflow #44706117830 passed Windows build/CTest/pluginval and Linux VST3/renderer build + hosted tests. Artifacts: Windows VST3 14615646988; Linux renderer 14615013106.
- PR33 still needs exact full owner-WAV render, full-source 31–32-sample alignment, independent 16× TP verification at -1 dBTP or lower, fresh synchronized A/B and owner listening. FL Studio session/automation recall is unverified.

## Next work, in order

1. Deuce transfer: obtain a genuinely new Deuce performance with the same source exported dry, through frozen v2.3, and through original FL Studio REC→MAIN. Run the transfer audit without refitting. Do not substitute the Guwop stem or Alchemist REC-printed input.
2. Native Deuce: port full causal v2.3 Sustained Air + v2.5 presence to C++ only after transfer evidence; persistent state, no audio-thread allocations/locks/file I/O. Keep factory 46 trial until verified.
3. Alchemist: use current Factory 43/48/54 renders; verify seven-slot source chain/routing; audition against owner MAIN target. No promotion without owner listening.
4. Skell Master: render exact PR33 binary against full owner input; verify TP, LUFS, spectrum/envelope, latency and CPU. Never copy positive target TP.
5. Integration: reconcile five production commits through PR #86, preserve PR #87 opt-in presence, rerun exact-head CI, review PR #85. Do not merge unverified branches.

## Preserve / do not do

- Never overwrite owner WAVs, FSTs, v1.3A/v1.4 protected Deuce history, D/Max backup, Alchemist v0.3/v0.7 history or FL Studio projects.
- Do not call v1.4 contour, v2.3 alone, phrase-specific v2.4, Factory 45/47–54 or current native v2.5 trial approved replacements.
- Do not convert Soundgoodizer raw 43/503/169 into percent or infer undocumented Waves XML knob mappings.
- Do not renumber factory/APVTS/automation/rack-slot IDs, VST3 identity or saved state.
- Do not claim exact proprietary emulation, blind ABX, independent Deuce transfer success, FL Studio approval or certified true peak without those tests.
- Keep new raw recordings and FST/FLP files out of public Git. Existing public archive assets are owner-approved; retain them and checksums.

🩻