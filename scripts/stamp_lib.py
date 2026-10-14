"""Shared geometry, paper, and ink helpers for the photo-stamp archive skill.

Every mechanical invariant of the format lives here so that no language model has
to remember it:

  * the canvas is always square (default 2048x2048);
  * the source photograph is never cropped and never distorted;
  * a landscape source gets its paper band BELOW, a portrait source gets it on
    the RIGHT;
  * EXIF orientation is applied before anything else, so a rotated iPhone frame
    is not mistaken for the opposite orientation.

Not a CLI. Use inspect_source.py, compose.py, or verify.py.
"""

from __future__ import annotations

import unicodedata
import zlib
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

try:  # HEIC/HEIF support for iPhone originals
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover - optional at import time
    pass

CANVAS = 2048
WEBP_QUALITY = 92

# A band thinner than this reads as an accident rather than a design choice, so
# a near-square source falls back to an inset photo instead of a sliver.
MIN_BAND_FRACTION = 0.16
MAX_BAND_FRACTION = 0.50

# An aspect this close to 1:1 counts as square. A square source cannot fill the
# canvas and still leave a band, so it is inset instead; the tolerance only
# decides which of those two paths a nearly-square frame takes.
SQUARE_TOLERANCE = 0.06

# A tinted caption is blended toward the seal's ink, and a pale seal -- tan,
# straw, dusty pink -- would carry the caption to the edge of legibility. Small
# text is never allowed to also be dim, so a tinted caption is darkened back to
# at most this luminance.
CAPTION_MAX_LUMINANCE = 132.0

# Hue names for the measured palette lines, as (upper bound in degrees, name).
# Read with the first match wins, so the list must end past 360.
_HUE_NAMES = [
    (15, "red"),
    (40, "orange"),
    (70, "yellow"),
    (95, "yellow-green"),
    (160, "green"),
    (195, "teal"),
    (255, "blue"),
    (285, "violet"),
    (320, "purple"),
    (345, "pink"),
    (361, "red"),
]

# Curated caption faces. The sampler picks among whichever of these the machine
# actually has.
#
# The pool is deliberately small and entirely monospaced. The house voice is a
# note typed on a machine, and three families that look plausible in a specimen
# all fail in the composite:
#
#   Book serifs (Iowan Old Style, Baskerville, Charter, Cochin, Bodoni) read as a
#   modern publication. Beside a hand-pressed seal they turn the caption into a
#   design element rather than into something typed and left there.
#
#   Plain sans monospace (Menlo, Monaco, Andale Mono, DejaVu Sans Mono) reads as
#   a code editor.
#
#   American Typewriter, at every weight. It is proportionally spaced and finely
#   drawn, and under this format's pale ink it reads as a thin spindly serif
#   rather than as typing -- the Light weights collapse into ghost outlines
#   outright. Proportional spacing is most of the problem: the even rhythm of a
#   monospaced face is a large part of what makes a caption read as struck by a
#   machine rather than set by a designer.
#
# Bold weights (Courier Bold, Courier New Bold) are excluded from the sample but
# remain available through --font: they read as emphatic next to a quiet seal,
# which is the opposite of the intent, but they are the right answer if a caption
# ever has to sit on a busy panel.
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/System/Library/Fonts/Courier.ttc#0",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def load_image(path: str | Path) -> Image.Image:
    """Open an image with EXIF rotation already applied, in RGB."""
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def orientation_of(width: int, height: int) -> str:
    aspect = width / height
    if abs(aspect - 1.0) <= SQUARE_TOLERANCE:
        return "square"
    return "landscape" if aspect > 1.0 else "portrait"


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------


@dataclass
class Layout:
    canvas: int
    orientation: str
    band_side: str  # "bottom" | "right"
    fit: str  # "bleed" | "inset"
    photo_box: tuple[int, int, int, int]  # x, y, w, h
    band_box: tuple[int, int, int, int]  # x, y, w, h
    seam: str  # "horizontal" | "vertical"
    fit_reason: str = ""  # why bleed or inset was chosen

    def as_dict(self) -> dict:
        return asdict(self)


