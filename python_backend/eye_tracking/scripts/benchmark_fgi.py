import os
import time
import platform
import json

import numpy as np
import torch

from fgi_eye_tracker.fgi_net import FGI_Net


def main():
    try:
        import psutil
    except ImportError:
        import subprocess
        subprocess.check_call([os.sys.executable, "-m", "pip", "install", "psutil", "thop"])
        import psutil

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = FGI_Net(num_classes=2).to(device).eval()

    n_params = sum(p.numel() for p in model.parameters())
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)

    wpath = os.path.join("weights", "fgi_net.pth")
    ckpt_bytes = os.path.getsize(wpath) if os.path.isfile(wpath) else None
    sd = model.state_dict()
    state_bytes = sum(v.numel() * v.element_size() for v in sd.values())

    macs = None
    flops = None
    try:
        from thop import profile

        x0 = torch.randn(1, 3, 224, 224, device=device)
        macs_v, _ = profile(model, inputs=(x0,), verbose=False)
        macs = float(macs_v)
        flops = macs * 2.0
    except Exception as e:
        print("thop unavailable:", e)

    x = torch.randn(1, 3, 224, 224, device=device)
    with torch.inference_mode():
        for _ in range(15):
            _ = model(x)
        if device.type == "cuda":
            torch.cuda.synchronize()

        times = []
        for _ in range(50):
            t0 = time.perf_counter()
            _ = model(x)
            if device.type == "cuda":
                torch.cuda.synchronize()
            times.append((time.perf_counter() - t0) * 1000.0)

    mem_alloc = None
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            _ = model(x)
            torch.cuda.synchronize()
        mem_alloc = torch.cuda.max_memory_allocated() / (1024**2)

    proc = psutil.Process(os.getpid())
    rss_mb = proc.memory_info().rss / (1024**2)

    info = {
        "system": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
            "cpu_count_logical": os.cpu_count(),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "torch": torch.__version__,
            "device": str(device),
            "cuda_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "model": {
            "input": "1x3x224x224",
            "output": "1x2 (pitch,yaw)",
            "parameters": n_params,
            "parameters_M": round(n_params / 1e6, 4),
            "trainable_params": n_trainable,
            "state_dict_fp32_MB": round(state_bytes / (1024**2), 3),
            "checkpoint_file_MB": round(ckpt_bytes / (1024**2), 3) if ckpt_bytes else None,
        },
        "compute": {
            "MACs": macs,
            "MACs_M": round(macs / 1e6, 3) if macs else None,
            "FLOPs_approx_2xMAC": flops,
            "FLOPs_G": round(flops / 1e9, 4) if flops else None,
            "latency_ms_mean": round(float(np.mean(times)), 3),
            "latency_ms_std": round(float(np.std(times)), 3),
            "latency_ms_p50": round(float(np.percentile(times, 50)), 3),
            "latency_ms_p95": round(float(np.percentile(times, 95)), 3),
            "fps_est": round(1000.0 / float(np.mean(times)), 2),
            "cuda_peak_alloc_MB": round(mem_alloc, 2) if mem_alloc is not None else None,
            "process_rss_MB": round(rss_mb, 1),
            "runs": 50,
            "warmup": 15,
        },
    }
    out = os.path.join("weights", "fgi_benchmark.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    print(json.dumps(info, indent=2))
    print("Wrote", out)


if __name__ == "__main__":
    main()
