#!/usr/bin/env python3
"""Assemble the seal generation prompt for one photograph.

The invariant two thirds of the prompt -- the ink character, the negative list,
the derived-not-designed clause, the surround -- never changes between photos,
and retyping it by hand is where seals drift: a clause gets dropped, the palette
line gets forgotten, the focus goes unstated and the model defaults to a shrunken
copy of the frame. So the wording lives here, the measured palette is read from
the photograph, and you supply only the judgments a person has to make.

What you decide, per photograph: what the subject is, whether the seal carries
the whole view or just the subject, what comes along with the subject and what
falls away, the outer shape, and which ink leads.

Arguments:
  --photo PATH        The source photograph. Required. Its palette is measured
                      and pasted into the prompt, so this is the real photo, not
                      a preview or a crop.
  --subject TEXT      The subject in one concrete phrase, e.g. "a mound of
                      shaved ice with mandarin segments on a metal plate".
                      Required.
  --focus MODE        subject (default) or whole.
                        subject -- the primary subject carries the seal.
                        whole   -- the composition the camera saw, with its
                                   depth and flanking elements.
  --keep TEXT         For subject focus: what comes along with the subject
                      because it physically supports or contains it -- the
                      plate, the pier, the branch. Repeatable.
  --reduce TEXT       What survives only as a light suggestion, e.g. "one loose
                      horizontal stroke of pale blue for the sea". Repeatable.
  --drop TEXT         What leaves entirely, e.g. "the wooden table and its
                      shadow". Repeatable.
  --shape NAME        none (default), circle, square, arch, ridge, silhouette.
                      none means no outer boundary -- the inked subject alone on
                      the paper, which is the common case.
  --lead-ink TEXT     The dominant ink in words, e.g. "the warm orange of the
                      syrup". Defaults to the palette's largest saturated
                      colour.
  --support TEXT      Supporting inks in words. Repeatable.
  --detail TEXT       Detail that must survive, e.g. "every dot on the pumpkin,
                      its ribbed segments, the curl of the stem". Repeatable.
  --colours N         Palette size to measure. Default 6.
  --out PATH          Write the prompt to a file as well as stdout.

Example:
  python build_prompt.py --photo source/IMG_9001.heic \\
    --subject "a mound of shaved ice with mandarin segments and banana slices" \\
    --focus subject --keep "the metal plate and the spoon lying on it" \\
    --drop "the wooden table and its shadow" \\
    --detail "the shaved-ice texture, the segments, the banana slices" \\
    --lead-ink "the warm orange of the syrup" --support "cream white" \\
    --support "a cool grey for the plate"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stamp_lib import describe_palette, dominant_palette, load_image, stem_seed

SHAPES = {
    "none": "no boundary -- the inked subject alone on the paper",
    "circle": "a circular seal",
    "square": "a square-framed seal",
    "arch": "an arched seal",
    "ridge": "a low panoramic ridge",
    "silhouette": "an irregular silhouette following the subject's own outline",
}

SHAPE_NOTES = {
    "square": (
        "Enclose the motif in one complete, unmistakably square ink border, all four "
        "sides visible. Worn corners, uneven pressure and slight broken ink are wanted; "
        "a clean digital frame, photo mat or generic rectangle is not."
    ),
    "silhouette": (
        "Follow the subject's own outline. Do not enclose it in a rectangle or any "
        "generic frame."
    ),
    "none": (
        "There is no frame, border, roundel or panel of any kind. The impression sits "
        "directly on the paper."
    ),
}

INK_CHARACTER = (
    "INK CHARACTER. Fine, granular and delicate. The impression is built from small ink "
    "grain, stipple and softly broken edges -- ink sitting on absorbent paper, with the "
    "pressure uneven and the edges eaten slightly. {detail} It survives as fine ink marks "
    "and grain, never as smooth photographic tone or gradient."
)

UNEVEN = (
    "UNEVEN PRESSURE. The block did not ink evenly. Some passages took the ink fully and "
    "stay sharp; others are starved, showing the paper through, with strokes broken into "
    "specks and small skips. The two sit close together in one impression, and where the "
    "ink failed is irregular -- not a border effect, not a gradient, not an even "
    "distressed overlay across everything."
)

# How completely the impression came out, as three grades. This is the one clause
# that is meant to differ from photograph to photograph.
#
# A drawer of real stamped papers holds crisp impressions and half-starved ones
# side by side, because a hand inking a pad and pressing it does not repeat
# itself. Asking for the same degree of breakup every time produces the opposite:
# ten seals that are all equally, identically half-legible, which reads as one
# applied effect rather than as a stamp used repeatedly. So the grade is drawn
# from the photograph's own name -- fluctuating across a batch, stable for any
# one photograph -- and --press overrides it.
#
# All three share the same spine: the seal looks very much like the photograph.
# What changes is how much of it resolves.
_LIKENESS = (
    "LIKENESS. The seal should look very much like the photograph -- the same object, the "
    "same arrangement, the same colours, recognisable at a glance as the thing that was "
    "photographed. Do not stylise the subject away or simplify it into a motif; "
    "resemblance is wanted."
)

_GRADE = {
    "crisp": (
        "This impression came out well. It took the ink cleanly and most of it resolves: "
        "the subject is fully legible throughout, with only a few passages going grainy or "
        "thinning at an edge. Still a pressed mark rather than a photograph -- the texture "
        "is ink grain, the edges are slightly eaten -- but a clean, confident one."
    ),
    "normal": (
        "This impression is ordinary: mostly it took the ink, in places it did not. Much of "
        "the subject resolves fully, enough to identify it beyond doubt, while other "
        "passages go coarse, break up, or thin away and let the eye complete them. Do not "
        "render the whole impression at one even level of sharpness -- the unevenness is "
        "what makes this a pressed mark rather than a picture."
    ),
    "starved": (
        "This impression came out dry. Whole passages are starved and broken, showing paper "
        "through, while a few areas still took the ink properly and read clearly. It should "
        "look under-inked rather than incomplete: even at its most broken the subject stays "
        "identifiable, and enough of it resolves that the eye can assemble the rest."
    ),
}

_COARSE = (
    "Slight coarseness throughout is wanted, and every irregularity should be genuinely "
    "irregular -- never a repeated texture, never evenly distributed, never tidy or "
    "symmetrical."
)


def selective_clarity(press: str) -> str:
    return " ".join([_LIKENESS, _GRADE[press], _COARSE])


NOT_POSTER = (
    "NOT a bold graphic reduction. No large flat fields of solid colour, no heavy linocut "
    "slabs, no thick graphic outlines, no poster-style simplification, no screen-print "
    "flattening into a few big shapes. The seal is delicate and fine-grained, not emphatic."
)

NOT_FILTER = (
    "NOT a processed photograph. Do not threshold, halftone-screen, dither, posterise, "
    "duotone, trace or auto-vectorise the photograph. Those keep every pixel and press "
    "nothing."
)

DERIVED = (
    "DERIVED, NOT DESIGNED. This seal comes from one specific photograph. What it does "
    "show must be visible in that photograph, in the same place, in the same number, at "
    "the same relative size, with the same irregularity. Do not add, rearrange, evenly "
    "space, symmetrise, tidy or idealise. Do not substitute generic stock elements -- "
    "identical cypresses, a neat skyline, lollipop figures -- for what the photograph "
    "shows. Omitting the background is allowed; inventing one is not."
)

NOT_BADGE = (
    "This is not a badge, crest, emblem, logo, patch or travel label."
)

SCALE = (
    "Scale and weight: small, light and quiet on the page -- quiet in size and ink weight, "
    "not in colour. It should read as something pressed by hand at stamp size, delicate "
    "rather than emphatic, closer to a botanical stamp or a library mark than to a poster."
)

SURROUND = (
    "Surround: outside the seal's own edge, plain near-white empty paper, with a generous "
    "clean margin on all four sides. Nothing besides the single impression in the frame."
)

OUTPUT = (
    "Output: one seal, centred, filling roughly two thirds of the frame, at high "
    "resolution. Render the impression large in the frame -- a small motif floating in a "
    "large empty field has to be enlarged later and goes soft."
)

NEGATIVE = (
    "Do not include: any caption, lettering, date, place name or number that is not "
    "physically part of the subject; any border or frame around the whole image; drop "
    "shadows; paper texture; torn edges; a mockup; multiple stamps; a sticker, badge, "
    "crest, shield, coat of arms, emblem, logo, patch, roundel, medallion, banner, ribbon, "
    "laurel, scroll or travel-label look; symmetrical, evenly spaced, tidied or idealised "
    "arrangement; generic stock elements standing in for what the photograph shows; "
    "invented content; recoloured or stock-palette inks; bold poster reduction; large flat "
    "colour fields; heavy linocut slabs; thick graphic outlines; glossy finish; clean "
    "vector flatness; smooth gradients or blends; continuous photographic tone; repeated "
    "worm-like squiggles; maze patterns; moire; fingerprint-like loops; ornamental curls; "
    "tiled or uniform noise fill."
)


def _lead_ink_guess(palette: list[dict]) -> str:
    """The largest colour with real chroma, described in the palette's own words."""
    for entry in palette:
        name = entry["name"]
        if "neutral" not in name and "grey" not in name:
            return f"{name} ({entry['hex']})"
    return f"{palette[0]['name']} ({palette[0]['hex']})" if palette else "the dominant colour"


