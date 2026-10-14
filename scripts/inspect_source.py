"""Report the true geometry of each source photo and the layout it forces.

Run this before writing any image prompt. It applies EXIF rotation first, so a
portrait iPhone frame stored as landscape pixels is classified correctly, and it
prints the exact sentences to paste into the generation prompt -- the orientation
rule is then a fact on screen rather than something to remember.

Arguments:
  sources               One or more image paths, or directories to scan
                        (non-recursive) for supported images. Required.
  --canvas N            Square output edge in pixels. Default 2048.
  --min-band FLOAT      Smallest paper band as a fraction of the canvas before
                        the photo is inset instead of bled to the edges.
                        Default 0.16.
  --max-band FLOAT      Largest paper band as a fraction of the canvas.
                        Default 0.42.
  --json                Print machine-readable JSON only, no prose brief.
  --palette-colours N   How many colours to sample from each photograph.
                        Default 6.
  --out PATH            Also write the JSON report to PATH.

Examples:
  python inspect_source.py source/
  python inspect_source.py a.heic b.jpg --json --out plan.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stamp_lib import (
    CANVAS,
    MAX_BAND_FRACTION,
    MIN_BAND_FRACTION,
    describe_palette,
    dominant_palette,
    exif_summary,
    load_image,
    plan_layout,
)

SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}


def collect(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            found += sorted(q for q in p.iterdir() if q.suffix.lower() in SUFFIXES)
        elif p.exists():
            found.append(p)
        else:
            print(f"warning: no such path: {p}", file=sys.stderr)
    return found


def describe(path: Path, canvas: int, min_band: float, max_band: float, colours: int = 6) -> dict:
    img = load_image(path)
    w, h = img.size
    layout = plan_layout(w, h, canvas=canvas, min_band_fraction=min_band, max_band_fraction=max_band)
    band_px = layout.band_box[3] if layout.band_side == "bottom" else layout.band_box[2]
    return {
        "source": str(path),
        "name": path.stem,
        "width": w,
        "height": h,
        "aspect": round(w / h, 4),
        "orientation": layout.orientation,
        "band_side": layout.band_side,
        "band_px": band_px,
        "seam": layout.seam,
        "fit": layout.fit,
        "layout": layout.as_dict(),
        "palette": dominant_palette(img, colours=colours),
        "exif": exif_summary(path),
    }


def brief(rec: dict) -> str:
    side = "BELOW the photograph" if rec["band_side"] == "bottom" else "to the RIGHT of the photograph"
    place = (
        "the complete photograph occupies the TOP of the square"
        if rec["band_side"] == "bottom"
        else "the complete photograph occupies the LEFT of the square"
    )
    fit_note = (
        ""
        if rec["fit"] == "bleed"
        else f"\n  NOTE: {rec['layout']['fit_reason']}. The photo is inset on the paper with "
        "margins instead of bleeding to the canvas edges. It is still uncropped and undistorted."
    )
    return (
        f"{rec['name']}  ({rec['width']}x{rec['height']}, aspect {rec['aspect']}, {rec['orientation']})\n"
        f"  Canvas: {rec['layout']['canvas']}x{rec['layout']['canvas']}, square 1:1.\n"
        f"  Layout: {place}; the paper panel goes {side}.\n"
        f"  Seam: one perfectly straight {rec['seam']} edge, {rec['band_px']}px of paper.\n"
        f"  Photo box: x={rec['layout']['photo_box'][0]} y={rec['layout']['photo_box'][1]} "
        f"w={rec['layout']['photo_box'][2]} h={rec['layout']['photo_box'][3]}\n"
        f"  Palette: {describe_palette(rec['palette'])}"
        f"{fit_note}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", help="image files or directories")
    ap.add_argument("--canvas", type=int, default=CANVAS)
    ap.add_argument("--min-band", type=float, default=MIN_BAND_FRACTION)
    ap.add_argument("--max-band", type=float, default=MAX_BAND_FRACTION)
    ap.add_argument("--palette-colours", type=int, default=6)
    ap.add_argument("--json", action="store_true", help="JSON only")
    ap.add_argument("--out", help="write JSON report here")
    args = ap.parse_args()

    files = collect(args.sources)
    if not files:
        print("error: no readable source images", file=sys.stderr)
        return 1

    records = [
        describe(f, args.canvas, args.min_band, args.max_band, args.palette_colours) for f in files
    ]

    if args.out:
        Path(args.out).write_text(json.dumps(records, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(records, indent=2))
    else:
        landscape = sum(r["band_side"] == "bottom" for r in records)
        portrait = len(records) - landscape
        print(f"{len(records)} source(s): {landscape} with paper below, {portrait} with paper on the right\n")
        for rec in records:
            print(brief(rec))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
