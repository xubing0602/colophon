# Checklist

`verify.py` covers the mechanical half. Everything below needs your eyes, at full
size, on every output.

## Already covered by verify.py — do not re-check by hand

- Canvas is exactly 2048×2048 and square.
- Paper band is on the correct side for the source's orientation.
- The photo region matches the original: uncropped, undistorted, unrepainted.
- The band is a quiet off-white, not a spill of photograph.

If `verify.py` passes, these are facts. Spend your attention on what follows.

## The seal

- **Derived, not designed.** Everything in the seal is in the photograph, in the
  same place, in the same number, as uneven as it really was. Nothing added,
  rearranged, evenly spaced, or symmetrised. No shield, crest, badge, roundel,
  banner, or ribbon; no stock cypress rows, generic skylines, or lollipop
  figures. If it would work as a logo for a town you have never been to, it is
  wrong.
- **Colours are the photograph's own.** Compare against the Palette line from
  `inspect_source.py`. Pale things stayed pale, a pastel sky stayed pastel, white
  stayed white — and vivid things stayed vivid. Nothing was deepened to make the
  print look bolder, and nothing was greyed down to make it look tasteful.
- **Pressed, not filtered.** Not a threshold, halftone screen, dither, duotone, or
  posterisation of the photograph. Those keep every pixel and press nothing, and
  read as a photocopy beside the source. Ask: could a filter have produced this?
  If yes, reseal.
- **Reads as inked and pressed.** Fine grain, stipple, softly broken edges, uneven
  pressure — a stamp affixed to paper. **Not** a linocut poster: no large flat
  fields of solid colour, no heavy slabs, no thick graphic outlines, no
  three-saturated-ink simplification. Delicate, not emphatic.
- **Detail survives as grain.** Petals, dots, mouldings, railings are present, and
  present as ink marks rather than smooth tone.
- **Focus was chosen, not defaulted.** Either the whole view is there for a reason,
  or the subject carries it with the surroundings reduced to a stroke or dropped.
  A background that was omitted is fine; one that was invented is not.
- **The edge is eaten, not cut.** Boundaries break up into grain and stipple where
  the ink ran thin, the way a stamp lifts off paper. A crisp continuous contour,
  or a clean vector edge, means it was drawn rather than pressed.
- **Pressure is uneven.** Some passages sit heavy, some are starved and show the
  paper through, with strokes breaking into specks and skips where the ink
  failed — and crisp passages sitting close beside them. A seal of uniform ink
  density across every mark was rendered, not impressed. This one is a flag
  before it is a reseal: raise `--seal-wear`, and only regenerate if the artwork
  itself is the problem.
- One dominant ink with a small number of supporting inks subordinate to it in
  coverage, none of them laid down as a large flat solid field, and no gradients
  or blends. Subordinate in area, not necessarily desaturated — a seal from a
  vivid photograph should be vivid.
- **Set the seal beside its photograph and look at both.** It should be obviously
  the same subject, in the same colours — likeness is wanted, and a seal that no
  longer looks like its source has failed. What you are checking is that it
  resembles the photograph the way a stamp does, not the way a reproduction does.
- **Clarity is uneven.** Some passages resolve fully, enough to identify the
  subject beyond doubt; others go coarse, break up, or thin away and let the eye
  finish them. Uniformly sharp is a copy. Uniformly vague is a smudge. The good
  seal is both, in different places.
- **Nothing about it is evenly distributed.** Detail, wear, spacing, weight — the
  tell of a machine-made image is evenness and tidy symmetry, so irregularity has
  to be real irregularity rather than a texture laid over the top.
- The shape suits the subject rather than defaulting to a circle.
- A square seal has a complete, four-sided, unmistakably square worn border.
- A circular seal still reads as circular through its dry-ink gaps.
- A silhouette seal follows the subject's own outline and is not boxed.
- Defining features survive: silhouette, count, signage, structure, posture.
- The scene is still recognisable as the photograph it came from — same framing,
  same viewpoint, same things either side.
- Wear is irregular and non-repeating. **No** worm-like squiggles, maze patterns,
  moiré, fingerprint loops, ornamental curls, or uniform noise fill. Any of these
  is a failed seal — reseal, do not accept.
- No pale rectangle of the seal's own background around it.

## The paper

- Warm off-white, gently archival. Not heavily yellowed, dirty, cracked, burned,
  or antique.
- Nearly smooth at normal viewing size. Not coarse, furry, embossed, streaky, or
  visibly repeated.
- Generous quiet blank space. The seal does not dominate the panel.

## The caption

- Spelling, place names, and dates correct against the source metadata.
- **Typed, not set.** Letters vary slightly in how hard they struck — some full,
  some faint — and sit a touch unevenly on the line. Uniform ink across every
  glyph is the giveaway that the text was rendered rather than typed.
- **Pale, and still readable.** The ink is deliberately light; a caption as
  strong as the seal competes with it. If you have to hunt for the line at full
  size, that is too far — raise `--caption-opacity`.
- The face is a typewriter face. A book serif here reads as a modern publication
  rather than an archival note; if one appears, `--font` was pinned to it.
- Small and faded, entirely within the paper panel, never over the photograph.
- Legible: not so faint it disappears at normal size.

## The whole

- One flat composite. Not a mockup, scrapbook, poster board, or before/after.
- The seam is straight and plain: no gradient, feather, gutter, or page turn.
- Nothing invented, no watermark, no stray lettering.
- Only final assets remain on disk; intermediate seals and test renders deleted.
- Every saved path reported to the user.
