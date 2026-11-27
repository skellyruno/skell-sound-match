# R58 — structural ablation, flexible native EQ and causal phase research

Owner defers listening until numerical gap is substantially smaller. No listening lab and no production promotion. R57 checkpoint integrity: 957 hashed entries verified, no mismatch; latest JUCE 8.0.12 Quick4 kit 13 checks passed. Actual native processor uses cached Skell Preset source 5902e104ca650b5e29e395584140a5dbb891f315 plus existing local integration patches, not latest head.

## Native artist bank

32 non-gate pairs searched, 1,820 native render evaluations. Earlier 45% fit / middle 25% select / final 30% retrospective guard. Structural ablation removes redundant stages; reorder, dynamics, gate and wet-return changes. Flexible native Studio Parametric EQ uses bell, high/low pass and shelving response, fits integrated energy and complex cross-spectrum. Model compared with actual C++ filter impulse transfer: 45 configurations at 44.1/48/96 kHz; maximum complex error 8.013e-7. Peak-margin rescue after earlier vetoes is same-performance iterative development, not independent generalization. Selection among passing methods uses middle region score. All prior waveform, envelope, stereo, tone, cross-rate, latency and full-recording +6 dB stress guards retained; unchanged pairs retain earlier evidence.

| Pair | R57 | R58 |
|---|---:|---:|
| Free Full | 6.239 | 4.344 |
| Nobody Main | 3.734 | 3.256 |
| Nobody Full | 5.122 | 3.861 |
| UP Main | 3.657 | 3.098 |
| UP Full | 4.272 | 3.800 |
| Myers Main | 3.733 | 3.101 |
| Myers Full | 4.964 | 4.414 |
| Wait Full | 4.291 | 4.094 |
| Plan Main | 5.659 | 4.902 |
| Overtime Full | 4.678 | 4.071 |
| Speakerz Main | 4.851 | 3.547 |
| Distortion Full | 8.779 | 7.043 |
| Club Angelic | 7.345 | 6.646 |

Mean 44.1k 5.6514565 -> 5.3136494; 48k 5.6656656 -> 5.3340259. Nominal worst true-peak estimates -1.229/-1.101 dBTP at 44.1/48; full +6 dB 48k/64 stress 0/33 overloads, worst -0.281 dBTP. No increased reported PDC. 13 adopted, 20 retained, gate and historical extras protected. Generation 58 contains 35 stable entries and 125 immutable revisions, approved artwork preserved. Local bank-enabled Linux build and embedded migration/byte identity tests pass; real Quick4 180 scenes zero failures, artist list inspected. Nine generic Python regression tests passed locally.

## Causal phase research, not deployed

Coherence-weighted all-pass fitting and polarity selection on R57 native renders improved 19/33 pairs under waveform/tone accuracy guards. Static allocation-free C++ research prototype compared with Python, max sample difference 2.981e-8. Additional 38 native input renders verify cross-rate and full-recording stress. Nine of 19 pass all guards; ten fail peak/stress. Baselines here are R57, not R58. Overtime Main 3.644 -> 1.616; Overtime Full 4.678 -> 2.840; Hop Main 3.851 -> 2.942; Hop Full 4.774 -> 3.919; Wait Main 5.038 -> 4.292; Wait Full 4.291 -> 3.997; Speakerz Full 3.983 -> 3.433; Club Muffle 5.413 -> 5.190; Plan Main 5.659 -> 5.266. These are offline cascades of actual native render and compiled research stage, not editable native presets. No lookahead in prototype; full plugin integration, automation and real-time certification remain unverified. Keep separate until safe additive state compatibility and peak guards are implemented. No target samples consumed during replay.

Uh Huh Base original reference peak +3.290 dBTP, varying phase/lag across voiced windows; fixed timing shift is not justified. Candidate improved aggregate but failed waveform and peaks, retained original trial. Full also retained. Exact formant, Panagement and pop cause unresolved. Independent performances, Windows VST3/FL Studio, nonlinear distortion/aliasing verification outstanding. Target below 1.5 not achieved. Private sources, presets, fitted settings, reports and bank payload stay outside public Git. No separate installer.
