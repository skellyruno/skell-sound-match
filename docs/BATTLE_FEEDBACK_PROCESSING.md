# Bulk sound battle feedback importer

A new owner-exported `SKELLY_BATTLE_PICKS.json` can be processed **without needing Codex**, by running:

```powershell
python -m skell_sound_match.wav_only.battle_feedback C:\SkellyPrivate\SKELLY_BATTLE_PICKS.json --output-dir C:\SkellyPrivate\battle-results\session-001 --reference-issue deuce-main-r5
```

The `--reference-issue` flag is **explicit manual evidence**, not NLP inference: only supply it when the original/reference has been reported or audited as incorrect. This session's issue is **Deuce original reportedly missing effects**. Results are written as `BATTLE_RESULTS.md` and `BATTLE_NEXT_ROUND_PLAN.json` and will not overwrite existing files.

Validator supports legacy v1 and current v2 schemas, unique group IDs, letters and candidate identities, consistent survivor lists, and non-self-elimination. V2 additionally preserves hashes, eligibility, ratings and session history; unsaved clicks never become owner decisions, and reference-only/blocked rounds never become eligible. It preserves ties with or without elimination. Two survivors can enter another battle with a new challenger; all-three ties require further development/listening first. No candidate is marked owner-approved. Private recordings, learned filters, and audio-embedded HTML are never submitted to GitHub. Test with `python -m pytest -q tests/test_battle_feedback.py`.
