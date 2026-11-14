"""Skelly Sound Match: comparison, stage analysis and read-only preset inspection."""
import argparse
import json
from .core import Audio, compare, gain_audio, load_wav, split_audio, optimize_gain


def main() -> None:
    p = argparse.ArgumentParser(description="Skelly Sound Match: safe offline measurements")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("compare", help="Compare reference and same-length candidate WAVs")
    c.add_argument("reference")
    c.add_argument("candidate")
    c.add_argument("--research-loss", action="store_true", help="Optional auraloss MRSTFT metric")
    f = sub.add_parser("gainfit", help="Fit gain on first split; evaluate on other splits")
    f.add_argument("dry")
    f.add_argument("reference")
    f.add_argument("--ceiling", type=float, default=-1.0)
    r = sub.add_parser("distortionfit", help="Experimental dasp-pytorch + auraloss optimizer")
    r.add_argument("dry")
    r.add_argument("reference")
    r.add_argument("--steps", type=int, default=80)
    st = sub.add_parser("stages", help="Diagnose serial record/main chains from four aligned WAV exports")
    for name in ("dry", "recording", "main", "combined"):
        st.add_argument(name)
    st.add_argument("--early", nargs=2, type=float, default=[.8, 6.5])
    st.add_argument("--middle", nargs=2, type=float, default=[7., 12.3])
    st.add_argument("--late", nargs=2, type=float, default=[12.7, 18.3])
    it = sub.add_parser("interactions", help="Compare level- and attack-dependent main-chain transfer from four aligned WAVs")
    for name in ("dry", "recording", "main", "combined"):
        it.add_argument(name)
    it.add_argument("--window", nargs=2, type=float, default=[.9, 6.8])
    serial = sub.add_parser("serialfit", help="Experimental four-render REC->MAIN calibration (offline, private audio)")
    for name in ("dry", "recording", "main", "combined"):
        serial.add_argument(name)
    serial.add_argument("--model", required=True, help="Save JSON model (will not overwrite)")
    serial.add_argument("--report", required=True, help="Save comparison report (will not overwrite)")
    serial.add_argument("--champion", help="Optional previously approved WAV for rejection gate")
    render = sub.add_parser("serialrender", help="Render an experimental serial model to 24-bit mono WAV")
    render.add_argument("dry")
    render.add_argument("model")
    render.add_argument("output")
    fst = sub.add_parser("inspect-fst", help="Read-only inspection of FL Studio mixer-track presets")
    fst.add_argument("paths", nargs="+")
    args = p.parse_args()
    if args.command == "inspect-fst":
        from .fst_inspector import inspect
        out = {"files": [inspect(p) for p in args.paths]}
    elif args.command == "stages":
        from .stages import analyze_stages
        paths = (args.dry, args.recording, args.main, args.combined)
        out = analyze_stages(*(load_wav(p) for p in paths),
                             windows={"early": tuple(args.early),
                                      "middle": tuple(args.middle),
                                      "late": tuple(args.late)})
    elif args.command == "interactions":
        from .interactions import analyze_interactions
        out = analyze_interactions(*(load_wav(p) for p in (args.dry, args.recording, args.main, args.combined)), window=tuple(args.window))
    elif args.command == "serialfit":
        from dataclasses import asdict
        from pathlib import Path
        from .serial_calibration import fit_serial, render_serial, evaluate_sections, probe_direct_path, apply_stage
        paths = (args.dry, args.recording, args.main, args.combined)
        dry, rec, main_only, combined = [load_wav(path) for path in paths]
        train = (.94, min(6.84, len(dry.samples)/dry.rate*.4)) if len(dry.samples)/dry.rate>17 else (.3, .35*len(dry.samples)/dry.rate)
        fit = fit_serial(dry, rec, main_only, combined, train)
        candidate = render_serial(dry, fit)
        duration = len(dry.samples)/dry.rate
        windows = {"training":train,
                   "validation":(max(train[1]+.15,duration*.45),duration*.7),
                   "test":(duration*.74,duration*.95)}
        result = {"serial":evaluate_sections(combined,candidate,windows,train),
                  "rec":evaluate_sections(rec,
                       Audio(apply_stage(dry.samples.mean(axis=1),dry.rate,fit.rec)[:,None],dry.rate),
                       windows,train),
                  "dry_path_probe":probe_direct_path(dry,candidate,combined,train,windows),
                  "model_note":"Offline lookahead; not a real-time VST3, and routing inference is inconclusive", 
                  "approved":False}
        if args.champion:
            champ = load_wav(args.champion)
            result["champion"] = evaluate_sections(combined,champ,windows,train)
            keys=("validation","test")
            result["candidate_passes_champion_gate"] = all(
                result["serial"]["sections"][k]["waveform_corr"] >= result["champion"]["sections"][k]["waveform_corr"] and
                result["serial"]["sections"][k]["envelope20_mae_db"] <= result["champion"]["sections"][k]["envelope20_mae_db"] for k in keys)
        else:
            result["candidate_passes_champion_gate"] = None
        model_path, report_path = Path(args.model),Path(args.report)
        if model_path.exists() or report_path.exists():
            raise FileExistsError('Model or report path already exists; refusing to overwrite')
        model_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.parent.mkdir(parents=True,exist_ok=True)
        model_path.write_text(json.dumps(asdict(fit))+"\n")
        report_path.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
        out=result
    elif args.command == "serialrender":
        from pathlib import Path
        from .serial_calibration import SerialModel,render_serial,safe_for_preview
        import soundfile as sf
        path=Path(args.output)
        if path.exists():
            raise FileExistsError('Output exists: refusing to overwrite')
        data=json.loads(Path(args.model).read_text())
        model=SerialModel(**data)
        y=render_serial(load_wav(args.dry),model)
        if not safe_for_preview(y):
            raise ValueError('Output exceeds -1 dBTP or contains non-finite samples; no WAV written')
        path.parent.mkdir(parents=True,exist_ok=True)
        sf.write(path,y.samples,y.rate,subtype='PCM_24')
        out={"written":str(path),"note":"Experimental offline candidate, not a verified sound match"}
    elif args.command == "compare":
        ref, x = load_wav(args.reference), load_wav(args.candidate)
        out = compare(ref, x)
        if args.research_loss:
            from .experimental import auraloss_mrstft
            out["auraloss_mrstft"] = auraloss_mrstft(ref, x)
    elif args.command == "gainfit":
        raw, ref = load_wav(args.dry), load_wav(args.reference)
        split_raw, split_ref = split_audio(raw), split_audio(ref)
        g = optimize_gain(split_raw["training"], split_ref["training"], ceiling_dbtp=args.ceiling)
        out = {"training_gain_db": g, "ceiling_on_training_dbtp": args.ceiling,
               "important": "Training-only gain, not a complete sound match; validation/test did not influence fitting"}
        for key in ("training", "validation", "test"):
            out[key] = compare(split_ref[key], gain_audio(split_raw[key], g))
    else:
        from .experimental import fit_distortion_drive
        out = fit_distortion_drive(load_wav(args.dry), load_wav(args.reference), args.steps)
    print(json.dumps(out, indent=2, allow_nan=False))

if __name__ == "__main__":
    main()