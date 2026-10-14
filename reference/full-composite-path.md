# The full-composite path

The default path has the image model draw only the seal, and a script assemble
the composite around an untouched photograph. This path hands the model the whole
frame instead: it renders the photograph, the paper, the seal, and the caption in
one image.

It is not a lesser path. It is the right one whenever the photograph itself
should be *reinterpreted* rather than preserved — and that is a real, common
intent, not a failure of nerve.

---

## When to use it

**The picture should become a print.** The strongest reason. If you want the
whole frame rendered as a woodblock, risograph, screen print, engraving, or line
drawing — the scene redrawn in ink on paper rather than photographed — then
preserving the original pixels is exactly the wrong goal. `compose.py` cannot do
this: it pastes a photograph, by design.

**The photograph cannot carry the frame.** Too low-resolution, badly compressed,
motion-blurred, dark, or damaged. A graphic treatment can survive what a
photograph cannot.

**One unified surface.** On the default path the photograph and the seal are
different media sitting side by side — that contrast is the format's signature.
When you want the opposite, a single continuous printed surface where the picture
and the stamp share one ink language, the model has to make both at once.

**Something should be abstracted away.** Faces, licence plates, house numbers,
a person who did not consent to being archived. Reinterpretation removes them by
construction rather than by retouching.

## When not to use it

- The photograph matters as a document — people you want to recognise, signage
  you want to read, a place as it actually looked.
- You want the format's usual look. The default path produces that faster,
  cheaper, and without a fidelity risk.
- You are only unhappy with the seal, the caption, the paper, or the placement.
  All of those are flags on the default path. Switching paths to fix them trades
  a guaranteed photograph for a one-line change you could have made anyway.
- The seal came back looking like a poster. That is a reseal on the default path,
  not a reason to hand the whole frame over. Rendering the photograph as a print
  too does not fix the seal; it produces two posters.

---

## What you give up, and what you keep

**Given up — every one of these becomes a risk rather than a guarantee:**

| | Default path | This path |
|---|---|---|
| Photograph pixels | copied exactly | redrawn |
| Crop and framing | impossible to change | must be checked |
| Faces and identity | preserved | may drift |
| Legible signage and numbers | preserved | often garbled |
| Object and people counts | preserved | may change |
| Colour accuracy | exact | interpreted |
| Cost per image | one seal generation | one full generation, usually slower |
| Revisions | free flag changes | mostly regeneration |

**Kept — these do not weaken at all:**

- `inspect_source.py` still resolves the geometry, and you still paste its real
  numbers into the prompt.
- `verify.py` still gates the canvas size and the orientation rule, absolutely
  and without softening. A non-square output is a failure here exactly as it is
  there.
- The seal shape vocabulary, the ink language, and the paper description are
  unchanged. In particular the seal stays a small pressed impression even when
  the picture panel is a bold print. The treatment applies to the picture, not to
  the seal, and the two must not converge into one poster.
- `reference/checklist.md` still applies to everything except the "photo region
  matches the original" line.

---

## Workflow

### 1. Resolve the geometry first

```bash
python inspect_source.py source/IMG_1588.heic
```

```
IMG_1588  (4032x2268, aspect 1.7778, landscape)
  Canvas: 2048x2048, square 1:1.
  Layout: the complete photograph occupies the TOP of the square; the paper panel goes BELOW the photograph.
  Seam: one perfectly straight horizontal edge, 896px of paper.
  Photo box: x=0 y=0 w=2048 h=1152
```

Paste those real numbers into the prompt. **Never leave a conditional in the
prompt.** Writing "for a landscape source do X, for a portrait source do Y" and
letting the model decide which applies is the single specific mistake that
produced the 2482×2048 and 2094×2048 outputs in the old archive. State the one
case that is true and delete the other.

### 2. Decide the treatment intensity

This governs both the prompt and which metric can gate the result.

| Intensity | What it means | Tone corr | Structural corr |
|---|---|---|---|
| **Light** | photographic, lightly graded, grain added | 0.97–1.00 | 0.95–1.00 |
| **Posterised** | flattened to a few tones, still photographic | 0.95–0.99 | 0.93–0.99 |
| **Print** | screen print or riso, heavy flattening, visible ink | 0.80–0.92 | 0.82–0.90 |
| **Line art** | drawn in ink on pale paper, tone inverted | **−0.75 to −0.35** | 0.70–0.80 |

Those figures are measured, not estimated — see *Choosing the metric* below.

### 3. Generate

One call per photo, using the template below. No speculative variants.

### 4. Gate before you look

```bash
python verify.py --source-dir source --output-dir output --metric structural
```

Pick the metric from the intensity you chose in step 2. Getting this wrong is the
most likely way to waste a good batch — see the next section.

### 5. Then run the eye checks

`reference/checklist.md`, skipping only the "photo region matches the original"
line. Add three checks that only matter on this path:

- **Count things.** Windows, people, chairs, lanterns. A redrawn scene quietly
  gains and loses objects.
