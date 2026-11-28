# R31 — retrieval-guided vocal reconstruction

Research reference: [Sonic-Icons-LISN/vocal-audio-retrieval](https://github.com/Sonic-Icons-LISN/vocal-audio-retrieval/tree/42a9b3de130918b55b619b510c89b52aa1eb07f9). Its README proposes text, vocal imitation and original sound encoders, fusion and contrastive alignment; CLVAP.json specifies 768-dimensional embeddings, HTSAT tiny audio/vocal encoders, 48 kHz / 64 mel bands. CLVAP/LICENSE is CC0, but outer repository and weight licensing are not established by that file. No upstream code, models, weights or training corpus copied. Independent NumPy/SciPy retrieval descriptors borrow the high-level retrieval idea, not the neural architecture. No new dependencies or cloud inference.

## Optional API
`vocal_retrieval.descriptor(audio,rate)`, `prototypes(enrollment_audio,rate)`, `rank_prototypes(query_descriptor, [(reference_id,prototype_tuple),...], allowed_keys=verified_stage_ids)`. Returns distances, not similarity percentages, sound approval, identity or alignment. Use 1–60 second excerpts, 32–384 kHz integer rates; mono/stereo only; silent or invalid input rejected. Store descriptors locally; no private recordings or feature vectors in Git. The bulk intake/production preset fitter remains unchanged; this is an explicit advisory API.

## Actual private benchmark
R27 lab hash and all 56 encoded clips checked; R27/R28/R30 archive manifests (85/210/25 entries) verified. Eighteen stage/group IDs. First 45% enrollment, middle 25% model selection, last 30% evaluation; all same historical recordings, previously explored. No independent performance generalization. One silent candidate excluded from middle selection. Initial four-group fusion was worse than tone-only (25 vs 26 top-one; 35 vs 41 top-three out of 56), rejected for retrieval. Search 96 fixed combinations on middle excerpts using group-macro reciprocal rank; choose tone + 0.35 stereo with whole and half enrollment prototypes. Final results:

| Query | Tone-only first | Calibrated first |
|---|---:|---:|
| Original | 11/18 | 16/18 |
| Recreation | 15/38 | 17/38 |
| All | 26/56 | 33/56 |

Top-three 41/56 -> 40/56 (regression), mean reciprocal rank .624 -> .679. Historical final sections already examined; this is exploratory, not a blind validation. Do not replace source/take/stage checks or auto-accept nearest matches.

## Actual audio finishing
72 bounded causal global/3-band level response + EQ trials across 18 archived stage groups. Select training baseline from exact prior pick, R28 or R30 experiment; compare against strongest available prior anchor and train-calibrated gain-only per window. Extra descriptor check is advisory; retain absolute spectral, envelope, waveform, stereo, level and peak gates. One initial pass, nine selected nonpasses rerun with four causal linked peak-hold/release ceiling choices on train and validation only (36 variants); four further passes. Repeated historical final excerpts, not independent. Estimated true peaks checked again after PCM24 FLAC encoding.

| Candidate | Prior final error | New final error | Estimated peak dBTP |
|---|---:|---:|---:|
| Nobody main | 3.670 | 3.452 | -7.07 |
| UP main | 2.008 | 1.844 | -4.83 |
| Myers main | 2.291 | 2.008 | -1.71 |
| Overtime main | 1.929 | 1.812 | -4.90 |
| Speakerz main | 2.300 | 1.900 | -3.21 |

Four unguarded variants exceeded peak limit and were not distributed. Other 13 groups did not pass; missing exact Deuce/Alchemist/Club Gate not substituted. Wobbly, Zaam, Angelic, Deep Voice still require genuine wet-path, modulation and formant reconstruction. No owner-approved sound replaced, no native parity or plugin release claim. Private R31 checkpoint and separate 5-group / 20-clip HTML outside Git, previous archives unchanged. 12 local focused tests passed after fixing gain normalization; CI pending. Local JUCE fetch DNS blocked; no UI changes or native builds.

Next: independently paired recordings, stage-specific hard-negative retrieval, measure actual learned pretrained embedding model only with verified local weights and licensing; retain raw audio and feature embeddings privately. Don't change tempo/key or replace preset identities.
