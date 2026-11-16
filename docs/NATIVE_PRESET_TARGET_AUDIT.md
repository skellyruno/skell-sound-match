# Native plugin preset bridge — verified source facts, not finished presets 🩻

Inspected GitHub sources of `skellyruno/skell-preset-vst` and `skellyruno/skell-adliblab-vst`, November 2026. Both are independent plugins; this document does not change either repo. Read their own `AGENTS.md` before native changes.

## Skell Preset

- `Source/PluginProcessor.cpp` declares a rack with stable host IDs such as `s1_type`, `s1_on`, `s1_wet`, `s1_p1`..`s1_p16`, and `s1_eqQ1`..`s1_eqQ8` for slot 1, continuing by slot.
- `Source/chain/EffectRegistry.h` enumerates 31 stable type choices (`0=Empty`, `1=EQ`, `2=Compressor`, `8=Exciter`, `11=De-Esser`, `17=Three-Band Dynamics`, `26=8-Band EQ`, `27=FET + Opto`, etc.). The host parameter choice mapping preserves historical IDs; never renumber effects.
- `Source/chain/PresetPackage.h/.cpp` uses `.skellpreset` ZIP containers with `preset.json` schema 2, a 16-slot `Document`, normalized per-slot parameter values, and safety checks. Do **not** confuse raw FL Studio/Waves plugin values with normalized `s1_p1` values.
- A native imported sound must be rendered and tested against the original audio before marking a mapping `verified`.

## Skell AdlibLab

- `Source/PluginProcessor.cpp` declares stable parameters including `outputGain`, `mix`, `slot0On`, `slot0Amount`, `slot0Rate`, `slot0Tone`, `slot0Mix` (and slots 1–3). Its effects are not a generic replacement for the entire Waves/FL Studio Deuce lead-vocal chain.
- The current source does **not** establish a parameter-by-parameter equivalent mapping for SSLChannel, Fresh Air, C6, Soundgoodizer or the original CLA compressors.

## Safety rule added to Skell Sound Match

`recipe_export.create_integration_plan()` now rejects presumed equivalence. A target mapping needs a verified native effect, exact stable parameter ID and matching units. Raw `.fst` state cannot be converted automatically. A recipe marked `not_approved_for_native_recall=true` stays blocked even when some parameters can be mapped.

Deuce and Alchemist remain **research recipes**, not released `.skellpreset` or AdlibLab factory presets. Do not change existing preset IDs, automation ranges or FL Studio sessions to force a translation.