- **Read every piece of text in the picture.** Shop signs, station names, numbers.
  Models garble lettering, and a garbled sign in an archive image is worse than
  no sign.
- **Check the framing against the original.** Open both. The model may have
  cropped in, extended the sky, or straightened a horizon you liked crooked.

---

## Choosing the metric

`verify.py` offers two fidelity tests. The canvas and orientation checks are
unaffected by this choice and never soften.

**`--metric tone`** (default) compares the images light-for-light. Correct
whenever the photograph was copied or only lightly treated.

**`--metric structural`** compares edge structure only, ignoring tone and
polarity. It asks "is this the same scene, framed the same way" — the only
fidelity question that still has a meaningful answer after heavy stylisation.

**`--metric either`** passes if either test passes. For a batch of mixed
intensities.

### Why the choice matters

A line-art treatment inverts tone: the dark parts of the photograph become pale
paper carrying dark ink. Measured on two real sources:

| Treatment | Tone | Structural |
|---|---|---|
| identical | +1.000 | +1.000 |
| blurred | +1.000 | — |
| posterised | +0.97 | +0.95 |
| duotone | +1.000 | — |
| heavy print | +0.85 | +0.85 |
| **line art** | **−0.37 / −0.74** | **+0.70 / +0.79** |
| cropped to 80% | — | +0.12 / +0.24 |
| wrong image (mirrored) | +0.01 / +0.22 | −0.05 / +0.31 |

So a perfectly faithful line-art composite scores *worse than a completely wrong
image* on the tone test. Gate that batch on tone and you will reject all of it.

The structural test still catches what matters: a crop scores 0.12–0.24 and a
wrong image −0.05 to 0.31, both far below the 0.55 default threshold, while
faithful line art sits at 0.70–0.79.

`verify.py` detects this specific situation and tells you:

```
FAIL  a.png
        - photo region does not match the source by tone (correlation -0.362 < 0.9),
          but its structure does (structural 0.715). This is what a print or line-art
          treatment looks like: same scene, inverted tone. If that was intended,
          re-run with --metric structural.
```

Do not respond to that message by lowering `--min-corr` toward zero. A negative
tone threshold accepts anything. Switch metrics instead.

### Thresholds

| Situation | Flags |
|---|---|
| compose.py output | `--min-corr 0.985` (default metric) |
| light or posterised treatment | `--min-corr 0.93` |
| print treatment | `--metric structural` (0.55 default) or `--min-corr 0.80` |
| line art | `--metric structural` |
| mixed batch | `--metric either` |

---

## Prompt template

Fill every bracket from `inspect_source.py` and from the photograph itself.
Delete the branches that do not apply — do **not** leave both halves of a
conditional in the prompt.

```text
Use case: identity-preserving style transfer.
Asset type: one flat archival composite, exactly [2048] x [2048] pixels, square 1:1.

Canvas: square 1:1. The finished image is [2048] wide and [2048] tall.

Layout: the complete photograph occupies the [TOP | LEFT] of the square, [2048] x [PHOTO_H] pixels. A paper panel occupies the [BOTTOM | RIGHT], [BAND_W] x [BAND_H] pixels. The two rectangles meet edge-to-edge at one perfectly straight [horizontal | vertical] seam.

PICTURE PANEL:
Render the supplied photograph as [a faithful photograph | a posterised photograph flattened to four or five tones | a screen print in three inks | an ink line drawing on pale paper]. The subject is [subject].

Keep, regardless of treatment: the framing, the crop, the viewpoint, the perspective, the relative positions of everything, the object and people counts, the occlusions, and the scene logic. The entire original frame stays visible at its original aspect ratio. Do not crop, truncate, extend, outpaint, add, remove, duplicate, or relocate anything.

[Light and posterised treatments only: Keep colour, lighting, and tonal relationships close to the original.]
[Print and line-art treatments only: Reduce to [number] inks: [name them]. Flatten the tonal range. Allow the tone to invert where paper stands in for light. Preserve the drawing of the scene, not its exposure.]
[If people are present: Preserve identity, age, build, posture, gesture, clothing, and the relationships between them. Faces may be simplified by the treatment but must not become a different person.]
[If legible text is present: The sign reads exactly "[text]". Reproduce it correctly or omit it entirely. Do not invent lettering.]

PAPER PANEL:
Clean warm off-white archival paper with very fine, low-contrast natural fibres, subtle cream and pale-grey variation, and light scan residue. Nearly smooth and quietly tactile at normal viewing size -- never coarse, furry, embossed, streaky, digitally enlarged, strongly directional, or obviously repeated. Gently archival, not heavily yellowed, dirty, cracked, burned, or stained. Generous quiet blank paper.

SEAL:
One small hand-pressed [circular | square-framed | panoramic | arched | subject-silhouette | unbounded] seal impression placed within the paper panel by visual balance -- the character of a rubber stamp or a Japanese hanko inked and pressed by hand onto the paper, not a printed illustration sitting on it.

[Choose one focus and delete the other:]
[Whole view: the seal carries the composition the camera saw -- the framing, the depth, the flanking elements and the sky. Preserve [defining subject features].]
[Subject focus: the seal is [the primary subject] alone. Reduce the surroundings to a light suggestion -- one loose stroke of [colour] for [the sea / the sky / the ground] -- or leave them out entirely. The seal does not have to carry the whole photograph.]

Ink character: fine, granular and delicate. Built from small ink grain, stipple and softly broken edges, with uneven pressure and edges eaten slightly by the paper. Detail survives and is wanted -- petals, dots, mouldings, railings -- and survives as fine ink marks, never as smooth photographic tone. NOT a bold graphic reduction: no large flat fields of solid colour, no heavy linocut slabs, no thick graphic outlines, no poster-style simplification into a few big shapes. The seal is small, quiet and delicate, closer to a botanical stamp or a library mark than to a poster, and it must stay quieter than the picture panel above it.

Keep wear irregular, non-periodic, varied in scale, and responsive to ink coverage -- dark areas must not become uniform patterned texture. Take every ink from the photograph: its measured palette is [paste the Palette line from inspect_source.py]. [Spot colour] dominant, [supporting inks] muted, each element at its real hue and lightness; do not deepen or saturate a colour to make the seal look bolder.
[Square seals only: one complete, unmistakably square worn ink border, all four sides visible. Worn corners and broken ink are wanted; a clean digital frame, photo mat, or generic rectangle is not.]
[Silhouette or unbounded seals only: follow the subject's own outline; do not enclose it in a rectangle or any generic frame.]

CAPTION:
Small faded typewriter-style text near the seal, inside the paper panel, never over the picture:
[caption lines]

Mood: quiet, restrained, graphic, tactile, memory-like.

Do not include: a cropped or extended source, a changed subject, added or removed objects, changed people, invented scenery, invented lettering, a pasted-photo look, glossy finish, clean vector graphics, a decorative sticker, a scrapbook collage, modern typography, heavy paper aging, coarse or enlarged paper texture, repeated worm-like squiggles, maze patterns, moire, fingerprint loops, ornamental curls, tiled or uniform noise inside the seal, dense text, a watermark, a gradient or feather or page-turn at the seam, a book mockup, a gutter, a diagonal split, or any decorative separator.
```

