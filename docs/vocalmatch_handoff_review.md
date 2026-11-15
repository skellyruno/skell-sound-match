# VocalMatch handoff evaluation (experimental) 🩻

The user-provided November 2026 Vocal Match handoff contained (1) an offline effect-chain estimator and (2) a cross-validated post-refinement script. The handoff SHA-256 manifest matched all 29 recorded entries. The supplied refinement tool passed its 8 synthetic tests. Its full source remains user-supplied research material; this branch integrates a safety-checked local runner without bundling private audio, vendor preset files or an unreviewed 65 KB estimator.

## Use

Install standard project dependencies and optional fit dependency:

    python -m pip install -e ".[test,fit]"

Keep trusted local vocalmatch_refine.py outside GitHub and run:

    python -m skell_sound_match.refine_bridge --script path/to/vocalmatch_refine.py --previous existing.wav --reference target.wav --out-dir a_new_folder --profile max

The command refuses overwrites and stereo ambience, checks input SHA-256 before/after, checks candidate samples/4x estimated true peak, and enforces a conservative objective quality gate. It NEVER automatically promotes the audio. Output remains local/private. The external script must be trusted: Python scripts execute code.

## Actual 15-second reference evaluation (private audio not committed)

With a protected, listening-approved version as input, **both safe and max profiles passed cross-validation** on five 3-second blocks, separated by 0.25-second gaps. The stronger max profile reduced the later passage's nine-band spectral error from 0.596 to 0.443 dB and its 20 ms envelope error from 0.704 to 0.618 dB. Whole-file gain-adjusted residual fell from -15.39 to -15.67 dB. This is a same-take, out-of-fold result, NOT a test on a different performance or approval by ear.

The handoff's standalone effect-chain estimator also ran on a private real dry/processed vocal pair, but inferred +29.6 dB makeup gain. That result is unsafe to treat as an accurately calibrated 12-slot plugin chain. Do not auto-install its estimated preset. It needs safer gain estimation and independent dry/wet tests first.

The post-refinement uses noncausal filters and smoothing and is offline-only, not ready to be dropped into a real-time Windows VST3. Preserve previous champions and automation IDs. Don't commit any source recording, .fst, FLP, or model fitted on private material.
