# R32 — pitch-conditioned voice-envelope analysis and assistant foundation

Research: [STAND](https://github.com/haruneko/stand/tree/d8fb9489a7da2d5e6e6c24609691495eb6e71a49) wraps WORLD DIO, STAR and PLATINUM and provides time-map utilities. Independent offline cepstral spectral-envelope diagnostic, not a port of WORLD or STAND. Use optional local Praat F0 or explicit F0 track, 40ms frames, 10ms hop, pitch-dependent lifter, stereo power, seven normalized 180–8000Hz bands and harmonic energy proxy. No key/tempo changes or pitch correction. Require common voiced frames within 100 cents and matching time geometry; does not establish same-take provenance. Install optional voice_analysis extra; no mandatory new dependency. API vocal_envelope.analyse and compare. No third-party source copied.

Actual exact R27 groups and original owner anchors, final historical 30% of each excerpt, R31 challenger recheck:

| Vocal | Earlier owner anchor MAE dB | R31 MAE dB |
|---|---:|---:|
| Nobody main | 1.207 | 1.051 |
| UP main | .681 | .638 |
| Myers main | .956 | .679 |
| Overtime main | .698 | .572 |
| Speakerz main | 1.031 | .839 |

16/18 groups measurable; Uh Huh and Deep Voice insufficient pitch-matched voiced frames. Separate bounded 96 pitch-conditioned EQ trials across 16 groups: six regularized EQ candidates per group, first45/middle25/final30 split, best available previous candidate/gain-only comparisons, same envelope and prior composite constraints; zero accepted. Nobody delay selected on middle section but final composite worsened 2.804 to 2.956; rejected. No new sound promotion. These historical sections are repeatedly used, not independent performance evidence. R31 five challengers retained; all earlier owner picks untouched. 16 focused local retrieval/envelope unit tests passed. Native assistance is a separate read-only backend in Skell Preset draft #97 commit 0c97e782af5d02373b33d5aaebe23557b543cf74, inspired by [KnightHacks](https://github.com/BasilOnGit/knighthacks-vocal-studio/tree/84572c3c3e8367db6b3b35ecb510b8a4f07a8a2a); no network inference, no copied code. Future bridge must preserve source stage and validated effect IDs. 40 native standalone cases plus sanitizer and 120 read-only real-clip goal evaluations; not a working AI chat UI or model. Local JUCE DNS blocked. No private audio, feature vectors, fitted recipes or HTML in public Git.