### On the caption

The model renders it on this path, which means it can misspell it. This is the
one place where the default path is strictly better with no trade-off — there the
caption is real text at full resolution.

If a caption keeps coming back wrong, generate the frame **without** a caption and
composite the text separately. Proofread every caption character by character
against your metadata; place names and dates are exactly what a model
approximates.

---

## Revision

```text
Edit the supplied accepted composite. Change only [the named seal, border, scale, position, ink, caption, or paper-age property].

Requested change: [precise instruction].

Keep invariant: the entire picture panel, the original framing and aspect ratio, the treatment and its ink count, the seam, the square [2048] x [2048] canvas, the paper texture, subject identity and count, scene geometry, colour relationships, caption spelling, and every unmentioned detail.

Do not regenerate the concept, alter the picture region, introduce content, cross the seam, add a gradient, or create a page-turn effect.
```

Re-run `verify.py` on every revision, with the same metric. A model asked to
change one property will sometimes resize the canvas on the way past — that is
not a rare failure, it is the normal cost of handing the whole frame over.

---

## Failure modes

Specific to this path, in rough order of how often they occur.

| Symptom | Cause | Response |
|---|---|---|
| Canvas is not square | Both prompt branches left in, or the aspect stated only in prose | Restate the exact pixel dimensions twice: in the asset-type line and in the canvas line |
| Paper on the wrong side | The model resolved the conditional itself | Delete the branch that does not apply |
| Picture is cropped or zoomed | "Compose a pleasing image" read into a faithful-rendering instruction | Repeat the framing constraint in the negative list |
| Sky or ground extended | Model filling the square canvas by outpainting | State the picture panel's exact pixel height and that the frame is complete |
| Signage garbled | Normal model behaviour | Quote the text exactly, or instruct omission |
| Object count changed | Treatment applied loosely | Name the count: "exactly three teardrop skylights" |
| Caption misspelled | Model-rendered text | Generate without a caption, composite text separately |
| Seam feathered or gradient | Decorative instinct | It is in the negative list; repeat it in the layout line |
| Seal fills the paper panel | No size constraint given | State "small" and "generous quiet blank paper" |
| Seal came back as a poster in the picture's style | The picture treatment bled into the seal block | Restate the seal's ink character separately: fine grain, stipple, delicate, not a bold graphic reduction |
| Everything correct, verify fails | Wrong metric for the treatment | `--metric structural` |

---

## Discipline

- One generation per photo. Inspect before generating again.
- Retry only the outputs that failed, and change only the property that failed.
- Never regenerate an accepted composite to make an unrelated change.
- Never lower a threshold to make a failure disappear. Change the metric if the
  metric is wrong; otherwise fix the output.
- Report which path produced each asset. Someone looking at the archive later
  cannot tell by eye whether a photograph was preserved or redrawn, and that is
  exactly the thing they will want to know.
