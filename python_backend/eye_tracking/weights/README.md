# Weights

Place a trained FGI-Net checkpoint here as:

```text
fgi_net.pth
```

Expected formats:
- bare `state_dict`
- `{"state_dict": ...}`
- `{"model": ...}`

## Important

The official repo [CZ178/FGI-Net](https://github.com/CZ178/FGI-Net) currently publishes **architecture only** (`FGI_Net.py`), not downloadable pretrained `.pth` files.

For paper-trained weights, contact the authors (README: `czhang2026@163.com`).

Until then you can generate a structural init checkpoint for wiring/smoke tests:

```powershell
python scripts\init_weights.py
```
