# R54 — native rack matching (2026-11-26/27)

Continue R53, not a new matching project. The private generation-54 catalog supersedes the trial generation-53 bank, with 35 stable skellyruno artist entries and 54 immutable revisions. The approved artwork payload is byte-for-byte unchanged. All historical approvals and old packages remain protected. 14 matching revisions, 2 separately classified headroom-only repairs, and 17 unchanged matched-pair chains; the two historical extra recipes remain unchanged. No production approval.

## Actual processor evidence

Verified original dry/target hashes for all 33 available same-take pairs. The direct diagnostic imports each native package into SkellPresetAudioProcessor and invokes processBlock; only declared host latency is compensated. It never consumes target samples during rendering. Tested using cached Skell Preset source revision 5902e104ca650b5e29e395584140a5dbb891f315 and verified JUCE 8.0.12 dependencies; the newer PR #90 revision was not tested here. Search performed 834 processor evaluations followed by 316 safety-search evaluations, plus separate final renders, trims and stress checks. First 45% training, middle 25% selection, final 30% retrospective regression guard. Not independent performance validation. R54 score uses the R53 diagnostic formula on actual processor renders; it cannot be compared with R51 offline scores.

| Sound | R53 actual native | R54 actual native |
|---|---:|---:|
| Wait Main | 7.956 | 6.789 |
| Overtime Main | 5.231 | 4.539 |
| Plan Full | 6.460 | 4.889 |
| Speakerz Full | 5.237 | 4.418 |
| Myers Angelic | 7.514 | 6.591 |
| Hop Main | 5.214 | 4.301 |
| Hop Full | 6.879 | 5.481 |
| Distortion | 11.275 | 9.726 |
| Deep Voice | 7.416 | 6.793 |
| Distortion Full | 12.028 | 9.030 |
| Skellian Full | 7.274 | 6.548 |
| Club Wobbly | 8.856 | 6.699 |
| Club Muffle | 6.822 | 5.589 |
| Club Zaam | 8.082 | 7.058 |

New revisions meet -1 dBTP estimated true-peak guard at 44.1 and 48 kHz without increased host PDC. Free Full and Myers Full are output-trim-only safety repairs, not closer matches (matching scores worsened). Plan Full's matching change also fixed its original peak failure. 33/33 nominal-level matched pairs now below 0 dBTP at both rates versus three over-full-scale at baseline. At +6 dB input, 12/33 still exceed full scale: release blocker. Wait Full's proposed revision failed the 48 kHz peak guard, so retain R53. Wait Main improved but the original pop's removal is not proven. Club Wobbly's side error reduced 4.786 to 0.749; not exact Panagement mapping. Keep Club Gate unchanged. No claim that the two historical additional recipes have verified reference-pair matches.

## Private delivery and regression

Prepared private generation 54 with stable IDs and the approved cached artwork. Built bank-enabled Linux VST3 and actual Quick4 renderer locally; native embedded bank tests passed all 35 with duplicate prevention, upgrade/history/downgrade and local-edit protections. Linux module entry/factory loading succeeded, not a full external host test. Quick4 reported 180 scenes, zero failures, using cached 5902 source plus local integration patches. Private Windows build, FL Studio, independent takes and listening approval remain unverified. No preset installation or separate end-user pack. Public repo receives this summary only; the actual private checkpoint retains the render harness, fitting scripts, source identities, catalog and diagnostics. Private audio, settings, artwork and listening lab remain out of Git.

Next: fix excess input-level sensitivity without flattening reference dynamics; use independent performances; investigate Wait's original transient and Wobbly's saved modulation controls, and improve the remaining high-error main/full pairs. Keep all changes experimental until actual listening and host verification.
