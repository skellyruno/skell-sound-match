# Deuce v2.5 — Presence Repair and current native status 🩻

**Owner listening decision (2026-11-15):** the owner auditioned the six-way synchronized 15-second lossless comparison and said **"v 2.5 sounds better."** The approved listening target is offline v2.5. D/Max remains the protected rollback; v2.3 and v2.4 remain historical experiments.

## Frozen offline signal path

This runs after the v2.3 Sustained Air candidate, not on dry vocal and not as a substitute for the original REC→MAIN chain.

- v2.3: candidate-only 7.9–15 kHz Butterworth band conditioner; amount 0.45, threshold -12 dB, knee 4 dB, attack 35 ms, activity floor -55 dB. Fitted on 0–4.8 s of the original 44.1 kHz take.
- v2.5: RBJ peaking EQ, 7,000 Hz, Q 0.75, +0.75 dB; fixed output trim -0.1467149783536854 dB.
- No target waveform lookup or phrase-specific timestamps during rendering. Python/SciPy implementation is offline research, not audio-thread-safe VST3 DSP.

## Same-take measurements

Active-frame STFT band-level MAE; lower means closer for this metric only.

| Segment | Version | 4.5–7.9 kHz | 9–14 kHz |
|---|---|---:|---:|
| 0.4–4.8 s | D/Max | 1.150 dB | 1.840 dB |
| 0.4–4.8 s | v2.3 | 1.284 dB | 1.282 dB |
| 0.4–4.8 s | v2.5 | **1.093 dB** | **1.212 dB** |
| 7.4–10.0 s | D/Max | 0.863 dB | 1.783 dB |
| 7.4–10.0 s | v2.3 | 1.140 dB | 0.839 dB |
| 7.4–10.0 s | v2.4 Gentle | 0.912 dB | 1.467 dB |
| 7.4–10.0 s | v2.5 | **0.892 dB** | **0.809 dB** |
| 11.0–14.0 s | v2.3 | 1.227 dB | 0.948 dB |
| 11.0–14.0 s | v2.5 | **1.041 dB** | **0.913 dB** |

A separate full-clip analysis-only loudness-matched comparison reports 4.5–7.9 kHz MAE **1.308 → 1.105 dB** and 9–14 kHz **1.153 → 1.111 dB** (v2.3 → v2.5). v2.5 measured -19.9985 LUFS and approximately -4.027 dBTP using 4× reconstruction. All these are same-take offline measurements, not proof of generalization.

## Verification status

- Owner listening: **v2.5 preferred**; not a blind ABX.
- Frozen presence stage + transfer audit focused tests: **26/26 passed locally**.
- Exact consolidated PR #2 head 35c7e8200782a6707957684a82b31e6d8635a36c: full suite **138/138 passed on Ubuntu and 138/138 on Windows**, workflow #44793736166.
- Reproduction: 15-second 24-bit FLAC matches the prior v2.5 render within quantization; report records full-clip band errors.
- Browser: six lossless tracks loaded, synchronized switching and third-phrase looping worked in Chromium, no JavaScript errors.
- Independent vocal stress: one 88.493 s stem reached -0.177 dBTP estimated (fails -1 dBTP output gate); one 42.602 s Alchemist REC-printed input reached -1.686 dBTP but is not a Deuce take or untreated dry source. Neither has an original Deuce REC→MAIN target; neither is a transfer-match pass.
- Full exact-head Sound Match CI passed on both Ubuntu and Windows; see workflow #44793736166.

## Native Skell Preset status

The current Skell Preset integration line contains a 13-stage factory 46 **Deuce v2.5 (Native Trial)**. It uses a D/Max-inspired native REC/MAIN base, broad corrective EQ, +0.75 dB / 7 kHz / Q0.75 bell and output calibration. The underlying v2.3 Sustained Air stage has **not** been ported. Do not call this an exact v2.5 port or an approved VST3 sound. Exact-head Windows VST3 and portable CI passed on integration commit 68ae71414d28cc30fa89275c1104544c000d6cef (run #44719941231); FL Studio and owner listening of the native trial remain separate gates.

## Transfer-audit acceptance gate

See DEUCE_V25_NEXT_PRIORITY_VALIDATION.md. A new test requires two sample-aligned files from the same entirely new Deuce performance: (1) frozen v2.3 candidate output and (2) original FL Studio REC→MAIN target. The reference is scoring-only. Never refit on the new target. Keep D/Max and original presets untouched.