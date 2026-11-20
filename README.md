# Skell Sound Match 🩻

Offline sound-matching research, source archive and reproducible comparison tools for Skelly.

**New agents: read docs/SOUND_MATCHING_HANDOFF_2026-11-20.md first.** It records the approved Deuce v2.5 offline sound, Alchemist source chain and current native trials, the separate Skell Master Deuce Match work, exact branches/PRs, tests and next actions.

## Current decisions

- **Deuce vocal:** offline v2.5 is the owner's preferred sound; D/Max remains the protected rollback. Skell Preset factory 46 is only a native trial because the full v2.3 Sustained Air stage has not yet been ported.
- **Alchemist vocal:** preserve the original seven-slot MAIN chain and Factory 43 native baseline. Factories 48 and 54 are diagnostic candidates only; no newer owner-approved winner.
- **Main Vocals:** show only Alchemist (factory 43) and Deuce (factory 46). Preserve internal historical factory identities and imported My Presets.
- **Skell Master:** Deuce Match is a separate master-bus comparison. Its current post-limiter makeup trial still needs an exact owner-WAV render and listening review.

## Restore the approved research archive

The archive is intentionally public and contains owner-approved historical data with SHA-256 verification. Do not add new raw vocals, FLPs, FSTs or proprietary state files.

~~~powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install -e ".[test]"
python scripts/materialize_archive.py --verify
python scripts/materialize_archive.py --restore --output local_sound_archive
python -m pytest -q
~~~

## Reproducible Deuce v2.5 transfer audit

~~~powershell
python -m skell_sound_match.deuce_transfer_audit new_v23_candidate.wav --target new_original_rec_main.wav --output deuce_v25_new_take_trial.wav --report deuce_v25_new_take_report.json
~~~

The input must already be the same new performance rendered through the frozen v2.3 candidate; the optional target is that exact source through the original REC→MAIN chain. The target is scoring-only. Without it, the tool reports safety only. It refuses overwrites, non-finite/clipped samples and estimated 4× true peak above -1 dBTP. It never auto-promotes a candidate.

The optional research dependencies are deferred experiments, not required for the current workflow. Current integration PR: #2 (draft, base main). The consolidated branch's full suite passed 138 tests on both Ubuntu and Windows in workflow #44794041833. See the handoff for exact provenance and status.