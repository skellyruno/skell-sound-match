# R4 external-reference offline diagnostics — 2026-11-24

Continue R3 at 61362c5, draft PR #2. No new owner feedback or production promotion.
Library recovery: SKELLY_MAIN_VOCAL_R3_PRIVATE_NOV24.zip, SKELLY_MAIN_VOCAL_RECONSTRUCTION_R3_NOV24.html, SKELLY_AUDIO_ONLY_TRANSFER_CHECKPOINT_NOV24.zip, SKELLY_AUDIO_ONLY_DYNAMICS_R2_PRIVATE_NOV24.zip and SKELLY_SOUND_MATCH_CONTINUITY_NOV24.zip. Keep these original archives and historical winners. Private audio, learned recipes and per-source metrics remain outside Git.

## Method and measured results
Parselmouth 0.4.7 labels voiced/unvoiced frames, activity is frozen to source, 1024/2048/4096 FFT band distributions compare unpaired performances. Pedalboard 0.9.23 implements a bounded 7-band EQ and optional compressor external reference, not native Skell DSP. Nine targets x 13 training evaluations = 117. Training excludes target and evaluation performance identities; 2–3 other recovered named performances per target. Reference fit uses first 60%, comparison final 40% of an already-seen 6-second excerpt. R3 metric is separately checked on full excerpt; these are not genuinely unseen target takes. R3 baseline uses recovered FLAC previews with preview gains undone, not full original stems. PyTorch implements an independent paired multi-resolution STFT diagnostic, not upstream Auraloss.

| Main target | R3 spectral error | R4 spectral error | Raw R4 estimated dBTP | Screen |
|---|---:|---:|---:|---|
| Deuce | 10.71 | 16.51 | -5.35 | reject |
| Alchemist | 5.29 | 5.19 | -7.71 | reject (R3 composite regressed) |
| Speakerz | 8.40 | 5.26 | -4.25 | experimental pass |
| Hop Out | 4.56 | 12.93 | -3.86 | reject |
| UP | 7.18 | 4.93 | -3.32 | experimental pass |
| Myers | 5.58 | 7.75 | -3.96 | reject |
| Plan | 4.35 | 5.91 | +2.39 | reject |
| Overtime | 3.80 | 9.74 | +0.03 | reject |
| Wait | 8.56 | 10.42 | -3.86 | reject |

Acceptance requires improvement versus dry and R3 on both spectral and R3 composite metrics, dynamics error no more than 0.5 dB above better baseline and raw peak <= -1 dBTP. Two pass; seven rejected. Scalar finish is preview safety, not limiter or proof of safe production gain. Paired Deuce multiresolution diagnostic: historical native 0.92689, Pedalboard 0.11592, independent R3 compressor 0.02833; same historical normalized isolated stage, no new performance.

## Verification and limitations
50/50 focused local tests including five added tests. Chromium loaded actual self-contained HTML content, reset candidate/target playback and played media; desktop and 390 px mobile screenshots captured, initial misleading R3/R4 peak labels and candidate playback reset corrected, then recaptured. 44 FLAC clips independently decoded, hashes/rate/length verified, estimated 4x preview peaks <= -1.4999 dBTP. No external neural model has been run: upstream DASP/Auraloss installation unavailable; TAPE, ST-ITO, DeepAFx-ST and NablAFx still need source/weights, license and independent validation. No commercial distribution of these tools. Local JUCE fetch failed DNS. No native integration, FL Studio, real new paired takes or owner listening approvals. CI for this commit separately required. 

## Continuation
Read AGENTS.md, active status, next matching tasks, latest exact draft PR and CI. Check Library first for latest named private checkpoints and listening lab before asking for resupply. Preserve prior artifacts; never restart or commit private recordings, learned models or proprietary source. Save new private checkpoint with hashes, report evidence, and update the existing draft PR with tested nonprivate code/docs. Next: train on genuine new performances, fix fixed-gain safety and independent native compressor streaming parity; add optional licensed upstream research tools in isolation, compare them against current metrics. 
