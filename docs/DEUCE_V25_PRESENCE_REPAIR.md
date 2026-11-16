# Deuce v2.5 — Presence Repair (listener-preferred offline experiment)

**Listening decision (2026-11-15):** The owner auditioned the six-way, lossless, same-take 15-second A/B player and explicitly said **“v 2.5 sounds better.”** v2.5 replaces v2.3/D/Max as the **preferred offline reference sound** for future Deuce work. The protected **D/Max** remains the rollback baseline. This does **not** make v2.5 a verified Skell Preset Windows VST3 preset or prove that it matches on a different take. Original WAVs, previous renders, FST files, automation IDs and saved preset states were not changed.

## Motivation

v2.3 improved 9–14 kHz air but softened 4.5–7.9 kHz consonant presence, especially around the third phrase (about 7.4–10.0 seconds). v2.4 Gentle and Safe applied phrase-specific corrections; those timings are not a portable audio algorithm. v2.5 instead uses one continuous, causal, candidate-only correction with **no reference or phrase lookup during rendering**.

## Offline signal path

This stage runs **after** the v2.3 Sustained Air candidate, **not** on the dry vocal and **not** as a substitute for the REC→MAIN processing chain.

- Peaking EQ: RBJ biquad, 7,000 Hz, Q 0.75, +0.75 dB.
- Fixed output trim: −0.1467149783536854 dB, calibrated against D/Max level using the first 4.8 seconds.
- Filter parameters selected using 0–4.8 seconds of the 44.1-kHz reference take only; subsequent phrases were evaluated later, but are still from the **same performance**.
- Causal filtering, persistent filter state across blocks, no lookahead or phrase timestamps. Python/SciPy processing is **offline research** and is not audio-thread safe.

## Same-take measurement (dB error; lower means closer)

Active-frame mean absolute STFT band-level error, 2048-sample frames, 512-sample hop. This metric is not a general perceptual quality rating.

| Segment / version | 4.5–7.9 kHz | 9–14 kHz |
|---|---:|---:|
| 0.4–4.8s D/Max | 1.150 | 1.840 |
| 0.4–4.8s v2.3 | 1.284 | 1.282 |
| 0.4–4.8s v2.5 | **1.093** | **1.212** |
| 7.4–10.0s D/Max | 0.863 | 1.783 |
| 7.4–10.0s v2.3 | 1.140 | 0.839 |
| 7.4–10.0s v2.4 Gentle | 0.912 | 1.467 |
| 7.4–10.0s v2.5 | **0.892** | **0.809** |
| 11.0–14.0s v2.3 | 1.227 | 0.948 |
| 11.0–14.0s v2.5 | **1.041** | **0.913** |

Full 15-second trial: -19.9985 LUFS and approximately -4.03 dBTP (4x oversampled), 44.1 kHz 24-bit stereo FLAC. These are measurements of the offline trial, **not native VST3**.

## Verification status

- **Owner listening:** v2.5 preferred in the six-way synchronized comparison; not a blind ABX.
- **Local Python:** 21 of 21 tests pass after adding frequency-response/stability and mono/empty-buffer coverage, across 44.1/48/96 kHz for the parameterized tests.
- **Real source check:** re-rendering the archived 15-second v2.3 comparison through this module matches the existing 24-bit v2.5 audio render within file quantization (MAE 2.63e-8; max 5.97e-8).
- **Previous browser check:** lossless tracks load, synchronized switching and third-phrase looping work, Chromium console had zero script errors.
- **Not verified:** entirely different Deuce performance with same REC→MAIN target; Skell Preset native implementation; Windows VST3; FL Studio; CPU/latency; preset/state recall; real-time thread safety; long-session A/B.

## Reproduce

```bash
python -m skell_sound_match.deuce_presence_repair prior_v23.flac new_v25.flac
pytest -q tests/test_deuce_presence_repair.py
```

Output refuses overwrites and refuses nonfinite or clipping rendered samples. Do not commit original/private vocal recordings.

## Promotion gate

1. Process a **different dry vocal performance** through the established Deuce REC→MAIN target chain. Apply this fixed correction to its v2.3 candidate **without refitting**. Measure, level-match and listen for sibilance, consonants, metallic artifacts and transients.
2. Port the causal filter to Skell Preset C++/JUCE with no audio-thread allocations; verify identical impulse/frequency and real-audio outputs, parameter/state compatibility, CPU and latency.
3. Build/test actual Windows VST3, FL Studio, preset save/restore and previous project compatibility. No automatic replacement of factory preset IDs or the D/Max rollback.