def plan_layout(
    width: int,
    height: int,
    canvas: int = CANVAS,
    min_band_fraction: float = MIN_BAND_FRACTION,
    max_band_fraction: float = MAX_BAND_FRACTION,
    band_side: str = "auto",
) -> Layout:
    """Decide where the photo and the paper band go, without distorting anything.

    The photo bleeds to the canvas edges when its own aspect ratio leaves a band
    of a usable size. When it would not (a near-square or extremely elongated
    source) the photo is inset on the paper instead -- still uncropped, still at
    its true aspect ratio.

    band_side is "auto" (the house rule: paper below a landscape source, right of
    a portrait one) or an explicit "bottom"/"right" override.
    """
    orientation = orientation_of(width, height)
    if band_side == "auto":
        band_side = "right" if orientation == "portrait" else "bottom"
    seam = "vertical" if band_side == "right" else "horizontal"

    min_band = int(round(canvas * min_band_fraction))
    max_band = int(round(canvas * max_band_fraction))

    bled = "photo aspect leaves a usable band, so the photo bleeds to the canvas edges"

    if band_side == "bottom":
        natural_photo_h = int(round(canvas * height / width))
        band = canvas - natural_photo_h
        if min_band <= band <= max_band:
            return Layout(
                canvas, orientation, band_side, "bleed",
                (0, 0, canvas, natural_photo_h), (0, natural_photo_h, canvas, band), seam, bled,
            )

        reason = _inset_reason(band, min_band)
        band = min(max(band, min_band), max_band)
        area_h = canvas - band
        photo_w, photo_h = _fit_inside(width, height, canvas, area_h, inset=0.055 * canvas)
        photo_box = ((canvas - photo_w) // 2, (area_h - photo_h) // 2, photo_w, photo_h)
        return Layout(
            canvas, orientation, band_side, "inset", photo_box, (0, area_h, canvas, band), seam, reason,
        )

    natural_photo_w = int(round(canvas * width / height))
    band = canvas - natural_photo_w
    if min_band <= band <= max_band:
        return Layout(
            canvas, orientation, band_side, "bleed",
            (0, 0, natural_photo_w, canvas), (natural_photo_w, 0, band, canvas), seam, bled,
        )

    reason = _inset_reason(band, min_band)
    band = min(max(band, min_band), max_band)
    area_w = canvas - band
    photo_w, photo_h = _fit_inside(width, height, area_w, canvas, inset=0.055 * canvas)
    photo_box = ((area_w - photo_w) // 2, (canvas - photo_h) // 2, photo_w, photo_h)
    return Layout(
        canvas, orientation, band_side, "inset", photo_box, (area_w, 0, band, canvas), seam, reason,
    )


def _inset_reason(band: int, min_band: int) -> str:
    if band < min_band:
        return "the source is close to square, so a full-bleed photo would leave only a sliver of paper"
    return "the source is very elongated, so a full-bleed photo would leave more paper than picture"


def _fit_inside(w: int, h: int, box_w: float, box_h: float, inset: float = 0.0) -> tuple[int, int]:
    """Largest (w, h) with the same aspect ratio fitting inside the box."""
    avail_w = max(1.0, box_w - 2 * inset)
    avail_h = max(1.0, box_h - 2 * inset)
    scale = min(avail_w / w, avail_h / h)
    return max(1, int(round(w * scale))), max(1, int(round(h * scale)))


# --------------------------------------------------------------------------
# paper
# --------------------------------------------------------------------------


def _soften(a: np.ndarray) -> np.ndarray:
    """A cheap separable 1-2-1 blur, so the fibres are grain rather than pixel snow.

    PIL's GaussianBlur refuses float32 images, and a 3-tap kernel is all this
    needs at single-digit amplitude.
    """
    k = np.array([0.25, 0.5, 0.25], dtype=np.float32)
    padded = np.pad(a, ((0, 0), (1, 1)), mode="reflect")
    a = k[0] * padded[:, :-2] + k[1] * padded[:, 1:-1] + k[2] * padded[:, 2:]
    padded = np.pad(a, ((1, 1), (0, 0)), mode="reflect")
    return k[0] * padded[:-2, :] + k[1] * padded[1:-1, :] + k[2] * padded[2:, :]


def make_paper(
    width: int,
    height: int,
    tone: tuple[int, int, int] = (237, 235, 229),
    grain: float = 1.9,
    mottle: float = 2.6,
    seed: int = 0,
) -> Image.Image:
    """Warm off-white archival paper: fine, low-contrast, nearly smooth.

    Deliberately restrained. The failure mode to avoid is coarse, furry,
    embossed, streaky or visibly tiled texture, so both noise layers are kept at
    single-digit amplitude and the low-frequency layer is isotropic.
    """
    rng = np.random.default_rng(seed)
    base = np.zeros((height, width, 3), dtype=np.float32)
    base[:, :] = np.array(tone, dtype=np.float32)

    if mottle > 0:
        small_h = max(2, height // 48)
        small_w = max(2, width // 48)
        low = rng.normal(0.0, 1.0, (small_h, small_w)).astype(np.float32)
        low_img = Image.fromarray(low, mode="F").resize((width, height), Image.BICUBIC)
        low_full = np.asarray(low_img)
        low_full = low_full / (np.abs(low_full).max() + 1e-6)
        base += (low_full * mottle)[:, :, None]

    if grain > 0:
        fine = _soften(rng.normal(0.0, grain, (height, width)).astype(np.float32))
        base += fine[:, :, None]
        # a hint of chroma so the fibres are not pure luminance noise
        base[:, :, 0] += rng.normal(0.0, grain * 0.25, (height, width)).astype(np.float32)
        base[:, :, 2] -= rng.normal(0.0, grain * 0.25, (height, width)).astype(np.float32)

    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), mode="RGB")


# --------------------------------------------------------------------------
# seal ink
# --------------------------------------------------------------------------


# How much colour it takes to be treated as ink rather than as paper during the
# knockout. Generated paper is near-neutral, so a low threshold is enough; set it
# much higher and a warm-white background would survive as a faint tint.
KNOCKOUT_CHROMA_GUARD = 26.0


def prepare_seal(
    seal: Image.Image,
    white_balance: bool = True,
    trim: bool = True,
    trim_tolerance: int = 10,
    knockout: float = 16.0,
) -> Image.Image:
    """Normalise a generated seal to ink-on-white, then crop to its ink.

    Accepts either RGBA art with real transparency or the far more common case:
    RGB art the image model rendered on its own paper-ish background. In the
    latter case the background is rescaled to white so a multiply blend drops it
    cleanly onto the real paper.
    """
    if seal.mode == "RGBA":
        flat = Image.new("RGB", seal.size, (255, 255, 255))
        flat.paste(seal, mask=seal.split()[3])
        seal = flat
    else:
        seal = seal.convert("RGB")

    arr = np.asarray(seal).astype(np.float32)

    if white_balance:
        # Per channel, map the paper (the bright bulk of the image) to pure white.
        for c in range(3):
            hi = float(np.percentile(arr[:, :, c], 97.5))
            if hi > 1.0:
                arr[:, :, c] *= 255.0 / hi
        arr = np.clip(arr, 0, 255)

    if knockout > 0:
        # Lift the seal's own background all the way to pure white. Without this
        # the multiply blend leaves a faint rectangle of the generated paper
        # sitting on top of the real paper. The threshold is measured from the
        # art itself, since every model returns a different shade of "paper".
        #
        # The ramp has to end BELOW the background's own spread, not at its
        # centre: half of a background centred on the white point would still
        # come through grey. So the ramp tops out one knockout step under the
        # measured level, and everything above it clamps to white.
        lum = arr.mean(axis=2)
        background = _background_level(lum)
        hi = background - knockout
        lo = hi - knockout
        alpha = np.clip((lum - lo) / max(1.0, hi - lo), 0.0, 1.0)

        # Luminance alone cannot tell pale ink from paper, and on a seal built
        # from fine stipple over a pale wash -- a blue sky, a straw ground -- it
        # gets the answer badly wrong: the wash sits in the same brightness range
        # as the background and gets lifted away with it, taking a fifth of the
        # impression's ink and most of its lightest passages.
        #
        # Chroma separates them. Generated paper is neutral; a pale wash is not,
        # however light it is. So colour is protected from the knockout in
        # proportion to how far it is from grey, and only the genuinely neutral
        # near-background pixels are lifted to white.
        chroma = arr.max(axis=2) - arr.min(axis=2)
        alpha *= np.clip(1.0 - chroma / KNOCKOUT_CHROMA_GUARD, 0.0, 1.0)

        arr = arr * (1.0 - alpha[:, :, None]) + 255.0 * alpha[:, :, None]

    if trim:
        lum = arr.mean(axis=2)
        ink = lum < (255 - trim_tolerance)
        if ink.any():
            rows = np.where(ink.any(axis=1))[0]
            cols = np.where(ink.any(axis=0))[0]
            arr = arr[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]

    return Image.fromarray(arr.astype(np.uint8), mode="RGB")


def _blobs(shape: tuple[int, int], rng, scale: int) -> np.ndarray:
    """A smooth random field at roughly `scale` pixels per blob, normalised 0..1.

    Built small and scaled up rather than blurred down: a bicubic enlargement of
    a 20x20 grid is genuinely low-frequency, where dozens of blur passes over
    full-resolution noise are both slow and still faintly pixel-flavoured.
    """
    h, w = shape
    gh, gw = max(2, h // max(1, scale)), max(2, w // max(1, scale))
    small = rng.random((gh, gw)).astype(np.float32)
    field = np.asarray(
        Image.fromarray((small * 255).astype(np.uint8), mode="L").resize((w, h), Image.BICUBIC),
        dtype=np.float32,
    ) / 255.0
    lo, hi = float(field.min()), float(field.max())
    return (field - lo) / max(1e-6, hi - lo)


def distress_seal(seal: Image.Image, wear: float = 0.5, seed: int = 0) -> Image.Image:
    """Press the seal unevenly, so one impression is part crisp and part starved.

    A seal that came back from an image model is usually inked with perfect
    evenness, which is the one thing a hand-pressed stamp never is. Real pressure
    varies across the block: some passages take the ink fully, others are starved
    and show the paper through, and the two sit inches apart in the same
    impression.

    The mechanism is a spatially varying ink threshold rather than an overlaid
    noise texture, and that distinction is what keeps it from looking like a
    filter. Under a starved press the *light* tones are what disappear first --
    thin lines break up, edges get eaten, solid cores survive and stay
    recognisable. Subtracting a threshold from ink coverage reproduces exactly
    that ordering, so the wear lands where a press would put it.

    Roughly half the seal is left untouched at any wear level. Distress that
    covers everything reads as uniform grunge; distress that covers part of the
    impression reads as pressure.

    wear  0..1. 0 returns the seal unchanged. 0.5 is the house default.
    """
    if wear <= 0:
        return seal

    wear = float(min(1.0, wear))
    rgb = seal.convert("RGB")
    arr = np.asarray(rgb).astype(np.float32)
    h, w = arr.shape[:2]

    # Ink coverage: 0 is bare paper, 1 is the densest ink in the impression.
    lum = arr.mean(axis=2)
    coverage = np.clip(1.0 - lum / 255.0, 0.0, 1.0)
    if coverage.max() < 0.02:
        return seal

    rng = np.random.default_rng(seed)
    span = max(h, w)

    # Three scales, because real uneven pressure is not one frequency: broad
    # regions that took less ink, patchiness within them, and grain at the size
    # of the paper's own tooth.
    broad = _blobs((h, w), rng, max(8, span // 7))
    patchy = _blobs((h, w), rng, max(4, span // 22))
    # Grain stays at the scale of the paper's tooth -- one to three pixels at the
    # size the seal is actually printed. Blur it further and starved passages turn
    # into a soft grey wash, which reads as a faded print rather than as ink that
    # broke up. This is why distress is applied at final size, after the seal has
    # been fitted: specks introduced at source resolution average away in the
    # resize and arrive as haze.
    grain = 0.7 * _soften(rng.random((h, w)).astype(np.float32)) + 0.3 * _blobs(
        (h, w), rng, 3
    )
    g_lo, g_hi = float(np.percentile(grain, 1.0)), float(np.percentile(grain, 99.0))
    grain = np.clip((grain - g_lo) / max(1e-6, g_hi - g_lo), 0.0, 1.0)

    # Two jobs, kept separate on purpose. `starved` says WHERE the press failed
    # to take ink -- broad regions, patchy within them. `speck` says HOW the ink
    # breaks up once it is failing -- at the scale of the paper's tooth. Blend
    # them into one field and starved areas merely go grey, which reads as a
    # faded print; multiply them and the same areas fragment into specks and
    # skips, which reads as a stamp.
    starved = 0.62 * broad + 0.38 * patchy
    s_lo, s_hi = float(np.percentile(starved, 1.0)), float(np.percentile(starved, 99.0))
    starved = np.clip((starved - s_lo) / max(1e-6, s_hi - s_lo), 0.0, 1.0)

    # Below the cut the impression is left crisp. That untouched fraction is the
    # point of the whole function: distress everywhere is grunge, distress in
    # part of the seal is pressure. It sits above half deliberately -- the seal
    # has to stay legible as the thing it depicts, and blank paper inside the
    # impression costs likeness faster than it buys character.
    cut = float(np.percentile(starved, 58.0))
    where = np.clip((starved - cut) / max(1e-6, 1.0 - cut), 0.0, 1.0) ** 1.25

    speck = np.clip(grain, 0.0, 1.0)

    # Scale everything to this seal's own ink density rather than to an absolute
    # value: a dense dark impression and a pale delicate one need very different
    # numbers to break up by the same visible amount, and only a relative
    # threshold gives one wear setting the same meaning on both.
    dense = float(np.percentile(coverage[coverage > 0.05], 92.0))

    # The speck term deliberately overshoots that density. A threshold that only
    # approaches the darkest ink lightens the impression evenly; one that passes
    # it lifts ink away completely in places, and those gaps are what the eye
    # reads as a skip.
    threshold = dense * wear * (0.38 * where + 1.45 * where * speck + 0.10 * speck)

    # Light ink goes first, dense ink survives -- the signature of a dry press.
    eaten = np.clip((coverage - threshold) / np.maximum(1e-6, 1.0 - threshold), 0.0, 1.0)

    # A few outright pinholes where the ink failed to transfer at all, confined to
    # the starved regions so they read as skips rather than as speckle scattered
    # evenly over the block.
    pinholes = (speck > 0.95 - 0.06 * wear) & (where > 0.55)
    eaten = np.where(pinholes, eaten * (1.0 - 0.55 * wear), eaten)

    ratio = (eaten / np.maximum(coverage, 1e-6))[:, :, None]
    out = 255.0 - (255.0 - arr) * ratio
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")


def _background_level(lum: np.ndarray) -> float:
    """The luminance of the seal's paper, as the histogram peak of the bright half.

    A percentile would drift with how much of the frame the motif covers; the
    mode of the bright half does not.
    """
    median = float(np.median(lum))
    hist, edges = np.histogram(lum, bins=48, range=(0.0, 255.0))
    centres = (edges[:-1] + edges[1:]) / 2.0
    bright = centres >= median
    if not bright.any() or hist[bright].max() == 0:
        return float(np.percentile(lum, 90))
    return float(centres[bright][int(np.argmax(hist[bright]))])


def multiply_paste(base: Image.Image, ink: Image.Image, xy: tuple[int, int], strength: float = 1.0) -> None:
    """Press ink into paper with a multiply blend, in place.

    Multiply is what makes white backgrounds disappear and lets the paper grain
    show through the ink, which is why the seal reads as pressed rather than
    pasted.
    """
    x, y = xy
    w, h = ink.size
    region = base.crop((x, y, x + w, y + h))
    a = np.asarray(region).astype(np.float32) / 255.0
    b = np.asarray(ink.convert("RGB")).astype(np.float32) / 255.0
    if strength < 1.0:
        b = 1.0 - (1.0 - b) * strength
    out = np.clip(a * b, 0.0, 1.0) * 255.0
    base.paste(Image.fromarray(out.astype(np.uint8), mode="RGB"), (x, y))


# --------------------------------------------------------------------------
# caption
# --------------------------------------------------------------------------


def parse_face(spec: str) -> tuple[str, int]:
    """Split a "path#index" face spec into its path and collection index."""
    if "#" in spec:
        path, _, idx = spec.rpartition("#")
        if idx.isdigit():
            return path, int(idx)
    return spec, 0


def face_exists(spec: str) -> bool:
    return Path(parse_face(spec)[0]).exists()


def load_font(size: int, spec: str | None = None) -> ImageFont.FreeTypeFont:
    candidates = [spec] if spec else []
    candidates += FONT_CANDIDATES
    for cand in candidates:
        if not cand:
            continue
        path, index = parse_face(cand)
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=index)
            except OSError:
                continue
    return ImageFont.load_default(size)


# Characters that routinely appear in place names and routinely go missing from a
# face. Mapped to the nearest thing that always renders.
_GLYPH_FALLBACKS = {
    "ʼ": "'", "ʻ": "'", "’": "'", "‘": "'",
    "“": '"', "”": '"', "–": "-", "—": "-",
    "…": "...", " ": " ", "′": "'", "″": '"',
}


@lru_cache(maxsize=32)
def _font_charset(path: str, index: int) -> frozenset[int] | None:
    """Every codepoint a face can actually draw, or None if it cannot be read."""
    try:
        from fontTools.ttLib import TTCollection, TTFont
    except ImportError:
        return None
    try:
        font = TTCollection(path).fonts[index] if path.lower().endswith(".ttc") else TTFont(path)
        points: set[int] = set()
        for table in font["cmap"].tables:
            points |= set(table.cmap.keys())
        return frozenset(points)
    except Exception:  # noqa: BLE001 - coverage checking is advisory
        return None


def safe_text(text: str, spec: str | None) -> tuple[str, list[str]]:
    """Replace characters the chosen face cannot draw, so nothing renders as tofu.

    A missing glyph is silent -- it just prints an empty box -- and place names are
    exactly where the odd character lives, so this substitutes rather than trusting
    every face to be complete. Returns the safe text and whatever was replaced.
    """
    if not text:
        return text, []
    path, index = parse_face(spec) if spec else (None, 0)
    charset = _font_charset(path, index) if path and Path(path).exists() else None

    out: list[str] = []
    swapped: list[str] = []
    for ch in text:
        if charset is None or ord(ch) in charset or ch in "\n\t":
            out.append(ch)
            continue
        repl = _GLYPH_FALLBACKS.get(ch)
        if repl is None:
            # Strip accents as a last resort: "ā" -> "a" beats an empty box.
            stripped = "".join(
                c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c)
            )
            repl = stripped if stripped and all(ord(c) in charset for c in stripped) else ""
        swapped.append(f"{ch!r}->{repl!r}")
        out.append(repl)
    return "".join(out), swapped


SUPERSAMPLE = 3


def render_caption(
    lines: list[str],
    font_path: str | None,
    size: int,
    color: tuple[int, int, int] = (86, 82, 76),
    opacity: float = 0.86,
    line_spacing: float = 1.62,
    tracking: float = 0.0,
    align: str = "left",
    weight: float = 0.0,
    texture: float = 0.0,
    jitter: float = 0.0,
    strike: float = 0.0,
    seed: int = 0,
) -> Image.Image:
    """Render a typewriter caption as ink-on-white, ready for multiply_paste.

    Drawn at SUPERSAMPLE scale and reduced, which is what allows sub-pixel
    control of stroke weight and a soft letterpress edge rather than crisp
    screen antialiasing.

    weight   -1..1, thinner to fatter, in units of about one final pixel.
    texture  0..1, mottled ink loss across the glyphs.
    jitter   0..1, per-glyph baseline and sidebearing wobble, as a hand-typed
             line sits slightly unevenly.
    strike   0..1, per-glyph variation in how hard the key landed. A typewriter
             never inks two letters identically -- one comes out full, the next
             half-starved where the ribbon was thin -- and that unevenness
             letter by letter is most of what separates typed text from set
             type. Uniform ink is the giveaway that text was rendered.
    """
    if not lines:
        return Image.new("RGB", (1, 1), (255, 255, 255))

    rng = np.random.default_rng(seed)
    ss = SUPERSAMPLE
    font = load_font(size * ss, font_path)

    safe_lines, swapped = [], []
    for line in lines:
        fixed, changes = safe_text(line, font_path)
        safe_lines.append(fixed)
        swapped += changes
    lines = safe_lines
    if swapped:
        print(f"note: caption characters the face cannot draw were replaced: {', '.join(swapped)}")

    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    ascent, descent = font.getmetrics()
    line_h = int(round((ascent + descent) * line_spacing))
    track_px = tracking * ss

    widths = []
    for line in lines:
        w = probe.textlength(line, font=font) + track_px * max(0, len(line) - 1)
        widths.append(w)
    width = int(round(max(widths + [1.0])))
    height = line_h * len(lines)
    pad = int(round(size * ss * 0.25))  # room for jitter and dilation

    # Ink is drawn white-on-black so the mask can be grown, eroded, and eaten
    # into with plain array maths before it becomes colour.
    mask = Image.new("L", (width + 2 * pad, height + 2 * pad), 0)
    d = ImageDraw.Draw(mask)
    wobble = jitter * size * ss * 0.05

    for i, line in enumerate(lines):
        y0 = pad + i * line_h
        if align == "right":
            x0 = pad + (width - widths[i])
        elif align == "center":
            x0 = pad + (width - widths[i]) / 2.0
        else:
            x0 = pad

        if track_px or wobble or strike > 0:
            x = x0
            for ch in line:
                dx = rng.normal(0.0, wobble) if wobble else 0.0
                dy = rng.normal(0.0, wobble) if wobble else 0.0
                # Space carries no ink, so letting it draw a strike value would
                # only waste random numbers and desynchronise the sequence.
                if strike > 0 and not ch.isspace():
                    # Floored well above zero: a typewriter's weakest strike is
                    # faint, never absent, and a missing letter reads as a bug
                    # rather than as character.
                    hit = float(np.clip(rng.normal(1.0, 0.32 * strike), 1.0 - 0.62 * strike, 1.0))
                else:
                    hit = 1.0
                d.text((x + dx, y0 + dy), ch, font=font, fill=int(round(255 * hit)))
                x += probe.textlength(ch, font=font) + track_px
        else:
            d.text((x0, y0), line, font=font, fill=255)

    if weight > 0:
        for _ in range(max(1, int(round(weight * ss)))):
            mask = mask.filter(ImageFilter.MaxFilter(3))
    elif weight < 0:
        for _ in range(max(1, int(round(-weight * ss)))):
            mask = mask.filter(ImageFilter.MinFilter(3))

    out_size = (max(1, (width + 2 * pad) // ss), max(1, (height + 2 * pad) // ss))
    small = mask.resize(out_size, Image.LANCZOS)
    arr = np.asarray(small).astype(np.float32) / 255.0

    if texture > 0:
        # Applied here, at final size, and not before the reduction. Mottling
        # introduced at supersample scale is averaged away by the LANCZOS step:
        # it survives only as a slight overall lightening, which is the opposite
        # of the intent -- a dry ribbon makes letters patchy, not uniformly grey.
        #
        # Two scales, because ribbon ink fails at two: fine grain across the
        # strokes, and larger soft patches where a whole letter or word came out
        # weak.
        fine = _soften(rng.random(arr.shape).astype(np.float32))
        f_lo, f_hi = float(np.percentile(fine, 2.0)), float(np.percentile(fine, 98.0))
        fine = np.clip((fine - f_lo) / max(1e-6, f_hi - f_lo), 0.0, 1.0)
        patch = _blobs(arr.shape, rng, max(3, out_size[1] // 3))
        field = 0.62 * fine + 0.38 * patch

        # Subtracting a threshold, not multiplying by a factor. Multiplying dims
        # the whole caption a little, which the eye reads as faded type; taking a
        # threshold off the ink lifts the weakest parts away entirely while the
        # strong parts stay put, which reads as ink that failed to transfer.
        # Faded and patchy are different things, and only the second says ribbon.
        thr = texture * np.clip(field, 0.0, 1.0) ** 1.4
        arr = np.clip((arr - thr) / np.maximum(1e-6, 1.0 - thr), 0.0, 1.0)

    alpha = arr[:, :, None] * opacity
    ink = np.array(color, dtype=np.float32)[None, None, :]
    rgb = 255.0 * (1.0 - alpha) + ink * alpha
    canvas = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
    return _trim_white(canvas)


def _trim_white(img: Image.Image, tolerance: int = 6) -> Image.Image:
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    ink = arr.mean(axis=2) < (255 - tolerance)
    if not ink.any():
        return img
    rows = np.where(ink.any(axis=1))[0]
    cols = np.where(ink.any(axis=0))[0]
    return img.crop((int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1))


# --------------------------------------------------------------------------
# misc
# --------------------------------------------------------------------------


def available_faces(extra: str | None = None) -> list[str]:
    """The faces the sampler may choose from on this machine.

    `extra` is an explicitly requested face, which always wins if it exists.
    """
    found = [f for f in FONT_CANDIDATES if face_exists(f)]
    if extra and face_exists(extra):
        found = [extra] + [f for f in found if f != extra]
    return found or [""]


def _describe_colour(r: int, g: int, b: int) -> str:
    """A plain-language name for one colour: lightness, saturation, hue."""
    mx, mn = max(r, g, b), min(r, g, b)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    chroma = mx - mn

    light = (
        "very dark" if lum < 45 else "dark" if lum < 95 else
        "mid" if lum < 150 else "light" if lum < 205 else "very light"
    )
    if chroma < 18:
        return f"{light} neutral grey"

    # Hue angle, degrees.
    mxf, mnf = mx / 255.0, mn / 255.0
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    d = mxf - mnf
    if mx == r:
        h = 60 * (((gf - bf) / d) % 6)
    elif mx == g:
        h = 60 * (((bf - rf) / d) + 2)
    else:
        h = 60 * (((rf - gf) / d) + 4)
    hue = next(name for edge, name in _HUE_NAMES if h < edge)

    sat = "muted" if chroma < 60 else "moderately saturated" if chroma < 120 else "vivid"
    return f"{light} {sat} {hue}"


def dominant_palette(img: Image.Image, colours: int = 6, sample: int = 220) -> list[dict]:
    """The photograph's actual palette, as facts to paste into a prompt.

    "Preserve the colour memory" on its own is an adjective, and a model will
    happily substitute a stock retro-travel palette for it -- pale stucco towers
    come back brick red, a pastel sunset comes back saturated navy. Giving it the
    real hex values, their share of the frame, and how light each one is removes
    the guesswork.
    """
    small = img.convert("RGB").resize((sample, sample), Image.LANCZOS)
    quant = small.quantize(colors=colours, method=Image.FASTOCTREE)
    palette = quant.getpalette() or []
    total = sample * sample
    out = []
    for count, idx in sorted(quant.getcolors() or [], reverse=True):
        r, g, b = palette[idx * 3 : idx * 3 + 3]
        out.append(
            {
                "hex": f"#{r:02x}{g:02x}{b:02x}",
                "rgb": [r, g, b],
                "share": round(count / total, 4),
                "lightness": round(0.299 * r + 0.587 * g + 0.114 * b, 1),
                "name": _describe_colour(r, g, b),
            }
        )
    return out


def describe_palette(palette: list[dict], top: int = 5) -> str:
    """One prompt-ready line naming the photograph's real colours."""
    parts = [
        f"{p['name']} {p['hex']} ({round(p['share'] * 100)}% of the frame)"
        for p in palette[:top]
    ]
    return "; ".join(parts)


def dominant_ink(seal: Image.Image, sample: int = 160) -> tuple[int, int, int] | None:
    """The seal's main ink colour, for tinting a caption to match it.

    Looks only at pixels that are both dark and saturated, so paper and the
    faintest wash do not drag the answer toward grey.
    """
    small = seal.convert("RGB").resize((sample, sample), Image.LANCZOS)
    arr = np.asarray(small).astype(np.float32).reshape(-1, 3)
    lum = arr.mean(axis=1)
    sat = arr.max(axis=1) - arr.min(axis=1)
    picked = arr[(lum < 215) & (sat > 18)]
    if len(picked) < 24:
        return None
    med = np.median(picked, axis=0)
    return tuple(int(round(v)) for v in med)  # type: ignore[return-value]


# --------------------------------------------------------------------------
# variation
# --------------------------------------------------------------------------


@dataclass
class Variation:
    """One sampled look. Every field is a value compose.py would otherwise default."""

    seed: int
    amount: float
    font: str
    layout: str
    anchor: str
    caption_align: str
    caption_size_scale: float
    caption_opacity: float
    caption_tracking: float
    caption_line_spacing: float
    caption_weight: float
    caption_texture: float
    caption_jitter: float
    caption_strike: float
    caption_wear: float
    caption_tint: float
    seal_scale: float
    seal_strength: float
    seal_wear: float
    paper_tone: tuple[int, int, int]
    paper_seed: int
    noise_seed: int
    grain: float
    mottle: float
    margin: float
    gap: float

    def as_dict(self) -> dict:
        d = asdict(self)
        d["paper_tone"] = list(self.paper_tone)
        return d


def _jit(rng, base: float, lo: float, hi: float, amount: float) -> float:
    """Move `base` toward a uniform sample in [lo, hi], scaled by amount."""
    return base + (float(rng.uniform(lo, hi)) - base) * amount


def _skewed(rng, base: float, lo: float, hi: float, amount: float, bias: float) -> float:
    """Like `_jit`, but the draw is weighted toward `lo` instead of being uniform.

    Some properties are not symmetric about their middle. Press quality is the
    clear case: most impressions come out somewhere between clean and ordinary,
    and a badly starved one is the occasional exception rather than a third of
    the drawer. A uniform draw over the full range makes the exception as common
    as the rule, so the range has to stay wide while the mass sits low.

    `bias` above 1 pushes samples toward `lo`; 1.0 reproduces `_jit`.
    """
    u = float(rng.random()) ** bias
    return base + ((lo + (hi - lo) * u) - base) * amount


def _pick(rng, options: list, default, amount: float):
    """Deviate from `default` with probability `amount`."""
    if not options or rng.random() >= amount:
        return default
    return options[int(rng.integers(0, len(options)))]


def ribbon(wear: float) -> dict:
    """How a typewriter ribbon at a given condition lays down ink.

    One control rather than four, because on a real machine these are not
    independent. A ribbon near the end of its life is fainter, patchier, and more
    uneven strike to strike, all at once, and it lays down slightly less ink per
    key. Sampling those separately produces combinations that never occur -- dark
    confident ink riddled with dropout, or pale ink struck with perfect
    consistency -- and both read as an effect applied to text rather than as text
    that was typed.

    wear 0 is a fresh ribbon: even, reasonably dark, only slightly mottled.
    wear 1 is a dry one: pale, patchy, visibly uneven letter to letter.

    The range is wide at the worn end because the caption's contrast floor makes
    it safe. `legible_ink` guarantees the *strongest* strokes clear a minimum
    against the paper, so the weak ones are free to fall well below it -- which is
    how a worn ribbon actually reads. Legibility comes from the letters that
    struck properly, and the patchiness lives in the ones that did not.

    Stroke weight thins as the ribbon dries but never goes negative -- these are
    light faces already, and paleness belongs in the ink rather than the stroke.
    """
    w = max(0.0, min(1.0, float(wear)))
    return {
        "opacity": 0.92 - 0.34 * w,
        "texture": 0.04 + 0.68 * w,
        "strike": 0.18 + 0.70 * w,
        "weight": 0.24 - 0.20 * w,
    }


def sample_variation(
    seed: int,
    amount: float,
    band_side: str,
    faces: list[str] | None = None,
) -> Variation:
    """Draw one look from curated ranges.

    Bounded on purpose. The point is that two composites in the same batch are
    not identical, not that any one of them is a surprise -- so every range here
    stays inside what already reads as the house style, and `amount` scales how
    far from the house default a sample may travel. amount=0 reproduces the
    fixed defaults exactly.
    """
    rng = np.random.default_rng(seed)
    amount = max(0.0, min(1.0, amount))
    faces = faces or available_faces()

    # A bottom band is wide, so the caption can sit beside the seal. A right-hand
    # band is a narrow column, where only stacking works.
    if band_side == "bottom":
        layout = _pick(rng, ["stacked", "split"], "split", amount)
        anchors = ["left", "center", "bottom-left", "top-left", "right"]
    else:
        layout = "stacked"
        anchors = ["center", "top", "bottom", "top-left", "left"]

    anchor = _pick(rng, anchors, "center", amount)
    align = "right" if anchor.endswith("right") else "left"
    align = _pick(rng, [align, "left"], align, amount * 0.4)

    # One ribbon condition drives ink opacity, mottling, per-glyph strike and
    # stroke weight together -- see `ribbon`. Skewed toward a fresh ribbon for the
    # same reason the seal's press is: a worn-out ribbon is what happens
    # sometimes, not what happens by default, and a batch where every caption is
    # equally faded reads as a filter rather than as a machine in use.
    cap_wear = _skewed(rng, 0.30, 0.0, 1.0, amount, bias=1.7)
    _ribbon = ribbon(cap_wear)
    cap_opacity = _ribbon["opacity"]
    cap_texture = _ribbon["texture"]
    cap_weight = _ribbon["weight"]
    cap_strike = _ribbon["strike"]

    tone_base = (237, 235, 229)
    tone = tuple(
        int(round(_jit(rng, c, c - 4, c + 5, amount))) for c in tone_base
    )

    return Variation(
        seed=seed,
        amount=amount,
        font=_pick(rng, faces, faces[0], amount),
        layout=layout,
        anchor=anchor,
        caption_align=align,
        caption_size_scale=_jit(rng, 1.0, 0.88, 1.14, amount),
        # Pale on purpose. A typewriter ribbon lays down far less ink than a
        # printer does, and a caption that matches the seal for weight competes
        # with it. The floor stays high enough to read at full size -- faint is
        # the effect, illegible is a bug.
        caption_opacity=cap_opacity,
        caption_tracking=_jit(rng, 0.0, 0.0, 2.6, amount),
        caption_line_spacing=_jit(rng, 1.62, 1.46, 1.82, amount),
        caption_weight=cap_weight,
        caption_texture=cap_texture,
        caption_jitter=_jit(rng, 0.15, 0.0, 0.55, amount),
        caption_strike=cap_strike,
        caption_wear=cap_wear,
        # Half the time the caption picks up the seal's ink instead of staying
        # neutral, which is the difference between the red and the grey captions.
        caption_tint=_pick(rng, [0.0, 0.55, 0.75, 0.9], 0.0, amount),
        seal_scale=_jit(rng, 1.0, 0.9, 1.08, amount),
        seal_strength=_jit(rng, 1.0, 0.88, 1.0, amount),
        # Deliberately the widest range in the sampler. Every other property here
        # wants to stay near the house default, but press quality is the one
        # thing that should genuinely fluctuate: a drawer of real stamped papers
        # holds crisp well-inked impressions and half-starved ones side by side,
        # and a batch where every seal is equally broken up reads as one applied
        # effect rather than as a hand pressing a stamp over and over. The bounds
        # are set wide because `amount` pulls samples back toward the base -- at
        # the default 0.65 these give roughly 0.15 to 0.85, which is the visible
        # difference between "cleanly stamped" and "the pad was nearly dry".
        # Off by default, and that is a deliberate reversal.
        #
        # This existed because generated seals used to come back mechanically
        # even, so the press unevenness had to be added afterwards. The prompt
        # now asks for it directly -- uneven pressure, plus a per-photograph
        # impression grade -- and the model delivers it well. Running the filter
        # on top of that starves ink that is already starved: the two compound,
        # and the result is a seal noticeably less legible than the artwork that
        # went in.
        #
        # The filter can only take ink away, never restore it, so the asymmetry
        # matters: a seal that came back too clean is one flag away from being
        # fixed, while a seal degraded on the way to the paper has lost detail
        # that no later step recovers. Off is the safe default and the prompt is
        # the right place for this. `--seal-wear` remains for the rescue case.
        seal_wear=0.0,
        paper_tone=tone,  # type: ignore[arg-type]
        # Both noise seeds are pinned at amount 0, so --variation 0 reproduces one
        # fixed look rather than merely one fixed set of parameters.
        paper_seed=int(rng.integers(0, 2**31 - 1)) if amount > 0 else 0,
        noise_seed=seed if amount > 0 else 0,
        grain=_jit(rng, 1.9, 1.2, 2.6, amount),
        mottle=_jit(rng, 2.6, 1.6, 3.6, amount),
        margin=_jit(rng, 0.075, 0.06, 0.105, amount),
        gap=_jit(rng, 1.0, 0.78, 1.35, amount),  # multiplier on the layout's gap
    )


# The caption must stay readable against the paper it sits on, whatever ink and
# opacity were sampled and whatever the paper tone drifted to. A fixed "don't go
# lighter than X" cap cannot express that, because it ignores both the paper and
# the opacity the ink will be laid down at -- the same grey is comfortable on
# warm white and invisible on a darker sheet. So the floor is stated as contrast
# and enforced against the colour that actually lands on the page.
CAPTION_MIN_CONTRAST = 3.4


def _rel_luminance(rgb) -> float:
    chan = []
    for v in rgb:
        v = max(0.0, min(1.0, v / 255.0))
        chan.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2]


def contrast_ratio(a, b) -> float:
    la, lb = _rel_luminance(a), _rel_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def legible_ink(
    colour: tuple[int, int, int],
    opacity: float,
    paper: tuple[int, int, int],
    min_ratio: float = CAPTION_MIN_CONTRAST,
) -> tuple[int, int, int]:
    """Darken the caption ink until what lands on the paper clears min_ratio.

    Faintness is the effect we want, so this deepens the ink rather than raising
    the opacity: the caption keeps its thin, under-inked ribbon character and
    only stops being invisible. Returns the ink unchanged when it already clears
    the floor, which is the common case.
    """
    composited = tuple(p * (1.0 - opacity) + c * opacity for p, c in zip(paper, colour))
    if contrast_ratio(composited, paper) >= min_ratio:
        return colour

    ink = [float(c) for c in colour]
    for _ in range(48):
        composited = tuple(p * (1.0 - opacity) + c * opacity for p, c in zip(paper, ink))
        if contrast_ratio(composited, paper) >= min_ratio:
            break
        ink = [c * 0.94 for c in ink]
    return tuple(int(round(max(0.0, min(255.0, c)))) for c in ink)  # type: ignore[return-value]


def tint_caption(
    neutral: tuple[int, int, int],
    ink: tuple[int, int, int] | None,
    strength: float,
) -> tuple[int, int, int]:
    """Blend the neutral caption ink toward the seal's colour."""
    if not ink or strength <= 0:
        return neutral
    # Darken the seal ink first; caption text at full seal chroma reads as loud.
    toward = tuple(c * 0.72 for c in ink)
    blended = [n + (t - n) * strength for n, t in zip(neutral, toward)]

    # A pale seal ink -- tan, straw, dusty pink -- would otherwise tint the
    # caption to the edge of legibility. Small text is never allowed to also be
    # dim, so cap how light a tinted caption may end up.
    lum = 0.299 * blended[0] + 0.587 * blended[1] + 0.114 * blended[2]
    if lum > CAPTION_MAX_LUMINANCE:
        scale = CAPTION_MAX_LUMINANCE / lum
        blended = [c * scale for c in blended]

    return tuple(int(round(max(0.0, min(255.0, c)))) for c in blended)  # type: ignore[return-value]


def stem_seed(text: str) -> int:
    """A stable seed derived from a filename, so each photo varies but repeats."""
    return zlib.crc32(text.encode("utf-8")) & 0x7FFFFFFF


def exif_summary(path: str | Path) -> dict:
    """Best-effort capture date and GPS, for building a caption."""
    out: dict = {}
    try:
        img = Image.open(path)
        exif = img.getexif()
        if not exif:
            return out
        for tag, key in ((36867, "datetime_original"), (306, "datetime")):
            val = exif.get(tag)
            if val:
                out[key] = str(val)
        gps = exif.get_ifd(34853)
        if gps:
            try:
                lat = _dms(gps[2]) * (-1 if str(gps.get(1, "N")).upper().startswith("S") else 1)
                lon = _dms(gps[4]) * (-1 if str(gps.get(3, "E")).upper().startswith("W") else 1)
                out["gps"] = [round(lat, 6), round(lon, 6)]
            except (KeyError, TypeError, ZeroDivisionError):
                pass
    except Exception:  # noqa: BLE001 - EXIF is advisory only
        return out
    return out


def _dms(triple) -> float:
    d, m, s = (float(x) for x in triple)
    return d + m / 60.0 + s / 3600.0


def save_webp(img: Image.Image, path: str | Path, quality: int = WEBP_QUALITY) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=quality, method=6)
