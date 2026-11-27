# R56 — Native wet-tail and direct-path reconstruction

Owner requests no new listening tests until matching scores are substantially closer. Continue R55, keep the stable artist library and all historical choices. The target remains below 1.5; this is not a finished match.

## Method and numerical results

32 non-gate paired recordings searched using the actual cached native Skell Preset processor, verified JUCE 8.0.12 offline dependencies. All 33 original pair hashes rechecked. Earlier 45% fit, middle 25% select, final 30% retrospective guards. Audio correlation and nonnegative power-envelope lag identification seed existing delay and reverb controls; isolated pre/post delay prints and compatible paired main/full prints inform wet-return research. Measure actual native effect returns, screen candidate mix/gain/width, rerender native chains. Additional residual phase/magnitude, dynamics and gate searches plus conservative bounded wet-mix follow-ups. Some follow-ups occurred after earlier guard failures; repeated same-take screening is not independent validation. No target samples enter runtime DSP.

Retain only candidates that improve middle and later scores while guarding tone, envelope, waveform, stereo, peaks, latency and full-recording +6 dB input stress at 48 kHz/64 samples. Selection among guard-passing methods uses the middle-region score, not the lowest final-region score. 2,114 completed-report processor evaluations including candidate confirmation renders. 15 updates, 18 retained. Two additional historic recipes remain unchanged.

| Pair | R55 | R56 |
|---|---:|---:|
| Free Main | 10.437 | 6.433 |
| Free Full | 10.418 | 7.560 |
| Nobody Main | 5.630 | 4.840 |
| Nobody Full | 8.929 | 6.453 |
| UP Full | 6.118 | 5.552 |
| Myers Full | 5.324 | 4.964 |
| Wait Full | 4.886 | 4.667 |
| Plan Full | 4.889 | 4.275 |
| Overtime Main | 4.539 | 4.307 |
| Overtime Full | 8.618 | 5.400 |
| Hop Main | 4.292 | 4.124 |
| Hop Full | 5.266 | 4.774 |
| Deep Voice | 6.793 | 6.561 |
| Distortion | 7.944 | 6.450 |
| Club Angelic Full | 7.869 | 6.840 |

Catalog mean 44.1 kHz: 6.749899 -> 6.181660. 48 kHz resampled comparison: 6.741864 -> 6.177072. Worst nominal estimated true peak -1.40376/-1.57035 dBTP at 44.1/48 kHz. 0/33 full-recording +6 dB overloads, worst -0.22925 dBTP. Changed packages freshly evaluated; unchanged R55 byte-identical packages retain previously measured results. No increased reported latency. Headroom guard does not establish distortion/aliasing quality. Protected Club Gate unchanged.

## Root causes and limits

Original processed tails can remain audible after the dry recording goes silent; several native chains decay too quickly. Stronger Uh Huh candidates lower aggregate errors but fail waveform/stereo/headroom guards. Approximate translation of saved EQ/compressor/character states did not pass. Existing spectral pitch/formant module reports 768 samples latency, so adding it to zero-latency Uh Huh would violate the guard. Exact unknown wrapped effects and Panagement behavior remain unresolved. Do not promote rejected chains or infer exact plugin parity. Continue reconstructing direct+wet effects and low-latency formant processing rather than tuning aggregate error alone.

## Private bank and local verification

Generation 56: 35 stable skellyruno entries, 93 immutable revisions, same approved artwork and listening metadata. Private preset package hashes and identities verified. Bank-enabled Linux VST3 and real editor built using cached source 5902e104ca650b5e29e395584140a5dbb891f315 plus existing local integration patches (not latest branch head). Native embedded bank tests passed install, idempotence, byte identity, upgrade, history, downgrade, local edit and collision guards. Generic echo diagnostic tests 3/3 passed locally. Windows VST3, FL Studio, independent takes and listening approval remain unverified. Private recording identities, settings, reports and bank payload remain outside public Git. No separate user installer or listening lab.
