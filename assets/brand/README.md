# Brand assets

Submission material for the Home Assistant brands repository.

| File | Purpose |
|---|---|
| `icon.png` | 256×256 — required for HA brands |
| `icon@2x.png` | 512×512 — HiDPI variant |
| `icon-source-2048.png` | 2048×2048 source, for re-rendering if the design changes |

## Getting the brand shown in HA + HACS

HA brands are served from [`home-assistant/brands`](https://github.com/home-assistant/brands), not from this repo. To get the icon to appear in Home Assistant and HACS:

1. Fork `home-assistant/brands`.
2. Copy `icon.png` and `icon@2x.png` into `custom_integrations/sinilink_udp/`.
3. Open a PR titled something like `Add sinilink_udp`. Their CI validates the images; once it passes a maintainer reviews and merges.
4. Once merged, remove `ignore: brands` from `.github/workflows/validate.yml` in this repo so the HACS validation enforces the icon going forward.

Until the brands PR merges, the HACS workflow here has `ignore: brands` set so CI stays green.
