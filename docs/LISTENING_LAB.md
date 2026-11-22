# Private, offline HTML blind-listening lab

**Implementation:** `skell_sound_match.wav_only.html_listening_lab`.

Generate a **single self-contained HTML file** with embedded FLAC audio from any number of presets. The HTML works offline; it is **PRIVATE**, because the embedded FLAC clips contain the owner's performances. **Never commit generated HTML, the private input manifest, original WAV/FLACs, downloaded listening results, owner-specific NPZ models or private audio hashes to this public GitHub repository.** Only code, synthetic tests, and general documentation belong here.

## Run

```powershell
python -m pip install -e ".[test]"
python -m skell_sound_match.wav_only.html_listening_lab C:\SkellyPrivate\listening_manifest.json --output C:\SkellyPrivate\four_vocal_blind_lab.html
python -m pytest -q tests/test_html_listening_lab.py
```

Example **private** JSON manifest, with all paths either absolute or relative to the manifest folder:

```json
{
  "groups": [
    {
      "id": "speakerz-main-01",
      "title": "Speakerz · main tone",
      "note": "One aligned performance; no native approval",
      "start": 1.0,
      "seconds": 12.0,
      "clips": [
        {"label": "Original MAIN", "path": "speakerz_main.wav", "kind": "reference"},
        {"label": "Candidate 01", "path": "speakerz_candidate.flac", "kind": "candidate"}
      ]
    }
  ]
}
```

Requirements: **2–12 variants per group**, same sample rate, channels, number of frames and start offset, active vocal, sample rate **32–192 kHz**. A filename matching the song is **not** proof of same performance or alignment; validate provenance and delay separately. The helper refuses mismatches, nonfinite/silent audio, out-of-bounds selections, invalid loudness, and existing destination files. The comparison itself is research, not independent-transfer validation.

The generator measures each selected clip's integrated loudness and brings it to a common target (default −18 LUFS) **for listening only**. It applies the *same* conservative attenuation across all versions to keep their estimated reconstructed peaks below −1.2 dBTP, so playback levels remain matched. This is a 4× oversampled *estimate*, not a certified BS.1770 or hardware true-peak result. Each converted PCM24 FLAC is read back and checked. Historical MP3 inputs remain lossy; wrapping them as FLAC cannot recover lost quality.

In the HTML, switch A/B/C **from the beginning (0:00) when choosing a different letter**, record **best / worst / notes** for every group, then click **Copy feedback** or **Download feedback JSON**. An optional **Reveal identities** control shows the labels after listening. Inputs, votes and labels remain local to the browser; the HTML uses no network requests or external scripts. Local-storage support may vary for `file://` pages; download feedback before closing.

The generator is a standalone companion to `skell_sound_match.wav_only.listening_test` (pairwise FLAC A/B) and `skell_sound_match.wav_only.skelly_bulk_match` (bulk scan, fit, apply-many). It does not replace the strict source-inferred role checks and private workspace requirement of `docs/BULK_MATCHER.md`.

## QA and release gates

- Unit tests use **synthetic audio only** and confirm embedding, safety guard, hash diagnostics, no-overwrite, invalid inputs, group uniqueness and safe HTML escaping.
- Browser functionality was exercised on the **actual generated HTML UI using synthetic audio** in Chromium: render, change letters at ~1.2 s and verify a restart near 0:00, vote best/worst, notes, reveal, JSON export and responsive desktop/mobile rendering.
- A private 2026-11-22 field run embedded **seven groups / 23 normalized lossless clips** across Deuce, Alchemist, Speakerz and Hop Out. The HTML is available privately in the ChatGPT conversation, *not* in the repo.
- **Not verified**: listening approval, independent new-voice transfer, Windows VST3/FL Studio native plugin behavior, system audio device output from a user's actual browser. No factory program is promoted by the generator.

## Round 2: append without recompressing old clips (2026-11-22)

When new vocal/reference candidates arrive, reuse the original **PRIVATE** listening HTML and append only the new rows instead of redoing all previous encoding and blind labels:

```powershell
python -m skell_sound_match.wav_only.html_listening_lab C:\SkellyPrivate\new_adlibs.json --append-from C:\SkellyPrivate\previous_blind_lab.html --output C:\SkellyPrivate\expanded_blind_lab.html
```

This keeps the old A/B/C letter-to-audio mapping and embedded PCM24 FLAC bytes **exactly unchanged**. It encodes only new clips and refuses duplicate group IDs, corrupt base64, unsafe level/peak, overwritten output and excessive embedded audio (85 MB per HTML / up to 100 rounds). When a page approaches the embedded-audio cap, generate a *new chapter*, not one enormous HTML.

The generated page now **restarts at 0:00 on every change to another letter**. Clicking the same letter toggles pause/resume. There is a quick-jump navigation, a reviewed-round counter, an explicit **too close to call** choice, and independent winner/loser/notes. Selecting a version does not reveal its source. If you mark a round uncertain, its conflicting winner/loser votes are cleared; selecting a winner later clears uncertainty. A single letter cannot be both winner and loser.

Every export contains a **session_id** tied to the exact embedded audio and shuffled letters. Browser persistence is keyed by session ID to stop a newly shuffled page from carrying over stale winner/loser choices. Download or copy feedback before closing, particularly when browser `file://` local-storage is restricted. Old v1 page results remain a distinct prior session and are summarized in `docs/ROUND2_FEEDBACK_AND_PRIORITIES_2026-11-22.md`.

Round 2 field page: **12 groups, 35 embedded lossless-normalized clips** (the original seven comparisons unchanged, four additional Club adlibs, and a separate MIC gate group). All new club reference audio and FST/FLP data remain private; this repository stores only the reusable renderer, synthetic tests and written engineering decisions. The offline Chromium smoke test checked desktop/mobile layout, reset from ~1.2 s to ~0.1 s on letter switch, uncertainty/export interactions and no JS console exceptions. This does **not** certify audio output on the owner's system.
