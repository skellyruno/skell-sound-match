# R66 full-effects repair

50% target (17 of 33, both-rate unchanged composite <=1.000 and existing peak/stress gates) remains unmet. Seven checkpoint-backed qualifiers, eight cumulative including reported-only R64 Wait Main. No new qualifying pair. 16/33 checkpoint-backed comparisons <=2, 19/33 <=3. Exact R62 processor bank unavailable and unchanged.

412 completed selection trials in 20 complete reports, 19 peak-safe selected candidates. Multi-seed context, separate M/S multiband finishing, exact-sample sparse wet stage, phase-preserving spectral correction, isolated REC supervision and native gain finish. Training region 45%, next 25% internal selection, refit through 70%, final 30% retrospective same-take evaluation. Previously fitted bases make internal validation non-independent. No target samples at inference. No independent performance or native-plugin validation.

| Pair | R65 worst-rate | R66 worst-rate |
|---|---:|---:|
| Overtime Full | 2.213340 | 1.481621 |
| Free Full | 2.886908 | 2.285717 |
| Wait Full | 1.386472 | 1.035593 |
| Myers Full | 1.411025 | 1.199914 |
| Speakerz Full | 1.452994 | 1.394881 |
| Plan Full | 1.489993 | 1.477265 |
| Wait Main (saved, not R64 reported) | 1.124890 | 1.123434 |

Wait Full, Myers Full and Overtime Full saved-coefficient nominal replays reproduce both rates exactly. All six improved full pairs pass both-rate nominal and +6dB full-recording stress checks. Estimated 4x true peak, not aliasing/distortion proof. One lower-error Myers candidate failed peak safety; retained only as research. R65 exact-head CI 45956488997 passed. Verified all 13 Quick4 kit entries, R65 manifest, rebuilt five C++ adapters with warnings-as-errors, 63 local tests passed (55 prior and 8 new). Fixed import-name collision in final gain script. Remaining broad, multiband, wet and static searches interrupted; excluded incomplete trials. New public helper is generic offline phase-preserving M/S fitting; private scripts retain exact fitted pipelines. New CI pending; no new real-time plugin, latency, CPU, Windows VST3, FL Studio, or UI claims. No private data published. Keep draft, no listening lab, no approved-bank changes.
