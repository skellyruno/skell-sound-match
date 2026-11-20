"""Optional research backends: NOT a replacement for listening or native DSP tests.

Requires: pip install -e '.[research]'
The dependencies are imported only when this module's functions are called.
"""
from __future__ import annotations
import numpy as np
from .core import Audio


def auraloss_mrstft(reference: Audio, candidate: Audio) -> float:
    """Compute auraloss multi-resolution STFT objective on short, aligned mono excerpts."""
    try:
        import torch
        import auraloss
    except ImportError as exc:
        raise RuntimeError("Install research extras: pip install -e '.[research]'") from exc
    if reference.rate != candidate.rate or reference.samples.shape != candidate.samples.shape:
        raise ValueError("Same sample rate, channel count, and exact length required")
    if reference.samples.shape[1] != 1:
        raise ValueError("Research loss currently supports mono only; never silently downmix")
    if len(reference.samples) < 2048:
        raise ValueError("Audio too short")
    with torch.no_grad():
        ref = torch.tensor(reference.samples.T[None, :, :], dtype=torch.float32)
        out = torch.tensor(candidate.samples.T[None, :, :], dtype=torch.float32)
        loss = auraloss.freq.MultiResolutionSTFTLoss(
            fft_sizes=[256, 1024, 2048], hop_sizes=[64, 256, 512],
            win_lengths=[256, 1024, 2048])
        value = float(loss(out, ref).item())
    if not np.isfinite(value):
        raise ValueError("Non-finite auraloss metric")
    return value


def fit_distortion_drive(dry: Audio, reference: Audio, steps: int = 80) -> dict:
    """Experimental dasp-pytorch drive optimization; CPU, offline, mono, no render claims.

    Fits only a single distortion parameter. Not an estimate of a proprietary
    compressor, or a recreation of an entire reference chain.
    """
    try:
        import torch
        import dasp_pytorch
        import auraloss
    except ImportError as exc:
        raise RuntimeError("Install research extras: pip install -e '.[research]'") from exc
    if dry.rate != reference.rate or dry.samples.shape != reference.samples.shape or dry.samples.shape[1] != 1:
        raise ValueError("Inputs must be aligned, mono, and have identical shape/rate")
    if not (4 <= steps <= 1000):
        raise ValueError("Steps must be between 4 and 1000")
    # Explicitly fit only the first ~2 seconds (training); never claim held-out accuracy.
    n = min(len(dry.samples), 2 * dry.rate)
    if n < 2048:
        raise ValueError("Insufficient audio")
    x = torch.tensor(dry.samples[:n, 0][None, None, :], dtype=torch.float32)
    y = torch.tensor(reference.samples[:n, 0][None, None, :], dtype=torch.float32)
    raw_drive = torch.nn.Parameter(torch.zeros(1))
    optim = torch.optim.Adam([raw_drive], lr=0.07)
    loss_fn = auraloss.freq.MultiResolutionSTFTLoss(
        fft_sizes=[256, 1024, 2048], hop_sizes=[64, 256, 512],
        win_lengths=[256, 1024, 2048])
    for _ in range(steps):
        optim.zero_grad()
        drive = 24 * torch.sigmoid(raw_drive)
        pred = dasp_pytorch.functional.distortion(x, dry.rate, drive)
        loss = loss_fn(pred, y)
        if not torch.isfinite(loss):
            raise RuntimeError("Non-finite training loss")
        loss.backward()
        optim.step()
    return {"drive_db": float((24 * torch.sigmoid(raw_drive)).detach().item()),
            "training_loss": float(loss.detach().item()),
            "steps": steps, "training_seconds": n / dry.rate,
            "status": "experimental; NOT listening validated"}
