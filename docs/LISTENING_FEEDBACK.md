> **Nov 24 native wet and exact Gate B:** shared convolution and optional delay ducking implemented, tested with actual Muffle/Wobbly IRs; optimized convolution ~45% faster locally at 256 partition. Recovered exact approved Gate B and compared pinned native gate (not sample-exact; preserve B). Speakerz isolated true wet control verified, unsafe untrimmed fits rejected; Angelic/Zaam/Muffle/Wobbly replacements not accepted. Exact Deuce v2.5 still missing. [Current evidence and next steps](NOV24_NATIVE_WET_GATE_B_CONTINUATION.md).

> **Latest owner decisions carried forward from the Nov 24 handoff (session ec3659f808d5f4e07046f328):** preserve approved Club Gate B listening target; retain both Alchemist sounds; retain Hop Out A, Muffle A and Wobbly B. Angelic no-delay A has incorrect reverb; full Angelic/Zaam delay remain unresolved. Speakerz needs slightly quieter delay. Exact Deuce offline v2.5 remains protected and unrecovered. These supersede older records below; no approval is inferred for the new native gate fit. [Decision identities](NOV24_OWNER_GATE_APPROVAL_AND_WET_ROUTING.md).

> **Nov 24 native validation:** Fixed quiet-vocal calibration and native render identity/geometry checks. Pinned SkellCore gate CLI and C++ tests built on Windows with warnings as errors; actual native fit/replay, four-rate block checks and 302 Python tests passed (1 optional skip). This does not approve a replacement for owner Gate B or verify the VST3 wrapper. [Exact evidence and remaining work](NOV24_NATIVE_GATE_VALIDATION.md).

> **Current continuation, Nov 23:** Six genuinely fresh experimental challengers (Alchemist, Angelic, Muffle, Zaam, Hop Out, Club MIC Gate) pass two measured sections after fixing silence-floor scoring and reconstructing missing tails. One private nine-target HTML has 30 audited clips; Deuce and Speakerz ranking remain blocked, Wobbly retains unresolved R5 attempts. Local suite 262 passed / 1 optional skip; wheel and simulated-DOM transport/export tests passed. Actual browser/FL Studio/native validation remains unverified. [Exact versions, results and next tasks](SIX_CHALLENGERS_AND_LAB_2026-11-23.md).

> **Fresh challenger batch, Nov 23:** New moving-delay spatial trials were rendered across all nine targets. Muffle and Zaam pass the complete-chain screening and improve measured scores against recovered exact R5 survivor excerpts, with identities confirmed by owner session 04ef2153d69dda2e7051355a. Other targets remain rejected or reference-blocked. Protected selections retain their status. Full local suite 255 passed/1 optional skip, followed by 3 targeted spatial tests. [Measurements and continuation](FRESH_SPATIAL_CHALLENGERS_2026-11-23.md).

> **Codex audit, Nov 23:** Fixed emitted-audio eligibility after peak trim, cached-render hash verification and nonfinite window rejection. Added a separate correlation quality gate and active-window stereo diagnostics. All nine target references were measured. Local focused tests 33 passed, 1 optional Pedalboard runtime test skipped, Python wheel built. Protected owner choices remain current. [Audit and next sound tasks](CODEX_INTEGRATION_AUDIT_2026-11-23.md).

## Owner feedback remains protected while generic knob candidates are rejected (Nov 23)

No new owner preferences were supplied after R6. The owner-supplied vox_cloner and fif-ears archives were examined and integrated for research, with no source code copied from the unlicensed vox_cloner ZIP. All six generic trials (Speakerz, Hop Out, Angelic, Muffle, Wobbly, Zaam) failed the stricter absolute stereo/tone/envelope/loudness quality gates; no candidate is approved or substituted for protected R5/R6 survivors. This corrects early provisional aggregate-score improvements that had ignored huge stereo antiphase gaps and actual output levels. See [novelty and evidence](VOX_AND_FIF_EARS_INTEGRATION_2026-11-23.md).

## R6 owner results and R7 listening direction — 2026-11-23\n\nSpeakerz R6 winner **C** (`speakerz-r6-full`), eliminated **A** (`speakerz-old-source`), survivor **B** (`speakerz-r6-gentle`). **Do not replace winner C:** R7 additional air is a new experimental challenger only. Club gate owner **did not choose**: R6 A/B/C all survive; intro has a little gate/noise issue. No owner approval of R7. See [R6/R7 report](R6_R7_FIF_EARS_FEATURE_AUDIT_2026-11-23.md).\n\n## Owner R5 battle decisions (submitted 2026-11-22) + experimental R6\n\nThis section supersedes historical “no new owner feedback” statements below, which remain as records of their earlier status. Deuce C beat A but the original had missing effects; mark its reference **UNVERIFIED_REPAIR_REQUIRED**. Club Gate B beat A, Muffle A beat B, Hop Out C beat A. Alchemist B/C tied with A dropped; Zaam A/B survived with C dropped. Angelic, Wobbly and Speakerz have no eliminated candidate yet. Specific R5 identities and all notes are preserved by the R5 feedback importer; do not conflate R5 candidates with the earlier R4 audio in this workspace.\n\nThe private R6 mini-battle now tests **Club Gate** and **Speakerz full-effects/stereo**, three experimental candidates per original. Both original references are outside voting. No new owner picks for R6 yet; no old champion replaced. See [R6 research report](R6_FOCUSED_SOUND_BATTLE_2026-11-22.md) for measured outcomes and important limits.\n\n> **NEW OWNER FEEDBACK RECEIVED — R5 battle, 2026-11-22:** 9 groups, session `04ef2153d69dda2e7051355a`. Winning candidate IDs and survivor/elimination decisions are preserved in [OWNER_BATTLE_RESULTS_R5_2026-11-22.md](OWNER_BATTLE_RESULTS_R5_2026-11-22.md). Deuce ORIGINAL reportedly lacks the desired effects; do not call its C preference a sound-match approval. The older 'no owner results' text below is historical.

