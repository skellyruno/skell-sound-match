# Skell Sound Match 🩻

Offline audio matching research for the Skelly ecosystem. **No private vocal recordings, unreleased samples, `.fst` files, FL Studio projects, or commercial plugin binaries belong in Git history.** This repository is source code and synthetic tests only.

## Status

- **Core (tested locally):** aligned same-take audio metrics, 5/20/200 ms envelope errors, multi-resolution spectral distance, signed waveform correlation, 4× true-peak estimate, train/validation/test splits, safe training-only gain fitting.
- **Research integrations (experimental, not verified in our environment yet):** optional `auraloss` multi-resolution STFT loss and `dasp-pytorch` distortion drive optimizer. Both need their optional dependencies installed and checked before using for production comparisons.
- **Not integrated:** Deuce or Alchemist proprietary plugin emulation, real-time SkellCore VST3, automatic workstation audio delivery, true blind perceptual matching, GPU performance measurements. Protected prior audio champions are kept outside this repository.

## Start on Windows

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install -e ".[test]"
python -m pytest -q
python -m skell_sound_match compare "reference.wav" "candidate.wav"
python -m skell_sound_match gainfit "dry.wav" "reference.wav"
```

For experimental PyTorch losses/processors: `pip install -e ".[research]"`. Installation and compatibility must be verified on the target PC. The optional experiment is `python -m skell_sound_match distortionfit "dry.wav" "reference.wav" --steps 80`.

**Important:** `compare` intentionally does not automatically shift timestamps, flip polarity, or match gains, because doing so could conceal a real difference. Files must already be the same take, sample-aligned, have equal sample rates/lengths and matching channel counts. Gain fitting trains on the FIRST split; validation and test audio cannot influence that fit. The 4× true-peak meter is an estimate, not certified compliance measurement. A score is never a substitute for a loudness-matched blind A/B listening test.

## Next milestones

1. Verify the experimental PyTorch backends and benchmark CPU usage on Windows.
2. Add robust same-take alignment with confidence reporting and polarity diagnostics.
3. Import the *code only* from existing Skelly VocalMatch experiments after regression tests and license review; do not import uploaded raw voices/presets.
4. Add a non-overwriting rendering pipeline and 15-second lossless listening page for local private audio, alongside held-out evaluation across independent vocal takes.
5. Integrate with Skell Preset only after phase/latency, preset recall, CPU and FL Studio tests.

See `AGENTS.md` for development standards. Third-party projects: [auraloss](https://github.com/csteinmetz1/auraloss) and [dasp-pytorch](https://github.com/csteinmetz1/dasp-pytorch) (both Apache-2.0; install as external packages rather than copying their code).

## Four-render serial-chain diagnostics (tested)

To investigate a recording-stage → main-stage vocal chain **without copying private audio into the repository**:

```powershell
python -m skell_sound_match stages "dry.wav" "recording_only.wav" "main_only.wav" "combined.wav"
```

The tool measures time-varying output/input gain within body, low-mid, mid, presence and consonant bands, separately for dry→main and recording→main. It rejects different sample counts, channels, sample rates, and non-finite data rather than silently aligning or downmixing. Measurements do **not** reveal the proprietary plugins' original settings, prove which plugin caused the difference, or constitute a sound match.

The default early/middle/late windows suit the 18.75-second Deuce experiment; for other clip durations choose `--early START END --middle START END --late START END` in seconds. Use multiple fresh performances before claiming a transferable preset.

## Experimental serial calibration (REC → MAIN)

Use four **sample-aligned** exports of the **same take** to fit an offline model of
REC followed by MAIN. Provide *both* dry→MAIN-only and REC-only→combined
examples. Any proprietary `.fst` state, private voice, or FL Studio project
must remain outside this public repository.

```powershell
python -m skell_sound_match serialfit "dry.wav" "rec_only.wav" "main_only.wav" "rec_plus_main.wav" --model "local_models/serial.json" --report "reports/private/serial.json" --champion "protected_champion.wav"
```

The model uses two regularized FIR filters with bounded, input-conditioned
5 ms gain curves. **This is an offline experiment with lookahead, not a VST3
or a reproduction of proprietary DSP.** The program reports REC, full-chain,
and champion metrics on chronological sections; it explicitly refuses to
promote a candidate automatically. `dry_path_probe` tests whether a fitted
parallel dry term improves held-out audio, but does **not** establish the actual
FL Studio routing; inspect the mixer routing or FLP to verify that.

Optional offline render (no forced limiting or loudness manipulation):

```powershell
python -m skell_sound_match serialrender "dry.wav" "local_models/serial.json" "local_models/serial_trial.wav"
```

Rendering refuses existing output paths, non-finite material, and peaks above
-1 dBTP (4× approximate oversampling). Do not compare the rendered trial by
ear without first matching listening loudness. The model's training/validation
passages may be from the same take, so generalization to other recordings and
true perceptual similarity remain unverified.