# Deuce v2.5 — next-priority transfer validation (2026-11-20)

## What is implemented

skell_sound_match.deuce_transfer_audit applies the frozen v2.5 7 kHz presence repair to an already-rendered v2.3 candidate. It never fits parameters and never uses the reference audio to render. A same-performance original REC→MAIN target is optional and used only for scoring. Without it, the report explicitly says **Safety audit only** and emits no matching scores.

- The focused v2.3 + v2.5 test suite passed **26/26 locally**.
- The consolidated repository suite passed **138/138 on Ubuntu and 138/138 on Windows** in workflow #44794041833.
- The original 15-second Deuce v2.3 candidate was re-rendered through the module. Its v2.5 result reproduced the existing 24-bit FLAC within quantization.
- Full-clip analysis-only loudness-matched band MAE: 4.5–7.9 kHz 1.308 dB → 1.105 dB; 9–14 kHz 1.153 dB → 1.111 dB.
- This is reproducibility on the already-approved take, not independent transfer validation.

## Correct interpretation of the two other-vocal stress checks

The two checks are **safety/streaming tests only**, not Deuce sound-match results:

1. An 88.493 s independent vocal stem: fixed presence-stage test, finite output and exact block/whole equivalence; estimated 4× true peak -0.177 dBTP (input -0.103). This exceeds the -1 dBTP release threshold. The transfer CLI must reject writing this output.
2. A 42.602 s Alchemist input: this is the owner's **REC-printed Alchemist recording source**, not untreated dry vocal and not another Deuce performance. Fixed presence-stage test, estimated 4× true peak -1.686 dBTP (input -1.707). It passes the numerical peak threshold but has no Deuce REC→MAIN target and says nothing about Deuce matching.

Do not describe the second file as a dry Deuce take. Do not claim either file proves that v2.5 generalizes.

## Run on a genuinely new Deuce performance

Prepare sample-aligned mono/stereo files at the same sample rate, frame count and start offset:

- new_v23_candidate.wav: the new dry Deuce take rendered through the frozen v2.3 candidate. It is not raw audio.
- new_original_rec_main.wav: the exact same dry take processed through the owner's original FL Studio REC→MAIN chain.

Then run:

~~~powershell
python -m skell_sound_match.deuce_transfer_audit new_v23_candidate.wav --target new_original_rec_main.wav --output deuce_v25_new_take_trial.wav --report deuce_v25_new_take_report.json
pytest -q tests/test_deuce_presence_repair.py tests/test_deuce_transfer_audit.py
~~~

The target is scoring-only. The tool rejects mismatched sample rates/shapes, path collisions, overwrites, non-finite samples, sample clipping and estimated 4× true peak above -1 dBTP. With no target, it produces safety-only diagnostics. The 4× true-peak estimate is a guard, not certified BS.1770 compliance.

## Promotion gate

1. Confirm band, envelope, consonant, sibilance, transient and punch-in behavior on the new take without refitting.
2. Audition original / D/Max / v2.5 at matched perceived loudness.
3. Port the full causal v2.3 stage plus v2.5 presence correction to native C++ only after transfer evidence; no allocations, locks or file access in the audio callback.
4. Run Windows VST3, state recall, automation, PDC, short-buffer, CPU and FL Studio tests. Keep factory 46 a trial until the exact offline sound is reproduced and the owner approves it.

No private vocal WAV or FL Studio state is included in this document or new code.