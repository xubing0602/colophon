"""Gate finished composites against the invariants that models forget.

Checks the square canvas, the orientation rule, and -- by correlating the output's
photo region against the original -- that the photograph was neither cropped,
distorted, nor replaced. Run it on every output before accepting a batch, whether
the composite came from compose.py or straight from an image model.

The canvas and orientation checks are absolute and never soften. Only the
fidelity test has a choice of metric, because "faithful" means something
different when the photograph was deliberately redrawn.

Exit code 0 when everything passes, 1 when anything fails.

Arguments:
  pairs                 One or more PHOTO:OUTPUT pairs, or a single directory
                        pair given as --source-dir/--output-dir instead. Required
                        unless both directory options are used.
  --source-dir DIR      Directory of source photographs, matched to outputs by
                        filename stem.
  --output-dir DIR      Directory of finished composites, matched by stem.
  --canvas N            Required square edge in pixels. Default 2048.
  --metric MODE         Which fidelity test gates the result.
                          tone       (default) light-for-light agreement. Correct
                                     when the photograph was copied rather than
                                     redrawn, i.e. anything from compose.py.
                          structural edge structure only, ignoring tone and
                                     polarity. Use for the full-composite path
                                     when the photo was redrawn as a print or
                                     line art, which inverts tone and drives the
                                     tone score negative despite a faithful
                                     composition.
                          either     passes if either test passes. For a mixed
                                     batch.
  --min-corr FLOAT      Tone threshold. Default 0.90. Use 0.985 for composites
                        made by compose.py, which should be near-exact.
                        Measured reference points: identical 1.000, blurred 1.000,
                        posterised 0.97, duotone 1.000, heavy print 0.85,
                        line art -0.37 to -0.74, wrong image 0.01.
  --min-structure FLOAT Structural threshold. Default 0.55. Measured reference
                        points: identical 1.000, posterised 0.95-0.98, heavy print
                        0.85, line art 0.70-0.79, cropped to 80% 0.12-0.24,
                        wrong image -0.05 to 0.31.
  --min-band FLOAT      Layout parameter, must match what compose.py used.
                        Default 0.16.
  --max-band FLOAT      Layout parameter, must match what compose.py used.
                        Default 0.50.
  --band-side SIDE      auto | bottom | right. Must match what compose.py used.
                        Default auto.
  --json                Emit a JSON report instead of prose.
  --quiet               Print only failures.

Examples:
  python verify.py --source-dir source --output-dir output
  python verify.py source/a.heic:output/a.webp --min-corr 0.985
  python verify.py --source-dir source --output-dir output --metric structural
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from stamp_lib import CANVAS, MAX_BAND_FRACTION, MIN_BAND_FRACTION, _soften, load_image, plan_layout

SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}
PROBE = 224


def _grey(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L").resize((PROBE, PROBE), Image.LANCZOS), dtype=np.float64)


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    if denom < 1e-9:
        return 0.0
    return float((a * b).sum() / denom)


def correlation(a: Image.Image, b: Image.Image) -> float:
    """Tone correlation: how closely the two images agree light-for-light.

    The right test when the photograph was copied rather than redrawn. Near 1.0
    for compose.py output. Blind to nothing, which is the point.
    """
    return _pearson(_grey(a), _grey(b))


def structural_correlation(a: Image.Image, b: Image.Image) -> float:
    """Edge-structure correlation, ignoring tone and polarity.

    Needed because a print or line-art treatment inverts tone -- dark parts of
    the photograph become pale paper carrying dark lines -- which drives the tone
    correlation NEGATIVE even when the composition is perfectly faithful.
    Comparing gradient magnitude instead asks "is this the same scene, framed the
    same way", which is the only fidelity question that survives stylisation.
    """
    out = []
    for img in (a, b):
        gy, gx = np.gradient(_grey(img))
        out.append(_soften(np.hypot(gx, gy).astype(np.float32)).astype(np.float64))
    return _pearson(out[0], out[1])


def band_stats(img: Image.Image, box: tuple[int, int, int, int]) -> dict:
    x, y, w, h = box
    arr = np.asarray(img.crop((x, y, x + w, y + h)).convert("RGB"), dtype=np.float32)
    lum = arr.mean(axis=2)
    sat = arr.max(axis=2) - arr.min(axis=2)
    return {
        "mean_lightness": round(float(lum.mean()), 1),
        "p10_lightness": round(float(np.percentile(lum, 10)), 1),
        "mean_saturation": round(float(sat.mean()), 2),
    }


def check(photo_path: Path, out_path: Path, args) -> dict:
    result = {"source": str(photo_path), "output": str(out_path), "failures": [], "notes": {}}

    if not out_path.exists():
        result["failures"].append("output missing")
        return result

    src = load_image(photo_path)
    out = Image.open(out_path)
    out = out.convert("RGB")
    ow, oh = out.size
    result["notes"]["output_size"] = [ow, oh]

    if ow != oh:
        result["failures"].append(f"not square: {ow}x{oh}")
    if ow != args.canvas or oh != args.canvas:
        result["failures"].append(f"not {args.canvas}x{args.canvas}: {ow}x{oh}")

    layout = plan_layout(
        *src.size,
        canvas=ow,
        min_band_fraction=args.min_band,
        max_band_fraction=args.max_band,
        band_side=args.band_side,
    )
    result["notes"]["orientation"] = layout.orientation
    result["notes"]["expected_band"] = layout.band_side
    result["notes"]["fit"] = layout.fit

    px, py, pw, ph = layout.photo_box
    region = out.crop((px, py, px + pw, py + ph))
    tone = correlation(src, region)
    struct = structural_correlation(src, region)
    result["notes"]["photo_correlation"] = round(tone, 4)
    result["notes"]["structural_correlation"] = round(struct, 4)

    def passes(t: float, s: float) -> bool:
        if args.metric == "tone":
            return t >= args.min_corr
        if args.metric == "structural":
            return s >= args.min_structure
        return t >= args.min_corr or s >= args.min_structure

    if not passes(tone, struct):
        # Distinguish "wrong side" from "photo altered" -- both look like a low
        # correlation, but only one of them is a layout bug.
        fx, fy, fw, fh = _mirror_layout(layout, ow)
        mirror = out.crop((fx, fy, fx + fw, fy + fh))
        alt_tone = correlation(src, mirror)
        alt_struct = structural_correlation(src, mirror)
        result["notes"]["opposite_side_correlation"] = round(alt_tone, 4)
        if passes(alt_tone, alt_struct):
            wrong = "right" if layout.band_side == "bottom" else "bottom"
            result["failures"].append(
                f"paper band on the wrong side: {layout.orientation} source needs paper "
                f"{layout.band_side}, found it {wrong}"
            )
        elif args.metric == "tone" and struct >= args.min_structure:
            result["failures"].append(
                f"photo region does not match the source by tone (correlation {tone:.3f} < "
                f"{args.min_corr}), but its structure does (structural {struct:.3f}). This is "
                "what a print or line-art treatment looks like: same scene, inverted tone. If "
                "that was intended, re-run with --metric structural."
            )
        else:
            result["failures"].append(
                f"photo region does not match the source (tone {tone:.3f}, structural "
                f"{struct:.3f}); likely cropped, distorted, or a different scene"
            )

    stats = band_stats(out, layout.band_box)
    result["notes"]["band"] = stats
    if stats["mean_lightness"] < 190:
        result["failures"].append(
            f"paper band is too dark (mean lightness {stats['mean_lightness']}); photo may have bled into it"
        )
    if stats["mean_saturation"] > 26:
        result["failures"].append(
            f"paper band is too colourful (mean saturation {stats['mean_saturation']}); expected quiet off-white"
        )

    result["ok"] = not result["failures"]
    return result


def _mirror_layout(layout, canvas: int) -> tuple[int, int, int, int]:
    """The photo box you would get if the paper band were on the other side."""
    _, _, pw, ph = layout.photo_box
    if layout.band_side == "bottom":
        return (canvas - pw, canvas - ph, pw, ph)
    return (0, canvas - ph, pw, ph)


def collect_pairs(args) -> list[tuple[Path, Path]]:
    if args.source_dir and args.output_dir:
        srcs = {p.stem: p for p in Path(args.source_dir).iterdir() if p.suffix.lower() in SUFFIXES}
        outs = {p.stem: p for p in Path(args.output_dir).iterdir() if p.suffix.lower() in SUFFIXES}
        return [(srcs[k], outs[k]) for k in sorted(set(srcs) & set(outs))]

    pairs = []
    for raw in args.pairs:
        if ":" not in raw:
            print(f"error: expected PHOTO:OUTPUT, got {raw}", file=sys.stderr)
            continue
        a, b = raw.rsplit(":", 1)
        pairs.append((Path(a), Path(b)))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", nargs="*", help="PHOTO:OUTPUT pairs")
    ap.add_argument("--source-dir")
    ap.add_argument("--output-dir")
    ap.add_argument("--canvas", type=int, default=CANVAS)
    ap.add_argument("--metric", choices=["tone", "structural", "either"], default="tone")
    ap.add_argument("--min-corr", type=float, default=0.90)
    ap.add_argument("--min-structure", type=float, default=0.55)
    ap.add_argument("--min-band", type=float, default=MIN_BAND_FRACTION)
    ap.add_argument("--max-band", type=float, default=MAX_BAND_FRACTION)
    ap.add_argument("--band-side", choices=["auto", "bottom", "right"], default="auto")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    pairs = collect_pairs(args)
    if not pairs:
        print("error: nothing to verify", file=sys.stderr)
        return 1

    results = [check(s, o, args) for s, o in pairs]
    failed = [r for r in results if not r.get("ok")]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if r.get("ok"):
                if not args.quiet:
                    n = r["notes"]
                    print(
                        f"PASS  {Path(r['output']).name}  {n['output_size'][0]}x{n['output_size'][1]}  "
                        f"{n['orientation']} -> paper {n['expected_band']}  "
                        f"tone {n['photo_correlation']}  struct {n['structural_correlation']}"
                    )
            else:
                print(f"FAIL  {Path(r['output']).name}")
                for f in r["failures"]:
                    print(f"        - {f}")
        print(f"\n{len(results) - len(failed)}/{len(results)} passed")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
