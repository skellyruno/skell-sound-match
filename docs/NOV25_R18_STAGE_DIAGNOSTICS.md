# R18 — recover R17 and separate vocal body from reverb-tail scoring

Parent repository head `48597da2d95711fcf672f6c465874408c43f4d19`, R16 CI run 45604907050 succeeded. R16 full checkpoint recovered and checked against its SHA256 manifest. R17 was interrupted before its complete checkpoint and commit; its final HTML, screenshots, exact five embedded FLAC clips and manifest are recovered and preserved here. R17 raw DSP recipe is **not available**. No R17 listening feedback was received. R16 feedback verified against R16 manifest and all ten audio hashes; Wait B remains selected, all three old Uhhuh candidates rejected. No owner promotion or protected preset edits.

## Reproduction
Extract R16 ZIP to `r16/`; extract R10 ZIP to `r10/`; copy the included original headers Reeverb2.h and PlateReverb.h to `r10/harness/core/`. Keep original user `myers.zip` at ../files/myers.zip and R14 checkpoint at ../SKELLY_SOUND_MATCH_R14_NEWER_VOCALS_PRIVATE_NOV25.zip. Keep exact R17 HTML at ../r17/SKELLY_SOUND_MATCH_R17_PRIVATE.html, the R16 feedback JSON at ../SKELLY_R16_LISTENING_FEEDBACK (1).json. Original audio remains private and is not re-exported as user-owned raw files in this checkpoint. Run:

```
cd r16
 g++ -std=c++17 -O2 -Wall -Wextra -Werror -ffp-contract=off -shared -fPIC limiter_static.cpp -o limiter_static.so
 python test_limiter.py
cd ..
 g++ -std=c++20 -O2 -Wall -Wextra -Werror -ffp-contract=off -shared -fPIC -Ir10/harness r10/original/Reeverb2.cpp room_bridge.cpp -o wet_room.so
python recover.py
OPENBLAS_NUM_THREADS=1 python search.py
OPENBLAS_NUM_THREADS=1 python native_search.py
OPENBLAS_NUM_THREADS=1 python audit.py
OPENBLAS_NUM_THREADS=1 python stage_search.py
OPENBLAS_NUM_THREADS=1 python -m pytest -q test_stage_diagnostics.py test_room_fit.py
```

## Evidence
All 15 R16/R17 embedded hashes and R16 votes bound. R17 dry and target differ from raw by shared -5.38998 dB preview gain only (residual RMS <3.5e-8). Restoring gain reproduces R17 later scores within 3e-6: A 7.15054, B 6.62173, C 6.89077. These are archived audio-only comparators, not reusable recipes. R16 exact saved Limiter C++ offline port rebuilt and reran 12 synthetic cases, four analytic clip checks, four invalid parameter checks; no Rust or FL parity. Native Reeverb2 wet engine compiled with recovered R10 test-only shim. Four real audio 127-vs-1024 block comparisons exactly equal, 44.1/48/96/192 kHz. JUCE fetch DNS blocked; no Rust compiler or full Maximus dependencies. No new UI or VST3.

18 long weighted FIR trials, 576 native wet-send trials, 864 stage-balanced wet-send trials (1458 total). Training-only parameter selection within each search, previously reused later section. Long FIR selected direct 16.3884, residual 13.2991 later; CG hit iteration cap, private research only. Native pre 10.1098, post 11.9186; stage-balanced pre 9.3752, post 8.8738. All rejected against R17 B 6.62173. Stage search also tested raw body and tail profile error, did not relax legacy gates. No new candidate promoted or added to active listening battle.

Original raw Uhhuh target has 293 scalar channel samples at/above abs(.9999), 179 at abs(1). Original score excluded all seven later dry-vocal-active frames using a -40 dBFS frame threshold; ten later scored frames are tail-dominated. New independent stage diagnostics freezes thresholds from training (source 24 dB below peak frame, reference 50 dB), separately measures seven vocal-active and 11 tail frames, excludes 110 rail-contaminated stereo sample positions of 14336 vocal sample positions in later region, reports 139 discarded partial-end samples. R17 B later vocal waveform NRMSE .66638, correlation .76602, tail envelope 1.57549 dB; old waveform score 1.38464 is different measurement, not an audio improvement. Native pre later vocal NRMSE .63565 but overall 10.1098, rejected. 11 stage diagnostic + 7 long-FIR focused tests passed. Original source and states remain private. Full independence unavailable (same performance/examined holdout). Next: acquire Maximus crate dependencies, original Fruity Compressor/Multiband code, reconstruct stereo modulation and reverb stage using independent audio. Keep previous winners. No public sharing of private DSP, fitted kernels or audio. Keep draft.
