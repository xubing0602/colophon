"""Composite a source photograph and a generated seal into the final square archive image.

This is the deterministic path. The image model draws only the seal; this script
owns every mechanical rule, so the photograph is copied at its true aspect ratio,
never cropped, never repainted, and the canvas is exactly square. Landscape
sources get the paper band below, portrait sources get it on the right.

Arguments:
  --photo PATH            Source photograph (jpg/png/heic/webp/tiff). Required.
  --out PATH              Output file. .webp or .png by extension. Required.
  --seal PATH             Generated seal artwork. Ink on a light background, or
                          RGBA with real transparency. Omit for caption only.
  --caption TEXT          Caption line. Repeat for multiple lines; a literal \n
                          inside one value also splits lines. Optional.
  --canvas N              Square output edge in pixels. Default 2048.
  --quality N             WebP quality. Default 92.
  --min-band FLOAT        Smallest paper band as a fraction of the canvas before
                          the photo is inset instead of bled. Default 0.16.
  --max-band FLOAT        Largest paper band as a fraction of the canvas. Default 0.50.
  --band-side SIDE        auto | bottom | right. auto applies the house rule:
                          paper below a landscape source, right of a portrait one.
                          Override only when the user explicitly asks for the
                          other arrangement. Default auto.
  --seal-raw              Skip white-balancing, background knockout, and trimming
                          of the seal art. Use when the seal is already clean RGBA.
  --seal-knockout N       How many luminance levels below the seal's own measured
                          background the knockout ramp ends, so no faint rectangle
                          of generated paper survives the multiply blend. Default
                          16. Raise it if a pale background box is still visible;
                          lower it if faint ink washes are being erased. 0 disables.
  --no-manifest           Do not write the sidecar .json of these settings.
  --print-layout          Print the resolved layout and exit without rendering.

Variation. Everything below is sampled per photo so that no two composites in a
batch look mechanically identical. Passing a flag explicitly always overrides the
sampled value, which is what keeps revisions predictable.

  --variation FLOAT       How far a sample may travel from the house default,
                          0-1. 0 reproduces the old fixed look exactly. Default
                          0.65.
  --seed N                Seed for this photo's look. Defaults to a checksum of
                          the photo's filename, so each photo differs from its
                          neighbours while any one photo re-composites
                          identically every time. Pass a seed to reroll.
  --layout MODE           split | stacked | auto. split sets the seal and caption
                          side by side, stacked puts the caption under the seal.
                          Sampled; auto picks split for a bottom band.
  --anchor POS            Where the seal-and-caption group sits inside the paper
                          band: center, left, right, top, bottom, top-left,
                          top-right, bottom-left, bottom-right. Sampled.
  --seal-scale FLOAT      Multiplier on the seal-and-caption group size, applied
                          after fitting. Use 0.9 for "make it 10% smaller".
                          Sampled in 0.90-1.08.
  --seal-strength FLOAT   Ink density, 0-1. Below 1 fades the seal. Sampled in
                          0.88-1.00.
  --seal-wear FLOAT       Uneven pressure across the seal, 0-1. Default 0: the
                          seal is printed exactly as generated. The prompt asks
                          the model for uneven pressure directly and it does the
                          job better, because it can vary the impression while
                          drawing it, where this filter can only take ink away
                          afterwards. Raise it only to rescue a seal that came
                          back mechanically even -- 0.5 is a moderate press, 0.8
                          a dry one. Applied at final size.
  --caption-size N        Caption point size. Sampled around canvas x 0.0175.
  --caption-opacity FLOAT Caption ink opacity, 0-1. Sampled in 0.72-0.90. Pale by
                          design: a typewriter ribbon lays down little ink, and a
                          caption as strong as the seal competes with it. The ink
                          is then darkened as needed so what lands on the paper
                          clears a minimum contrast -- faint is the look,
                          illegible is a bug.
  --caption-align SIDE    left | center | right. Ragged edge of the caption block,
                          and which edge of the seal it hangs from when stacked.
                          Sampled.
  --caption-tracking F    Extra pixels between glyphs. Sampled in 0-2.6.
  --caption-spacing F     Line spacing multiple. Sampled in 1.46-1.82.
  --caption-weight F      Stroke weight, -1 to 1, in units of about one final
                          pixel. Sampled in 0 to 0.30, never negative: these
                          faces are light already, and paleness belongs in the
                          ink colour rather than in the stroke.
  --caption-texture F     Mottled ink loss across the glyphs, 0-1. Sampled in
                          0.16-0.40, and capped further when the ink is pale.
  --caption-jitter F      Per-glyph baseline and sidebearing wobble, 0-1, as a
                          hand-typed line sits unevenly. Sampled in 0-0.55.
  --caption-strike F      Per-glyph variation in how hard the key landed, 0-1.
                          A typewriter never inks two letters alike; uniform ink
                          is what gives rendered text away.
  --caption-wear FLOAT    Ribbon condition, 0-1, in one knob. 0 is a fresh
                          ribbon -- even and reasonably dark; 1 is a dry one --
                          pale, patchy and visibly uneven letter to letter. It
                          sets opacity, texture, strike and weight together,
                          because on a real machine those go together; setting
                          any of them explicitly overrides this for that one
                          property. Sampled around 0.30, skewed fresh.
  --caption-tint F        How far the caption ink moves toward the seal's own
                          colour, 0-1. Sampled as 0 about half the time, else
                          0.55-0.9.
  --caption-color R,G,B   Neutral caption ink, before tinting. Default 86,82,76.
  --font PATH             Caption face. Pins one face, overriding the sample.
                          Append "#N" to pick one face inside a .ttc collection,
                          e.g. ".../Courier.ttc#1" for Courier Bold.
                          The sampled pool is small and entirely monospaced:
                          Courier New and Courier. Book serifs read as a modern
                          publication, plain sans monospace as a code editor, and
                          American Typewriter -- proportionally spaced and finely
                          drawn -- as a thin spindly serif under this format's
                          pale ink. Bold Couriers are available here but kept out
                          of the sample: they read as emphatic next to a quiet
                          seal.
  --paper-tone R,G,B      Paper base colour. Sampled around 237,235,229.
  --grain FLOAT           Fine fibre amplitude. Sampled in 1.2-2.6. 0 disables.
  --mottle FLOAT          Low-frequency tone variation. Sampled in 1.6-3.6.
                          0 disables.
  --paper-seed N          Seed for the paper texture. Sampled.
  --margin FLOAT          Paper margin as a fraction of the canvas. Sampled in
                          0.060-0.105.
  --gap FLOAT             Gap between seal and caption as a fraction of the
                          canvas. Sampled around 0.10 split, 0.055 stacked.

Examples:
  python compose.py --photo source/IMG_1443.heic --seal tmp/seal.png \\
      --caption "Rice University" --caption "Houston, United States" --caption "DEC 2016" \\
      --out output/IMG_1443.webp

  python compose.py --photo source/a.jpg --seal tmp/seal.png --seal-scale 0.9 \\
      --anchor bottom-left --out output/a.webp

  # reroll the look, or pin it down entirely
  python compose.py --photo source/a.jpg --seal tmp/seal.png --seed 41 --out output/a.webp
  python compose.py --photo source/a.jpg --seal tmp/seal.png --variation 0 --out output/a.webp
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from stamp_lib import (
    CANVAS,
    MAX_BAND_FRACTION,
    MIN_BAND_FRACTION,
    WEBP_QUALITY,
    available_faces,
    dominant_ink,
    load_image,
    make_paper,
    multiply_paste,
    plan_layout,
    distress_seal,
    legible_ink,
    ribbon,
    prepare_seal,
    render_caption,
    sample_variation,
    save_webp,
    stem_seed,
    tint_caption,
)

ANCHORS = {
    "center": (0.5, 0.5),
    "left": (0.0, 0.5),
    "right": (1.0, 0.5),
    "top": (0.5, 0.0),
    "bottom": (0.5, 1.0),
    "top-left": (0.0, 0.0),
    "top-right": (1.0, 0.0),
    "bottom-left": (0.0, 1.0),
    "bottom-right": (1.0, 1.0),
}


def parse_tone(text: str) -> tuple[int, int, int]:
    parts = [int(p) for p in text.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("paper tone must be R,G,B")
    return tuple(max(0, min(255, p)) for p in parts)  # type: ignore[return-value]


def caption_lines(values: list[str] | None) -> list[str]:
    lines: list[str] = []
    for value in values or []:
        lines += [part for part in value.replace("\\n", "\n").split("\n")]
    return [ln for ln in lines if ln.strip()]


def build_group(
    seal: Image.Image | None,
    caption: Image.Image | None,
    mode: str,
    gap: int,
    align: str = "left",
) -> Image.Image:
    """Arrange seal and caption on white, ready to be multiplied into the paper."""
    parts = [p for p in (seal, caption) if p is not None]
    if not parts:
        return Image.new("RGB", (1, 1), (255, 255, 255))
    if len(parts) == 1:
        return parts[0]

    if mode == "split":
        w = seal.size[0] + gap + caption.size[0]
        h = max(seal.size[1], caption.size[1])
        group = Image.new("RGB", (w, h), (255, 255, 255))
        group.paste(seal, (0, (h - seal.size[1]) // 2))
        group.paste(caption, (seal.size[0] + gap, (h - caption.size[1]) // 2))
        return group

    # Stacked: the caption hangs off the seal's own edge rather than floating
    # centred under it, which is what makes the pair read as one printed block.
    w = max(seal.size[0], caption.size[0])
    h = seal.size[1] + gap + caption.size[1]
    group = Image.new("RGB", (w, h), (255, 255, 255))
    if align == "right":
        group.paste(seal, (w - seal.size[0], 0))
        group.paste(caption, (w - caption.size[0], seal.size[1] + gap))
    elif align == "center":
        group.paste(seal, ((w - seal.size[0]) // 2, 0))
        group.paste(caption, ((w - caption.size[0]) // 2, seal.size[1] + gap))
    else:
        group.paste(seal, (0, 0))
        group.paste(caption, (0, seal.size[1] + gap))
    return group


def fit_group(
    group: Image.Image,
    box_w: int,
    box_h: int,
    scale: float,
    fill: bool = False,
    what: str = "group",
) -> Image.Image:
    """Scale to fit a box, optionally enlarging to fill it.

    `fill` is the difference between "make sure this is not too big" and "make
    this the size it is supposed to be". The seal wants the second: how many
    pixels the generated art happens to contain is an accident of the image
    model, and it must not decide how large the seal sits on the paper. Without
    it a seal whose inked area came back small simply stays small -- a speck in
    the middle of the panel, with nothing in the output to say why.

    The caption block wants the first. It is rendered at a real point size, so
    enlarging it would blow the type up past the size that was chosen for it.
    """
    factor = min(box_w / group.size[0], box_h / group.size[1])
    if not fill:
        factor = min(factor, 1.0)
    factor *= scale
    if abs(factor - 1.0) < 1e-3:
        return group
    if factor > 1.6:
        # Enlarging is the right call -- a correctly sized soft seal beats a
        # sharp speck -- but past this much the art itself is the problem, and
        # the fix is to regenerate it larger rather than to accept the blur.
        print(
            f"note: {what} art is small ({group.size[0]}x{group.size[1]}px) and is "
            f"being enlarged {factor:.1f}x to fill its panel. Consider regenerating "
            f"it at a higher resolution."
        )
    new_size = (max(1, int(round(group.size[0] * factor))), max(1, int(round(group.size[1] * factor))))
    return group.resize(new_size, Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--photo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seal")
    ap.add_argument("--caption", action="append")
    ap.add_argument("--canvas", type=int, default=CANVAS)
    ap.add_argument("--quality", type=int, default=WEBP_QUALITY)
    ap.add_argument("--min-band", type=float, default=MIN_BAND_FRACTION)
    ap.add_argument("--max-band", type=float, default=MAX_BAND_FRACTION)
    ap.add_argument("--band-side", choices=["auto", "bottom", "right"], default="auto")
    ap.add_argument("--seal-raw", action="store_true")
    ap.add_argument("--seal-knockout", type=float, default=16.0)
    ap.add_argument("--no-manifest", action="store_true")
    ap.add_argument("--print-layout", action="store_true")

    # Variation. Everything below is sampled per photo unless given explicitly;
    # an explicit flag always wins, so revisions stay predictable.
    ap.add_argument("--variation", type=float, default=0.65)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--layout", choices=["auto", "split", "stacked"], default=None)
    ap.add_argument("--anchor", choices=sorted(ANCHORS), default=None)
    ap.add_argument("--seal-scale", type=float, default=None)
    ap.add_argument("--seal-strength", type=float, default=None)
    ap.add_argument("--seal-wear", type=float, default=None)
    ap.add_argument("--caption-size", type=int, default=None)
    ap.add_argument("--caption-opacity", type=float, default=None)
    ap.add_argument("--caption-align", choices=["left", "center", "right"], default=None)
    ap.add_argument("--caption-tracking", type=float, default=None)
    ap.add_argument("--caption-spacing", type=float, default=None)
    ap.add_argument("--caption-weight", type=float, default=None)
    ap.add_argument("--caption-texture", type=float, default=None)
    ap.add_argument("--caption-jitter", type=float, default=None)
    ap.add_argument("--caption-strike", type=float, default=None)
    ap.add_argument("--caption-wear", type=float, default=None)
    ap.add_argument("--caption-tint", type=float, default=None)
    ap.add_argument("--caption-color", type=parse_tone, default=(86, 82, 76))
    ap.add_argument("--font", default=None)
    ap.add_argument("--paper-tone", type=parse_tone, default=None)
    ap.add_argument("--grain", type=float, default=None)
    ap.add_argument("--mottle", type=float, default=None)
    ap.add_argument("--paper-seed", type=int, default=None)
    ap.add_argument("--margin", type=float, default=None)
    ap.add_argument("--gap", type=float, default=None)
    args = ap.parse_args()

    photo = load_image(args.photo)
    layout = plan_layout(
        *photo.size,
        canvas=args.canvas,
        min_band_fraction=args.min_band,
        max_band_fraction=args.max_band,
        band_side=args.band_side,
    )

    if args.print_layout:
        print(json.dumps(layout.as_dict(), indent=2))
        return 0

    # Sample one look. The seed defaults to the photo's own filename, so each
    # photo in a batch differs from its neighbours while any single photo
    # re-composites identically every time.
    seed = args.seed if args.seed is not None else stem_seed(Path(args.photo).stem)
    var = sample_variation(
        seed, args.variation, layout.band_side, available_faces(args.font)
    )

    def chosen(explicit, sampled):
        return sampled if explicit is None else explicit

    mode = chosen(args.layout, var.layout)
    if mode == "auto":
        mode = "split" if layout.band_side == "bottom" else "stacked"
    base_gap = 0.10 if mode == "split" else 0.055
    gap_frac = args.gap if args.gap is not None else base_gap * var.gap
    anchor = chosen(args.anchor, var.anchor)
    margin_frac = chosen(args.margin, var.margin)
    seal_scale = chosen(args.seal_scale, var.seal_scale)
    seal_strength = chosen(args.seal_strength, var.seal_strength)
    caption_align = chosen(args.caption_align, var.caption_align)

    # 1. Paper fills the whole canvas, so the band and any inset margin share one
    #    continuous surface with no visible tiling.
    paper_tone = chosen(args.paper_tone, var.paper_tone)
    canvas_img = make_paper(
        args.canvas,
        args.canvas,
        tone=paper_tone,
        grain=chosen(args.grain, var.grain),
        mottle=chosen(args.mottle, var.mottle),
        seed=chosen(args.paper_seed, var.paper_seed),
    )

    # 2. The photograph, resized only uniformly, never cropped.
    px, py, pw, ph = layout.photo_box
    canvas_img.paste(photo.resize((pw, ph), Image.LANCZOS), (px, py))

    # 3. Seal and caption, pressed into the band.
    seal_img = None
    if args.seal:
        raw = Image.open(args.seal)
        seal_img = raw.convert("RGBA") if raw.mode == "RGBA" else raw.convert("RGB")
        seal_img = prepare_seal(
            seal_img,
            white_balance=not args.seal_raw,
            trim=not args.seal_raw,
            knockout=0.0 if args.seal_raw else args.seal_knockout,
        )

    lines = caption_lines(args.caption)
    caption_img = None
    if lines:
        base_size = max(12, int(round(args.canvas * 0.0175)))
        size = args.caption_size or max(10, int(round(base_size * var.caption_size_scale)))
        # An explicit --caption-wear re-derives the whole ribbon, so the four
        # properties stay consistent with each other; individual flags still win
        # over it, which is what makes "drier, but keep it this dark" expressible.
        rib = ribbon(args.caption_wear) if args.caption_wear is not None else None
        cap_opacity = chosen(
            args.caption_opacity, rib["opacity"] if rib else var.caption_opacity
        )
        cap_texture = chosen(
            args.caption_texture, rib["texture"] if rib else var.caption_texture
        )
        cap_weight = chosen(
            args.caption_weight, rib["weight"] if rib else var.caption_weight
        )
        cap_strike = chosen(
            args.caption_strike, rib["strike"] if rib else var.caption_strike
        )

        tint = chosen(args.caption_tint, var.caption_tint)
        colour = tint_caption(
            args.caption_color,
            dominant_ink(seal_img) if seal_img is not None else None,
            tint,
        )
        # Last word on legibility, after both the tint and the sampled opacity are
        # known. A pale seal ink and a low opacity are each fine alone and
        # invisible together, and only here is the actual paper tone in hand.
        colour = legible_ink(colour, cap_opacity, paper_tone)
        caption_img = render_caption(
            lines,
            chosen(args.font, var.font),
            size,
            color=colour,
            opacity=cap_opacity,
            line_spacing=chosen(args.caption_spacing, var.caption_line_spacing),
            tracking=chosen(args.caption_tracking, var.caption_tracking),
            align=caption_align,
            weight=cap_weight,
            texture=cap_texture,
            jitter=chosen(args.caption_jitter, var.caption_jitter),
            strike=cap_strike,
            seed=var.noise_seed,
        )

    if seal_img is not None or caption_img is not None:
        bx, by, bw, bh = layout.band_box
        margin = int(round(args.canvas * margin_frac))
        inner_w = max(1, bw - 2 * margin)
        inner_h = max(1, bh - 2 * margin)

        if seal_img is not None:
            cap_w = caption_img.size[0] if (caption_img is not None and mode == "split") else 0
            gap_px = int(round(args.canvas * gap_frac)) if caption_img is not None else 0
            seal_box_w = max(1, inner_w - cap_w - gap_px) if mode == "split" else inner_w
            seal_box_h = inner_h if mode == "split" else int(round(inner_h * 0.62))
            seal_img = fit_group(seal_img, seal_box_w, seal_box_h, 1.0, fill=True, what="seal")
            # Distress last, at the size the seal will actually be printed. Ink
            # that breaks up at source resolution averages back into haze when
            # the seal is scaled down; done here, the specks are the specks the
            # viewer sees.
            seal_img = distress_seal(
                seal_img,
                wear=chosen(args.seal_wear, var.seal_wear),
                seed=var.noise_seed + 17,
            )

        group = build_group(
            seal_img, caption_img, mode, int(round(args.canvas * gap_frac)), caption_align
        )
        group = fit_group(group, inner_w, inner_h, seal_scale)

        ax, ay = ANCHORS[anchor]
        gx = bx + margin + int(round((inner_w - group.size[0]) * ax))
        gy = by + margin + int(round((inner_h - group.size[1]) * ay))
        multiply_paste(canvas_img, group, (gx, gy), strength=seal_strength)

    out = Path(args.out)
    if out.suffix.lower() == ".webp":
        save_webp(canvas_img, out, quality=args.quality)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        canvas_img.save(out)

    if not args.no_manifest:
        manifest = {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(args).items()}
        manifest["resolved_layout"] = layout.as_dict()
        manifest["resolved_mode"] = mode
        manifest["resolved_variation"] = var.as_dict()
        manifest["seed"] = seed
        manifest["source_size"] = list(photo.size)
        out.with_suffix(out.suffix + ".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(
        f"{out}  {canvas_img.size[0]}x{canvas_img.size[1]}  "
        f"{layout.orientation} -> paper {layout.band_side}  ({layout.fit})  "
        f"seed {seed}  {mode}/{anchor}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