def resolve_press(args) -> str:
    """Pick the impression grade, deriving it from the filename when set to auto.

    Deriving rather than randomising keeps the two properties that matter: a
    batch fluctuates, and any one photograph gives the same answer every time, so
    regenerating a seal you liked does not quietly change its character. The mix
    leans to "normal" because that is the house look; crisp and starved are the
    ends that keep a batch from reading as one setting applied ten times.
    """
    if args.press != "auto":
        return args.press
    # Weighted rather than an even rotation. A dry, badly-taken impression is the
    # exception in a drawer of stamped papers, not one case in three: most come
    # out somewhere between clean and ordinary. Roughly 40 / 45 / 15.
    bucket = stem_seed(Path(args.photo).stem) % 100
    if bucket < 40:
        return "crisp"
    if bucket < 85:
        return "normal"
    return "starved"


def build(args, palette: list[dict]) -> str:
    parts: list[str] = []

    parts.append(
        "Asset type: one small hand-pressed seal impression, inked and affixed to paper -- "
        "the character of a rubber stamp or a Japanese hanko pressed by hand. Alone on "
        "blank paper."
    )
    parts.append(f"Subject: {args.subject.rstrip('.')}.")

    if args.focus == "whole":
        parts.append(
            "FOCUS. Keep the composition the camera saw -- the framing, the depth, the "
            "flanking elements, the ground and sky. The seal carries the whole view."
        )
    else:
        focus = [
            "FOCUS. Center the seal on the subject itself. The seal does not have to carry "
            "the whole photograph; when one subject dominates, let it be the seal and let "
            "the rest fall away."
        ]
        if args.keep:
            focus.append(
                "Keep with it, because they physically carry or contain the subject: "
                + "; ".join(k.rstrip(".") for k in args.keep)
                + "."
            )
        if args.reduce:
            focus.append(
                "Reduce to a light suggestion: "
                + "; ".join(r.rstrip(".") for r in args.reduce)
                + "."
            )
        if args.drop:
            focus.append(
                "Leave out entirely: " + "; ".join(d.rstrip(".") for d in args.drop) + "."
            )
        parts.append(" ".join(focus))

    detail = (
        "Detail survives and is wanted: "
        + "; ".join(d.rstrip(".") for d in args.detail)
        + "."
        if args.detail
        else "Detail survives and is wanted."
    )
    parts.append(INK_CHARACTER.format(detail=detail))
    parts.append(selective_clarity(resolve_press(args)))
    parts.append(UNEVEN)
    parts.append(NOT_POSTER)
    parts.append(NOT_FILTER)
    parts.append(DERIVED)
    parts.append(NOT_BADGE)

    shape_line = f"Shape: {SHAPES[args.shape]}."
    note = SHAPE_NOTES.get(args.shape)
    parts.append(f"{shape_line} {note}" if note else shape_line)

    lead = args.lead_ink or _lead_ink_guess(palette)
    colour = [
        "Colour: take every ink from the photograph itself. Its measured palette is: "
        + describe_palette(palette)
        + ".",
        "Keep each element at its real hue and lightness: pale stucco stays pale, a pastel "
        "sky stays pastel, white stays white -- and anything vivid in the photograph stays "
        "vivid here.",
        f"{lead.rstrip('.')[0].upper()}{lead.rstrip('.')[1:]} leads at its real strength",
    ]
    if args.support:
        support = [s.rstrip(".") for s in args.support]
        listed = (
            support[0]
            if len(support) == 1
            else " and ".join([", ".join(support[:-1]), support[-1]])
        )
        colour[-1] += (
            f", with {listed} kept subordinate to it in how much of the seal they cover"
        )
    colour[-1] += "."
    colour.append(
        "Do not substitute a stock retro-travel or national-park palette, do not deepen or "
        "saturate a colour to make the print look bolder, and equally do not grey down or "
        "wash out a colour that is genuinely strong in the source. The seal may be "
        "colourful; what keeps it quiet is its small size and light ink weight, not a "
        "drained palette."
    )
    parts.append(" ".join(colour))

    parts.append(SCALE)
    parts.append(SURROUND)
    parts.append(OUTPUT)
    parts.append(NEGATIVE)

    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--photo", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--focus", choices=["subject", "whole"], default="subject")
    ap.add_argument("--keep", action="append", default=[])
    ap.add_argument("--reduce", action="append", default=[])
    ap.add_argument("--drop", action="append", default=[])
    ap.add_argument("--shape", choices=sorted(SHAPES), default="none")
    ap.add_argument(
        "--press",
        choices=["auto", "crisp", "normal", "starved"],
        default="auto",
        help="How completely the impression came out. auto varies it per photograph.",
    )
    ap.add_argument("--lead-ink", default=None)
    ap.add_argument("--support", action="append", default=[])
    ap.add_argument("--detail", action="append", default=[])
    ap.add_argument("--colours", type=int, default=6)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    photo = Path(args.photo)
    if not photo.exists():
        print(f"error: no such photo: {photo}", file=sys.stderr)
        return 2

    palette = dominant_palette(load_image(photo), colours=args.colours)
    prompt = build(args, palette)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(prompt + "\n")
        print(f"# written to {args.out}", file=sys.stderr)
    print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
