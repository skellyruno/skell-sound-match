# Deuce v2.3 — Sustained Air (experimental) 🩻

**Listening champion:** D/Max (15-second extract). **Protected history:** v1.9, v1.7, v1.4. This experiment is not approved or native-VST3-ready.

## Why this experiment exists

The previous D/Max render is very close overall, but high-band analysis found persistent 9–14 kHz differences on sustained vocal portions. Global treble boosts and extra clipping made other metrics or listening worse. The new causal conditioner uses a 7.9–15 kHz Butterworth bandpass on the candidate, tracks candidate-only low and consonant-band energy, and emphasizes less-bright passages while backing off for consonants. The reference is used only for offline *parameter fitting*. No per-phrase reference lookup or pasted target waveforms are used when rendering.

## Real same-take evaluation (44.1 kHz, 15-second 24-bit Deuce D/Max)

Settings: `amount=0.45`, `threshold_db=-12`, `knee_db=4`, `attack_ms=35`, `activity_floor_db=-55`, trained exclusively on 0–4.8 seconds. Comparison sections were 5.4–9.8 seconds and 10.5–14.7 seconds. These sections were examined during development and are **not independent unseen vocal takes**.

| Metric | Middle D/Max | Middle v2.3 | Later D/Max | Later v2.3 |
|---|---:|---:|---:|---:|
| 9–14 kHz mean absolute band-level error | 2.275 dB | 1.567 dB | 1.634 dB | 0.980 dB |
| Signed waveform correlation | 0.988727 | 0.988649 | 0.985839 | 0.985759 |
| Active 20 ms envelope error | 1.006 dB | 1.006 dB | 0.616 dB | 0.618 dB |
| Multi-res log spectral error | 3.964 dB | 3.960 dB | 3.695 dB | 3.681 dB |

Whole clip integrated loudness: D/Max `-20.000 LUFS`, trial `-19.989 LUFS`; 4× estimated true peak trial `-4.30 dBTP`. Whole-file null residual improves on some bands but overall it is about 0.03 dB worse, so **do not declare universal improvement**. Choose by actual level-matched A/B listening. The source D/Max and reference were not modified.

## Run with your own audio

```bash
python -m skell_sound_match.sustained_air_fit fit candidate.wav reference.wav --model model.json --trial trial.wav --report report.json
python -m skell_sound_match.sustained_air_fit apply another_candidate.wav model.json new_trial.wav
```

- The fitter can choose `amount=0` (exact bypass) when processing makes the reference match worse.
- `apply` needs only source audio and the saved model, not the reference.
- Outputs refuse existing paths and a 4× estimated true peak over -1 dBTP.
- Python source is **offline research**. Streaming/chunk equivalence is tested, but real-time CPU, low-latency VST3/FL Studio, and native sound equivalence are **unverified**. All filters are causal but Python allocations remain unsuitable for the audio callback.

## Next verification before any promotion

1. Audition the 15-second lossless player: original / protected D/Max / v2.3. Listen for mouth consonants, bright vowels, harshness, sibilance and any metallic texture.
2. Apply the saved parameters to a completely different Deuce performance, with the same REC→MAIN target chain, and measure it without retuning.
3. Port the candidate-only filter/envelope code into the Skell native DSP backend only after CPU/latency, parameter ID, state restore, and FL Studio tests.
4. Check both Deuce and Alchemist separately: Alchemist's input already has printed recording processing; it is **not** a clean dry input.
