# All nine original targets + ten provisional source families — native research, Nov 24

Continuation of f585b3e. Previous exact-head Python CI 45526462297 success; Core 09a3539 portable DSP, Windows template VST3 and headless JUCE workflows all succeeded. New Core draft #47 head 929c1b7f85f8d145e0e9dee3031c7197d5d0c117 contains 3edcd73 (MatchToneFinish / MatchModulation) and 929c1b7 (frozen Deuce stages). Local GCC and Clang C++17 Release -O3 -DNDEBUG -Wall -Wextra -Werror regression executables passed; four rates for tone/modulation, five for Deuce, five block schedules, actual native C++ bridges. Exact header/test Git blobs verified. No production wrapper changes, no APVTS/state/factory mutations. New-head CI separate.

## Scope and metric
Nine original sound targets (4 main, 4 Club adlibs, MIC gate); Angelic no-delay and full are distinct groups. Ten additional provisional source families, not ten new approved presets. Existing protected sources and owner choices unchanged. Recovered latest lossless comparison URIs verified by stored SHA-256 before decoding. Real stage data from prior verified intake, one original named pair per provisional family. No cross-family pair, no fabricated mono side content in tone stage, no reference waveform used by native DSP.

First pass 21 candidate/stage jobs (11 historical excerpt variants, 10 new stage families), 810 bounded training evaluations. Nested exploratory pass 21 jobs, 19 sufficient coverage, 1968 evaluations, fits first 40%, chooses among regularized recipes/baseline in next 20%, scores final 40%. Because original later scores have already been examined, this is repeated same-take research, not blind or independent validation. Modulation 9 jobs, 8 sufficient coverage, 960 train evaluations; source-only Hop Out active-span retry 120 additional evaluations. Total 3858 tone/modulation training objective evaluations, not distinct owner-approved presets. Gate separate. All native candidate outputs selected without outer-section tuning within each pass.

Composite lower is better: six-band active frame MAE dB + 0.5*envelope MAE + 0.3*side/mid gap dB + 3*correlation gap + waveform relative RMS; deterministic <=128 frames per section, target training floor; exclude near silence and rail neighborhoods. Require >=2% train and later improvement, -1 dBTP estimated 4x peak ceiling, individual later regression guard (band .15 dB, envelope .2 dB, side .4 dB, correlation .025, waveform .035). No claim of certified percentage accuracy. Fixed bounds, no auto normalization during fitting; output preview calibration is separate and re-scored. Existing candidates historically fit on same takes, so these comparisons cannot establish independent performance generalization.

## Original targets, historical anchor finish pass (later composite)
| Target | Baseline | Trial | Outcome |
|---|---:|---:|---|
| Alchemist A | 4.399 | 4.596 | rejected, preserve approved |
| Alchemist B | 4.421 | 4.526 | rejected, preserve approved |
| Speakerz R6 full | 6.450 | 6.615 | rejected full-chain finish |
| Hop Out A | 3.914 | 3.745 | rejected, training improvement below 2% |
| Angelic no delay A | 5.766 | 6.059 | rejected; reverb unresolved |
| Angelic full A | 6.779 | 6.170 | diagnostic pass |
| Angelic full B | 6.808 | 6.242 | diagnostic pass |
| Muffle A | 5.428 | 5.299 | rejected side/correlation regression |
| Wobbly protected B | 7.460 | 7.247 | rejected side/correlation regression (letter A in current lab is same identity) |
| Zaam A | 5.322 | 4.178 | diagnostic pass |
| Zaam B | 5.576 | 4.332 | diagnostic pass |
| Deuce | — | — | disputed original excluded, native stage parity below |
| Club Gate | — | — | separate full gate assessment below |

Nested trial selected unity for both Alchemist, no-delay Angelic, Hop Out, Muffle and Wobbly; confirms not forcing changes. Both full Angelic and both Zaam variants again diagnostic pass. Speakerz nested 6.450->6.324 below required 2%; no promotion. Native tone stage is a finish on an existing printed candidate, NOT a reconstructed complete chain or actual delay/reverb solution.

