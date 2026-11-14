"""Run python -m skell_sound_match compare|gainfit|research."""
import argparse
import json
from .core import compare, gain_audio, load_wav, split_audio, optimize_gain


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
    args = p.parse_args()
    if args.command == "compare":
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
