# Owner listening feedback and DSP source integration priority — Nov 24

Feedback session native-all-nine-20261124-b15aa91f53f8, submitted after the 13-group native research lab. Exactly two groups have submitted votes; all other notes are qualitative feedback, not new formal approvals.

- Zaam: B wins, A eliminated. Preserve B (zaam_adlib-full_effects-r5-next-delay-465-0.65-False-1800-0-0.55) and C (zaam-native-tone-finish-a-nov24) as survivors. B close; fix delay.
- Angelic full: submitted tie, no elimination, but explicit note all bad, delay is the issue. Retain all three attempts as history, none approved; prioritize delay replacement rather than tone finish.
- Alchemist: both very close; make B less bright, retain A and B.
- Angelic no delay: reverb bad; keep separate from full delay.
- Club MIC Gate: both good; previous exact B approval remains protected.
- Hop Out: sounds close; isolated chorus almost close.
- Muffle: very close; preserve current anchor.
- Wobbly: displayed A close, convolution still needs work. A is wobbly_adlib-nov24-ir-round-actual-ir-gated-stereo-0.08, earlier round B; keep same identity rather than letter.
- Speakerz full: owner asks whether recreation because almost identical. Current A is excerpt postprocess, B estimated delay cancellation; neither established complete source-to-output native preset.
- Speakerz isolated Flangus: qualitative A preference, needs a little more Flangus. A calibrated direct-only, B native moving-delay diagnostic; do not treat A as a Flangus recreation or formal vote.
- Wait stereo: more stereo.
- Deuce: no new feedback, exact offline v2.5 remains protected and unrecovered.

## Source integration plan (not implemented)

Owner reports having DSP code for Flangus, Delay 3, limiter, compressor and convolver. No DSP source files delivered in this message. Verify provenance and rights to use/modify/distribute before incorporating any third-party implementation or publishing source. Keep supplied proprietary or unlicensed material out of public Git. If source cannot be used, maintain independently implemented compatible engines and parameter mappings.

Priority: Delay 3 and Flangus first, then Convolver, limiter and compressor. Confirm implementation/version, parameter ranges and physical mappings, defaults, smoothing, tempo synchronization, stereo routing, feedback topology, gain staging, oversampling and latency. Decode authorized original FST/FLP parameter values with versioned mappings, preserve unknown fields, no guess presented as exact. Shared engine in SkellCore only where redistribution authorized; link same engine to Sound Match harness and Skell Preset wrapper. Versioned opt-in trial engine, preserve existing factory indices, automation IDs, plugin state and existing approved presets. Compare identical inputs against original FL Studio isolated prints and full chains, report null residual, phase/stereo, band/envelope, repeats/tails, peak, sample-rate/block-size equivalence, host CPU/latency and state recall; validate independent takes and owner listening before promotion.

Do not claim bit-exact FL Studio compatibility based on matching DSP code alone. Exact parameter serialization and mixer-chain order, input level, sample rate, plugin version, tempo, wet/send routing and host behavior also matter. No audio or raw feedback file published; no source integrated yet.
