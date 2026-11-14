# Compressor-aware MAIN-chain diagnostic

Run locally with your own settings:

```shell
python -m skell_sound_match.compressor_anchor input.wav processed.wav --threshold-db=-24 --ratio=4 --attack-ms=10 --release-ms=100 --makeup-gain-db=0 --out report.json
```

**The values above are synthetic examples, not real saved preset settings.** Do not push original vocals, preset states, real per-user parameter settings, screenshots, or local reports to public GitHub. The script never modifies source audio and refuses to overwrite its output report.

It estimates a 5ms frame-rate compressor-envelope *hypothesis* and compares it with the observed gain of the ENTIRE effect chain. It does not emulate any vendor compressor, derive precise knob values from audio, or establish that a sound is perceptually closer. Evaluate independent passages and preserve listening-approved files.
