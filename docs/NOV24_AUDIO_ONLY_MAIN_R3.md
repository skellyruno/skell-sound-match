# Audio-only R3 — main vocals and independent compressor

Parent 77b11f2a0e31744879870e9cd6e8669b575fdcfd Python CI 45542218617 passed. Owner asked to focus on main vocals and external tools, liked earlier gate listening but did not submit new winner selection. Keep all nine original presets, provisional families and historical approvals. No new factory promotion, no supplied engine in this experiment.

## Paired compressor
Historical 15-second lossless Deuce Studio vs Native isolated compressor lab: direct dry and Studio RMS compressor, same recording 661500 frames 44100 stereo, historical approximate -22 LUFS normalization. Training zero-lag correlation .98829. First 40% fit, next 20% validation, final 40% not optimized (previously seen in earlier research). 665 bounded 1ms power detector evaluations, 35 validation population candidates full rate, gain-only competes. Independent causal linked dual power filters, knee, parallel blend and gain. Not identification of unique original controls, not independent-performance equivalence.
Later relative RMS historical Skell .4112579; gain-only .2318317; new .0238277; 10/50/200ms envelope MAE .8275007/.8189150/.8742512 -> .0443533/.0433547/.0368490 dB; crest gap 3.20239 -> .151342 dB. Full raw trial estimated -7.372 dBTP. 135 separate Pedalboard 0.9.23 compressor training grid evaluations, top12 validation, later RMS .0902570, 200ms .294699dB. Not identical search budget or proof of superiority of all implementations. Same preview geometry. No model training or code copied from third parties. Other main dry/main pairs had low/inverted lag correlation, so not used as isolated compressor pairs.

## Reference-only main tone transfer
New conditioned_main.py estimates coarse periodicity using normalized autocorrelation and compares 6-band distributions across fixed source groups (>=8 frames/group). Not phoneme ID or robust F0 estimation. Main EQ/gate/compression only, no invented echo/reverb/stereo widening. Two unrelated training sources, first up to 6 seconds of reference; later 40% scored against 3–4 other dry takes per target (exclude target identity). 495 evaluations across 9 main styles and 32 held-out source renders. Earlier full-FX recipes shown where available; Speakerz and Hop Out now main-only target, so not same objective. Plan initial training window silent; corrected outer-padding start to frame 284672; reran all. Scores are comparative distribution distances, not percent matches. Some references are short historical excerpts or have limited nonperiodic coverage (Deuce only periodic group), source differences remain. 
| Main target | Mean dry score | Mean R3 score | Prior mean when available | Peak passes / tested |
|---|---:|---:|---:|---:|
| Deuce | 19.0628 | 9.1732 | 10.2638 | 3/4 |
| Alchemist | 15.8236 | 6.0951 | 5.7404 | 3/4 |
| Speakerz | 7.9048 | 9.6804 | 17.5292 | 0/4 |
| Hop Out | 22.7850 | 12.7462 | 14.3156 | 2/4 |
| UP | 9.5757 | 6.1403 | — | 0/3 |
| Myers | 11.9814 | 6.3136 | — | 0/3 |
| Plan | 14.3963 | 7.7199 | — | 0/3 |
| Overtime | 13.6105 | 4.6016 | — | 2/3 |
| Wait | 14.3118 | 10.9051 | — | 4/4 |
Peak pass = <= -1 dBTP estimated 4x. 14/32 safe, 18/32 fail. 8/9 improve all evaluated sources vs dry shape; Speakerz regresses; Alchemist previous recipe better on mean. Reject unsafe recipes; no production promotion, no implicit limiter. Wait diagnostic candidate only. Reference-only audio cannot uniquely identify original chain or disentangle microphone/performer/pitch/formant/effects. Independent source renders are new to this fit but prior project research used them. 
## External research and local checks
- ST-ITO https://github.com/csteinmetz1/st-ito : inference-time search in style embeddings, test optional loss against listening choices; Apache-2.0 metadata, model weights separately verify.
- TAPE https://pnlong.github.io/audio-effect-transfer/ : processed-reference-only effect embeddings and editable parameter decoding, research candidate; availability/weights/license not verified for deployment.
- dasp https://github.com/csteinmetz1/dasp-pytorch : differentiable EQ/dynamics, optional offline optimization; Apache-2.0 package metadata.
- DeepAFx-ST https://github.com/adobe-research/DeepAFx-ST : benchmark parameter prediction and differentiable FX; review dependencies/weights/rights.
- NablAFx https://github.com/mcomunita/nablafx : paired gray/black-box modeling; candidate for nonlinear dynamics/saturation, not tested.
- auraloss https://github.com/csteinmetz1/auraloss : multi-resolution spectral loss, candidate objective not trained or installed.
- Parselmouth https://github.com/YannickJadoul/Parselmouth : locally available 0.4.7, 95.56% agreement with independent coarse periodicity labels on 225 active Deuce frames, not ground-truth accuracy. GPL-3.0-or-later; research-only external optional dependency, no bundling.
- Sony Gaussian-prior vocal transfer https://arxiv.org/abs/2505.11315 : constrain parameter combinations using prior knowledge, investigate with multiple performances.
No downloads/weights installed; local JUCE retrieval DNS blocked, no screenshots or host validation. 
## Verification
45 local pytest across matching subset (9 new cases), includes rate 32–192k, gain invariance, causality, synthetic fit, invalid geometry and group coverage. 10-group 35 lossless clip HTML verified decoded finite, 4x peak <= -1.4999 and JS syntax. Main comparison uses active RMS matching and common attenuation; compressor uses common safety attenuation retaining historical level normalization. Browser playback/visual and VST3 unverified. Private recipes/audio/measurements remain in R3 checkpoint outside Git; no original raw presets or supplied DSP published. Next: native streaming compressor (static parity first), headroom-aware multi-source main fitting, finer spectral envelopes and pitch/phonetic conditioning, main stage alignment and isolated de-esser/limiter/saturation, held-back genuinely new recordings, then optional external embeddings vs owner choices. Keep gate/FX tracks active, no restart.
