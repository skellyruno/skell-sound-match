# R57 — integrated native band energy and isolated-stage identification

Owner continues to defer listening tests until substantially closer scores. Preserve the R56 catalog and all historical listening approvals. No listening lab or production promotion.

## Native matching evidence

Reused the verified JUCE 8.0.12 offline kit (13 checksum entries) and existing cached Skell Preset source 5902e104ca650b5e29e395584140a5dbb891f315 plus local integration patches. Direct native processor processBlock rendering. All searched original pair identities verified. Search 32 non-gate pairs: 1,626 matching/isolated-delay processor evaluations plus 40 isolated formant diagnostic renders. Protected gate unchanged. Exact integrated Welch band-energy model with coherence-weighted complex residual; fit bounded existing native eight-band bell controls before rendering actual processor. Joint direct/wet search, multiband dynamics and bounded headroom rescues. First 45% fit, middle 25% selection, final 30% retrospective regression veto. Repeated same-take development and rescue after previous safety vetoes are not independent validation. No reference samples enter replay.

| Pair | R56 | R57 |
|---|---:|---:|
| Free Full | 7.560 | 6.239 |
| Free Main | 6.433 | 5.024 |
| Nobody Main | 4.840 | 3.734 |
| Nobody Full | 6.453 | 5.122 |
| UP Main | 4.710 | 3.657 |
| UP Full | 5.552 | 4.272 |
| Myers Main | 5.728 | 3.733 |
| Wait Full | 4.667 | 4.291 |
| Overtime Main | 4.307 | 3.644 |
| Overtime Full | 5.400 | 4.678 |
| Speakerz Main | 6.609 | 4.851 |
| Speakerz Full | 4.410 | 3.983 |
| Hop Main | 4.124 | 3.851 |
| Myers Angelic Full | 7.138 | 6.682 |
| Deep Voice | 6.561 | 5.025 |
| Distortion | 6.450 | 5.415 |
| Distortion Full | 9.107 | 8.779 |
| Club Muffle | 5.589 | 5.413 |
| Club Wobbly | 6.699 | 6.447 |

19 improved / 14 retained recording pairs. Mean at 44.1 kHz 6.181660 -> 5.651457; at 48 kHz 6.177072 -> 5.665666. Worst nominal true peak estimate -1.21676/-1.10113 dBTP; full-recording +6 dB stress at 48 kHz/64 samples 0/33 overloads, worst -0.11242 dBTP. Changed packages retested; unchanged retain R56 evidence. Native tone, envelope, waveform, stereo and latency guards retained. Peak guard alone does not prove absence of clipping distortion/aliasing.

## Isolated stage research

Uh Huh isolated no-formant pre/post delay prints: recurrent lag 9873 samples at 44.1 kHz (223.878 ms). First wet tap stronger than direct path; this is measured diagnostic recurrence, not an exact proprietary parameter mapping. Native delay-only stage final error 18.718 -> 12.645; envelope and waveform improved but tone worsened. End-to-end candidate fails acceptance; both Uh Huh chains remain unchanged. Isolated formant-on/off median voiced fundamental ratio 1.0 (106 matched frames): evidence for spectral-envelope shift rather than pitch transposition. Existing spectral-formant stage selected candidate scores 7.338 versus 9.487 baseline but exceeds full scale and adds 768 samples reported latency; rejected. Causal EQ diagnostic 6.488 at -1.380 dBTP, zero latency, still not an exact formant reconstruction. Neither diagnostic promoted to full chain.

## Bank and verification

Generation 57 contains 35 stable skellyruno entries and 112 immutable revisions, same approved artwork and historical recipes. Private bank-enabled Linux VST3 rebuild and embedded-bank tests passed on cached source. Six new generic synthetic diagnostic tests passed locally; current exact-head CI must be checked independently. Windows VST3, FL Studio, independent performances and listening approval remain unverified. Private preset settings, recording data, stage identities, search reports and bank assets stay outside public Git. No separate user installer. Remaining priorities: Uh Huh direct/feedback and causal formant behavior, Distortion Full nonlinear character, Club modulation and independent transfer. Target remains below 1.5.