# Listening feedback and current experimental versions

## R7 Angelic stereo-delay investigation

The original Angelic no-delay print has side/mid energy about +6.33 dB. Collapsing that stage to mono loses substantial spatial information. A new causal two-input/two-output echo fitter preserves cross-channel routing and selects echo/repeat/ridge parameters using nested training validation. Its synthetic cross-channel echo regression passes on held-out samples and frozen independent-input replay.

The real Angelic stage trial selected a first echo around 923.76 ms, but unseen wet-relative RMS error was 1.0203 (worse than zero reconstructed wet). It is REJECTED and excluded from the listening lab. The difference between separate modulated prints cannot be assumed to be isolated delay; changing modulation state is a possible confound, not a verified explanation. No original effect state, native setting or full Angelic recreation is claimed.

GitHub Python test workflow for commit `b01860be837872689b51d0dda53272935eeef01e` completed SUCCESS. This confirmation does not cover later R7 source until its own exact-head checks complete. FL Studio inspection was attempted but blocked by an app-approval timeout; no native editor/settings verification occurred.

**Owner feedback:** No new listening results submitted. Earlier Round 2/3 observations are preserved in their existing documents. Do not infer approval from numeric improvements.

## Main and gate experiments

| Target / version | Held-out waveform error: prior → new | Band MAE: prior → new (dB) | Envelope MAE: prior → new (dB) | Status |
|---|---:|---:|---:|---|
| deuce R5C | 1.144 → 0.667 | 3.305 → 3.331 | 4.188 → 4.151 | Experimental holdout pass |
| alchemist R5C | 1.220 → 0.552 | 1.929 → 1.929 | 1.576 → 1.573 | Experimental holdout pass |
| speakerz R5C | 1.129 → 0.487 | 1.332 → 1.305 | 1.314 → 1.278 | Experimental holdout pass |
| hop_out R5C | 1.405 → 0.543 | 1.997 → 1.996 | 0.906 → 0.912 | Experimental holdout pass |

R5C uses a private train-derived phase-only filter after the earlier R4 source-only chain. Declared latency is 2048 samples (46.44 ms at 44.1 kHz), compensated explicitly in the listening crop. Alchemist input remains REC-printed, not untreated dry. The separate Alchemist R5B candidate is also retained for character/brightness review. No native preset, host parameter or factory identity changed.

Club Gate R5 quiet-region heldout MSE decreased from 4.723e-7 to 1.494e-7 versus raw bypass (68.4% reduction). Active error stayed essentially unchanged. The historical near-approved gate was not replaced.

## Adlib recreation research

The original FST metadata indicates chorus, nonlinear dynamics, filters, convolution, reverb/delay and (for Wobbly) flanger/phaser/Panagement. This evidences names/order only; settings and bypass states remain unverified. R6 introduces nonlinear delayed features and a periodically varying filter, with rate/ridge selection on nested TRAIN validation only. Wobbly selected 0.4 Hz; the other three selected the static control. All initial R6 and finishing R6B trials failed the combined quality gate. R6C blends are selected using training audio only.

| Target / R6C | Band MAE (dB) | Envelope MAE (dB) | Waveform relative RMS | Outcome |
|---|---:|---:|---:|---|
| angelic_adlib | 2.547 | 4.371 | 1.372 | REJECTED_REGRESSION |
| muffle_adlib | 3.770 | 2.191 | 1.060 | RESEARCH_HOLDOUT_PASS |
| wobbly_adlib | 2.716 | 2.560 | 1.202 | REJECTED_REGRESSION |
| zaam_adlib | 3.897 | 5.289 | 1.227 | REJECTED_REGRESSION |

Muffle R6C improves envelope and waveform error while band error rises by about 0.097 dB, within the declared 0.1 dB tradeoff tolerance. It is an incomplete filtered/effects recreation, not a completed modulation chain. Its corresponding original adlib print is used; the card remains UNVERIFIED because required creative stages are incomplete. Failed Angelic/Wobbly/Zaam candidates are preserved privately and excluded from voting.

## Verification boundaries

- Local package regression suite: 219 passed (including synthetic DOM/audio playback tests and train/holdout isolation tests). The local partial checkout omits three historical archive/materialization test files; full exact-head GitHub CI is separate.
- Local Python wheel build passed. This is not a VST3 build.
- All embedded clips are decoded back, peak-estimated at 4x and checked for comparable integrated loudness. Hashes bind actual source, reference and candidate versions; candidate timing is checked against its processed reference.
- Real in-app browser access to the listening server timed out even after the server reported listening. Actual browser screenshots, mobile interaction and physical device playback remain UNVERIFIED. Synthetic runtime tests are not browser inspection.
- Four frozen main chains passed finite/peak safety checks on a different source. No independent paired processed target was available, so transfer sound accuracy remains UNVERIFIED. Offline CPU timing and declared latency are recorded privately; no realtime/native CPU claim.
- Native Windows VST3/Quick4/FL Studio validation remains UNVERIFIED. JUCE 8.0.12 was located locally; Sound Match is an offline Python project.
- Never publish owner vocals, embedded HTML, FST/FLP state, private model coefficients or source-derived filters. Keep PR #2 draft; do not merge.