## Real moving-delay stages (later composite, side/mid gap dB, true peak)
- Speakerz MAIN to MAIN+Flangus: 12.841->4.452, side gap 39.323->11.301 dB, -2.360 dBTP, passes. Slight waveform increase .2257->.2376 within margin. Full preset and requested delay balance still open.
- Hop Out MAIN DRY to MAIN CHORUS: original 51.43s file padded with ~36s silence; initial later coverage insufficient. Source-only last active frame 665781 plus 1s tail, first 60% fits, remaining active section scores. 12.883->4.422, side gap 40.308->12.110 dB, -3.711 dBTP full render, tail RMS error 5.46e-9->3.05e-9. Pass, not full-chain.
- Wait combined Flangus + separation: 11.660->3.894, side gap 36.645->10.728 dB, -1.079 dBTP, pass combined stage, not exact isolated Flangus.
- UP Flangus 12.881->2.137, -0.303 dBTP and waveform regression; Myers Flangus 11.695->3.032, +0.877 dBTP; reject, do not hide peak.
- Added source-driven modulated return on protected Muffle/Wobbly/Angelic no-delay/Zaam full anchor: none pass. Need actual pre/post-convolution and coherent modulation/delay routing. No arbitrary polarity or fake width replacement.

## Ten provisional families
First pass later composite: Myers main 20.841->13.291 (unsafe +5.20 dBTP/waveform); Myers Angelic 35.730->33.963 (envelope regression); Myers Uhuh 25.198->25.787 (unsafe); Wait main 8.029->5.185 (waveform regression); Plan main 23.423->20.530 (diagnostic pass, not isolated send or independently aligned); Overtime main 13.092->10.547 (waveform regression); Deep 36.750->35.952 (envelope regression); distortion 14.298->14.537 (regression); Skellian 24.077->22.854 (envelope regression); UP main 17.554->9.225 (unsafe +5.13 dBTP/waveform). Nested Wait main 8.029->6.297 -6.18 dBTP passes; Deep 37.139->36.285 -4.65 dBTP passes limited tone diagnostic, NOT pitch/formant reproduction. Myers Angelic/Uhuh nested insufficient frames; all other nested provisional trials reject. Preserve source identities and original rail warnings.

## Club Gate
Recovered complete original raw/gate pair, not exact approved B reference. Separate native train-first 60% constrained full-target fit. Coverage active 172086/103103, quiet 77376/71331, onset 161/59. Gate-only later normalized MSE active .000252012->.000248893, quiet .01920698->.01563283, onset .08618744->.03837642, peak -6.475 dBTP, exploratory pass. Finish later active .000257877->.000256823, quiet .01636632->.01151997, onset .17460360->.15811399, pass. Earlier B-fitted gate only parameters on original full recording yield later onset .02460089, quiet .01074120, but its B excerpt overlaps this performance and later section; do not call independent. Exact B not replaced, no new owner decision.

## Deuce native math
Ported frozen v2.3 Sustained Air and v2.5 presence into native double precision. Independent SciPy equivalent reference at 32/44.1/48/96/192k max synthetic discrepancy 1.17e-15; real historical 15s lossy D/Max preview max 1.67e-16 and RMS 1.01e-17, estimated -4.1523 dBTP, native offline 0.0731s. Golden tests at all five rates. This verifies mathematical stage port on a historical preview only. Exact approved v2.5 lossless and complete D/Max source still missing; no comparison to disputed original or full REC/MAIN approval.

## Private listening output and validation boundaries
New private single HTML has 13 groups, 39 clips, 2 reviewable battles. All prior ten groups' references/candidates unchanged; added one challenger to Angelic full and Zaam, retained old two attempts (not owner approvals). Separate non-voting Speakerz/Hop Out/Wait isolated-stage diagnostics. All 39 decoded/checksummed, geometry checked, max estimated true peak -1.4999995 dBTP and max within-group LUFS spread 7.15e-7. Actual emitted C previews re-scored Angelic 6.779->6.251, Zaam 5.322->4.180, pass both-section and regression checks. JavaScript syntax checked. Actual Chromium file and localhost navigation blocked by administrator policy, so no current visual/browser playback or feedback-export claims. No real listening approval; no private audio/recipe/IR/checksum data published. Local JUCE fetch failed DNS; new host CPU/latency, full VST3 wrapper, pluginval, FL Studio, independent takes remain unverified. Keep drafts unmerged and retain all factory identities.

Next: exact source recovery, independent performances and coherent wet routing; build native renderer integration for new primitives, use modulation stage evidence to fit correct full-chain order, no forced numeric promotion on weak or unsafe candidates. 
