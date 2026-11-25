# Skelly Flangus owner source intake

Owner supplied a C++ source/header pair and states their team authored it, requests Skelly Licensing. The definitive license terms are pending; preserve originals and private adapted source. Do not upload source, audio, FST or individual private recipes to public Git. No third-party dependency relicensing.

Actual native DSP isolated from LYNX mixer wrapper, corrected namespace mismatch. Exact eight-control raw-state layout verified against UP and Myers FST records. Same settings in both; do not assume other targets share them. Portable adapter supports raw little-endian 32-byte decode/encode, validation and fixed-state renders; GCC, Clang, ASan/UBSan tests passed. Frozen output block parity at 32/44.1/48/96/192 kHz. Live gain automation 64/512-sample schedules differ by max 0.0209675282, so do not claim automation parity.

Real aligned same-take stage tests; outer dry/wet routing fitted on earlier segment, later segment diagnostic. Composite lower is better, not percent match:
| Stage | Calibrated direct baseline | Supplied engine with inferred outer mix |
|---|---:|---:|
| Speakerz Flangus | 12.853 | 0.281 |
| UP Flangus | 12.844 | 0.501 |
| Myers Flangus | 11.717 | 1.254 |
| Wait combined stereo | 11.660 | 0.874 |
| Hop Out chorus | 12.894 | 8.585 |

Speakerz later band MAE .085 dB, estimated -1.36 dBTP, promising stage diagnostic only. UP/Myers/Wait exceed peak gate; Hop Out previous independent chorus approximation remains closer. No auto promotion, complete source-to-output preset or independent take validation. Outer mixer fit is not an original FL knob setting.

Skell Flang draft PR #19, exact head d11224ad9956c9711c05372f1d604093412c75dc, adds optional owner-source build, separate eight raw IDs plus default-off exclusive trial, no replacement of legacy settings. Portable raw signal-path test passed GCC, Clang and sanitizers; original engine fixed-state parity, mono, transitions and disabled legacy identity. Standard build does not include private engine. Private package includes untouched original source, isolated adapted source, portable tests, recovered 32-byte state, and private results. No private source committed. JUCE/Windows raw-enabled build, UI, state recall, pluginval, real host automation and independent A/B remain unverified. Next: reuse the same owner engine for Sound Match and Skell Preset through an approved source distribution workflow; confirm outer mixer routing and delay code next.
