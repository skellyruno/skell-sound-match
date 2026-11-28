# R55 — phase-aware native fitting and full-recording headroom

Owner explicitly deferred listening tests until substantially closer numbers. No listening lab generated. Continue the R54 checkpoint; private artist catalog generation 55, 35 stable skellyruno entries, 78 immutable revisions (54 old + 24 new). Artwork payload exactly unchanged. Two historic extra presets and protected Club Gate unchanged. No production promotion.

## Real native processor results

Reused the verified offline JUCE 8.0.12 kit and cached Skell Preset source 5902e104ca650b5e29e395584140a5dbb891f315 plus existing local integration patches. All 33 original dry/reference pairs checked against recorded hashes. Direct native processor render, not portable DSP approximation. 32 non-gate pairs searched, 2,019 search renders and 125 extra verification renders. Native complex EQ fitted magnitude AND phase of an earlier-region complex cross-spectrum; no target samples enter processor replay or post-hoc target shifts. Other experiments used source-specific dynamics, native modulation, paired echo and bounded existing saturation/clipper controls. First 45% fitting / next 25% candidate selection / final 30% retrospective guard. Repeated same-performance development is not independent validation; some bounded follow-ups after a stress veto were re-screened on those same regions. New generic native_phase_eq.py consolidates the fitter; 2 local synthetic unit tests passed.

| Sound | R54 | Final R55 |
|---|---:|---:|
| Myers Full | 20.348 | 5.324 |
| Myers Main | 17.712 | 5.728 |
| Nobody Main | 15.696 | 5.630 |
| Plan Main | 15.390 | 5.659 |
| UP Main | 10.016 | 4.710 |
| Nobody Full | 15.701 | 8.929 |
| Free Main | 17.656 | 10.437 |
| Free Full | 16.625 | 10.418 |
| UP Full | 9.601 | 6.118 |
| Distortion | 9.726 | 7.944 |
| Wait Main | 6.789 | 5.038 |
| Wait Full | 5.952 | 4.886 |
| Myers Angelic | 6.591 | 6.256 |
| Myers Angelic Full | 7.617 | 7.138 |
| Hop Full | 5.481 | 5.266 |

15 match revisions, nine separately classified headroom repairs, nine unchanged pair chains. No added reported latency. Same-take mean error at 44.1k 9.217345 -> 6.749899; at 48k (resampled processor outputs compared with same 44.1k references) 9.199875 -> 6.741864. Nominal worst estimated true peak -1.3503 dBTP at 44.1k and -1.2233 at 48k. The new complete-recording +6 dB input stress audit found 16/33 baseline over-full-scale cases, versus 0/33 in the final bank at 48k/64 samples (worst -0.0788 dBTP). Earlier short stress test was less comprehensive; overload can create audible nonlinear distortion and aliasing even below full scale. Headroom-only trials must not be promoted as sound matches. Native wave/side/tone/envelope component guards maintained. The target 1.5 score has not been met except protected Club Gate. Uh Huh Base/Full, Free pair, Nobody Full, Distortion Full, Overtime Full, and the adlib modulation/pitch/ambience mismatch remain high-priority. Exact Panagement mapping and Wait pop removal remain unverified.

## Bank, build and verification

Private bank generation 55 verified 35 packages, 78 history revisions, unchanged stable artist/type/pair identity and artwork. Local bank-enabled Linux VST3 and Quick4 renderer rebuilt after restoring the verified offline header search environment. Embedded native bank test passed install, repeat, upgrade/history/downgrade, local edits, unmanaged collision, malformed bank. Corrected local capture invocation and temporary home; final actual editor 180 reported scenes / zero failures, artist list inspected. Cached source is not current head; Windows VST3/FL Studio and independent takes remain unverified. No user-facing installer or separate preset pack. Public repository contains generic fitter/tests and aggregate documentation only; private catalog, recording identities, fitted controls, reports and source checkpoint stay out of Git.
