"""Create an architecture-compatible init checkpoint for smoke tests."""

from __future__ import annotations

import os
import sys

import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fgi_eye_tracker.fgi_net import FGI_Net  # noqa: E402


def main():
    out = os.path.join(ROOT, "weights", "fgi_net.pth")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    torch.manual_seed(42)
    model = FGI_Net(num_classes=2)
    # Warm shape check
    with torch.no_grad():
        y = model(torch.randn(1, 3, 224, 224))
        assert y.shape == (1, 2), y.shape
    torch.save({"state_dict": model.state_dict(), "meta": {"source": "architecture_init", "note": "Not paper-trained. Replace with author weights when available."}}, out)
    print(f"Wrote {out}")
    print("Official FGI-Net authors did not publish .pth files on GitHub.")
    print("Email czhang2026@163.com for trained weights, then overwrite this file.")


if __name__ == "__main__":
    main()
