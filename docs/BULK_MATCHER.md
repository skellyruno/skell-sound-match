# Bulk WAV-only matching — public engine, private vocal data

**Status:** offline research tooling only. Source-inferred main/FX roles are hypotheses, not verified FL Studio plugin settings or approved native VST3 presets. The kit intentionally contains no user recordings, no FFT-derived impulse responses, no proprietary `.fst/.flp` data, and no frozen owner-specific models.

## Install and run

From this Sound Match repository root:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[test]"
python -m pytest -q tests/test_wav_only_*.py
```

Use a **private workspace outside the repository** for files and derived models:

```powershell
python -m skell_sound_match.wav_only.skelly_bulk_match scan --workspace C:\SkellyPrivate\match-work C:\SkellyPrivate\uploads\*.zip
python -m skell_sound_match.wav_only.skelly_bulk_match fit --workspace C:\SkellyPrivate\match-work
# Opt-in; more computationally expensive and some modulation stages remain unfit:
python -m skell_sound_match.wav_only.skelly_bulk_match fit --workspace C:\SkellyPrivate\match-work --effects
```

`scan` indexes SHA-256, sample rate, channels and frame counts and caches unchanged ZIP fingerprints. It writes `BATCH_CATALOG.json`, `AUDIO_INDEX.csv`, and `WORK_QUEUE.md` **only in the private workspace**. It refuses ZIP path traversal, overly large or encrypted members. Names provide hints, not proven chain identity. The exact source-to-target performance and zero offset must be checked before interpreting scores.

`fit` selects active-voice training and nonoverlapping same-take holdout windows, estimates a conservative 8-band EQ and linked causal gain-control stage, and writes experimental reports and recipes under `<workspace>/fits`. `--effects` additionally tests isolated wet-only delay/reverb/static-FIR prints when available and leaves rejected attempts unapproved. It does *not* infer proprietary plugin state or automatically compose an owner-approved chain. A later section of the **same take** is not an independent performance validation.

## Apply a frozen standalone recipe to new vocals

The private recipe bundle layout is:

```text
private-recipe-root/
  reports/
    speakerz_source_only_chain.json
    hop_out_source_only_chain.json
    ... future_preset_source_only_chain.json
  recipes/
    learned_filter_a.npz
    ...
```

Keep this directory private. It is *not* part of GitHub, because even fitted filter models may be derived from private sound recordings. Replay uses no wet reference audio:

```powershell
python -m skell_sound_match.wav_only.apply_reconstructed_preset C:\SkellyPrivate\new_dry.wav --recipe C:\SkellyPrivate\private-recipe-root\reports\speakerz_source_only_chain.json --models C:\SkellyPrivate\private-recipe-root\recipes --output C:\SkellyPrivate\previews\speakerz.flac
```

Render **every saved standalone preset onto one or more dry recordings** in one command:

```powershell
python -m skell_sound_match.wav_only.skelly_bulk_match apply-many C:\SkellyPrivate\new_dry.wav --recipe-root C:\SkellyPrivate\private-recipe-root --presets all --output-dir C:\SkellyPrivate\previews
```

Or choose explicit IDs with `--presets speakerz hop_out`. Outputs are append-only by hashed source and recipe; unchanged runs are cached, and tampered outputs require review rather than silent overwrite. Recipes check model SHA-256 before playback; untrusted model JSON and local NPZ files should still be treated as untrusted input. Mono/stereo support is limited to the underlying offline model's constraints.

To apply just a newly **auto-fit main-only** recipe, use:

```powershell
python -m skell_sound_match.wav_only.skelly_bulk_match apply-main C:\SkellyPrivate\new_dry.wav --recipe C:\SkellyPrivate\match-work\fits\speakerz\recipe_<sha>.json --output C:\SkellyPrivate\previews\speakerz-main-only.flac
```

Do not confuse an automatic `fit` recipe (`skelly.wav-only.batch-main.v1`, EQ+leveler only) with a reviewed standalone source-to-effects recipe (`skelly.wav-only.standalone-experiment.v1`, models+stages). Only the latter is discoverable by `apply-many`.

## Private blind listening A/B helper

After a candidate has passed the preliminary safety and held-out metrics, create blinded and level-matched listening clips. The original reference and candidate must be the **same take**, start-aligned, and the same length, sample rate, and channels. This tool does not fix alignment for you.

```powershell
python -m skell_sound_match.wav_only.listening_test C:\SkellyPrivate\original_main.wav C:\SkellyPrivate\candidate.flac --output-dir C:\SkellyPrivate\blind_reviews\speakerz_001 --start 2 --duration 10 --target-lufs -18
```

The command writes `A.flac`, `B.flac`, `LISTENING_SESSION.md`, and `answer_key.json` **only** to the private output directory. The A/B identities are randomized; the answer key is deliberately separate. The clips are matched by integrated LUFS, and a **common** safety attenuation is then applied equally to both files, so one is not made louder by the peak guard. The originals remain untouched, and prior A/B outputs are never silently overwritten. Read the listening instructions and record your preference before revealing the key. The output uses a 4× estimated peak check, not a certified true-peak limiter. If a file is silent or the pair has different durations/channels/rates, the CLI rejects it instead of guessing.

This prepares reproducible A/B material for owner review; it **does not** independently validate sonic accuracy or imply plugin release readiness.

## Many presets, one repeatable review loop

1. Upload ZIPs with any combination of dry, main-only, full-effects, isolated delay/reverb/chorus, `.fst/.flp` if ever available, and notes. The tooling does **not require** the original project or preset.
2. Run `scan` again, then read the private `WORK_QUEUE.md`. Resolve ambiguous labels/duplicate takes; don't automatically cross-pair songs.
3. Run `fit` only for matched dry/main pairs and `fit --effects` when isolated stage prints exist. Save SHA-256, model version, train/holdout spans, safety metrics, and failure cases.
4. Use `apply-many` with **a different dry vocal** to create cross-preset audition renders. Loudness-match candidate/reference for listening only; keep the safety-guarded actual output unmodified.
5. Collect owner A/B judgments (compression, tone, sibilance, effects, stereo, artifacts), retune on the training split, and verify again on disjoint clips and **independent takes** before proposing a native plugin port.

A rejected chorus/full-effects fit remains a failed experiment. Offline EQ/FIR/smoothing can approximate parts of a chain but cannot guarantee identically reproduced dynamic or modulated plugins. The true-peak numbers are 4× estimates, not certified BS.1770 compliance. There are no FL Studio, JUCE, native C++, realtime CPU, plugin-state, UI, or Windows VST3 verification claims for this package.
