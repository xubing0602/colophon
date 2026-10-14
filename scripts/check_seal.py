"""Check a generated seal against its source photograph before compositing.

Catches the failures that are easy to miss while a seal looks good on its own:
colour drift (pale stucco coming back brick red, a pastel sunset coming back
saturated navy), over-saturation added to make the print look bolder, and colour
drained out of a seal whose photograph is genuinely vivid.

This is an advisory check on taste, not a correctness gate like verify.py. It
flags what to look at; your eyes decide. Run it after generating a seal and
before spending a composite on it.

Exit code 0 when nothing is flagged, 1 when something is.

Arguments:
  --photo PATH          Source photograph. Required.
  --seal PATH           Generated seal artwork. Required.
  --colours N           Palette size sampled from each image. Default 6.
  --max-hue-drift DEG   How far a seal ink may sit from the nearest photograph
                        hue before it is flagged, in degrees. Default 40.
  --max-sat-loss N      How much less saturated the seal's inks may be than the
                        photograph's before it is flagged. Default 45. Catches
                        restraint spent on the palette instead of on the scale.
  --max-sat-gain N      How much more saturated the seal's inks may be than the
                        photograph's, 0-255. Default 45.
  --max-light-drift N   How far the seal's mean ink lightness may sit from the
                        photograph's, 0-255. Default 55.
  --json                Emit a JSON report instead of prose.

Examples:
  python check_seal.py --photo source/IMG_4705.heic --seal seals/IMG_4705_seal.png
  python check_seal.py --photo a.jpg --seal a_seal.png --max-hue-drift 25
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from stamp_lib import describe_palette, dominant_palette, load_image, prepare_seal


def _hsv(rgb: list[int]) -> tuple[float, float, float]:
    r, g, b = (c / 255.0 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d < 1e-6:
        h = 0.0
    elif mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * (((b - r) / d) + 2)
    else:
        h = 60 * (((r - g) / d) + 4)
    return h, d * 255.0, mx * 255.0


def _hue_gap(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--photo", required=True)
    ap.add_argument("--seal", required=True)
    ap.add_argument("--colours", type=int, default=6)
    ap.add_argument("--max-hue-drift", type=float, default=40.0)
    ap.add_argument("--max-sat-gain", type=float, default=45.0)
    ap.add_argument("--max-sat-loss", type=float, default=45.0)
    ap.add_argument("--max-light-drift", type=float, default=55.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    photo = load_image(args.photo)
    raw = Image.open(args.seal)
    seal = prepare_seal(raw.convert("RGBA") if raw.mode == "RGBA" else raw.convert("RGB"))

    photo_pal = dominant_palette(photo, colours=args.colours)

    # Only the seal's ink matters; its paper ground would dominate the palette.
    arr = np.asarray(seal.convert("RGB")).astype(np.float32)
    ink_mask = arr.mean(axis=2) < 235
    if ink_mask.sum() < 64:
        print("could not find enough ink in the seal to judge")
        return 1
    ink_pixels = arr[ink_mask].astype(np.uint8)
    ink_img = Image.fromarray(ink_pixels.reshape(-1, 1, 3))
    seal_pal = dominant_palette(ink_img.resize((64, 64), Image.NEAREST), colours=args.colours)

    photo_hsv = [_hsv(p["rgb"]) for p in photo_pal]
    findings = []

    for p in seal_pal:
        h, s, _v = _hsv(p["rgb"])
        if s < 25:  # near-neutral inks carry no hue to drift
            continue
        gaps = [_hue_gap(h, ph) for ph, ps, _ in photo_hsv if ps >= 20]
        if gaps and min(gaps) > args.max_hue_drift:
            findings.append(
                f"seal ink {p['hex']} ({p['name']}) sits {min(gaps):.0f}deg from any "
                f"hue in the photograph - likely a substituted stock colour"
            )

    photo_sat = float(np.mean([s for _h, s, _v in photo_hsv]))
    seal_sat = float(np.mean([_hsv(p["rgb"])[1] for p in seal_pal]))
    if seal_sat - photo_sat > args.max_sat_gain:
        findings.append(
            f"seal inks average {seal_sat:.0f} saturation against the photograph's "
            f"{photo_sat:.0f} - the print was punched up"
        )
    elif photo_sat - seal_sat > args.max_sat_loss:
        # The mirror failure, and the quieter one. A seal asked to be small and
        # restrained often comes back with the restraint spent on the palette
        # instead of on the scale, which drains a colour the photograph really
        # has. Worth a look rather than an alarm: a seal that deliberately drops
        # a colourful background and keeps a grey subject lands here too, and
        # that one is correct.
        findings.append(
            f"seal inks average {seal_sat:.0f} saturation against the photograph's "
            f"{photo_sat:.0f} - the colour may have been washed out. Check that "
            f"anything vivid in the source is still vivid here"
        )

    photo_light = float(np.mean([p["lightness"] for p in photo_pal]))
    seal_light = float(np.mean([p["lightness"] for p in seal_pal]))
    if abs(seal_light - photo_light) > args.max_light_drift:
        direction = "darker" if seal_light < photo_light else "lighter"
        findings.append(
            f"seal inks average {seal_light:.0f} lightness against the photograph's "
            f"{photo_light:.0f} - noticeably {direction}"
        )

    report = {
        "photo": args.photo,
        "seal": args.seal,
        "photo_palette": photo_pal,
        "seal_palette": seal_pal,
        "findings": findings,
        "ok": not findings,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1 if findings else 0

    print(f"photo  {describe_palette(photo_pal)}")
    print(f"seal   {describe_palette(seal_pal)}")
    print()
    if findings:
        print(f"FLAGGED  {Path(args.seal).name}")
        for f in findings:
            print(f"    - {f}")
        return 1
    print(f"OK  {Path(args.seal).name}  colours consistent with the source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
