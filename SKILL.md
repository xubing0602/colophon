---
name: colophon
description: Turn photographs into square archival composites that pair the untouched photo with a warm-white paper panel carrying a small hand-pressed seal and a typewriter caption. Landscape photos get paper below, portrait photos get paper on the right, output is always 2048x2048. Use for requests mentioning colophon, 钤记, 图章, 印章, stamp, seal, 照片加图章, 照片档案, 拼接, 清爽纸张, 圆形章, 方形章, 异形章, photo stamp archive, or iterative changes to seal shape, border, scale, position, ink colour, caption, paper age, or splice orientation.
---

# Colophon

A colophon is the printer's mark at the end of a book: a small emblem, and a note
saying where and when the thing was made. That is exactly what this produces —
one finished square composite per source photo, the photograph exactly as shot,
joined to a quiet paper panel bearing a compact subject-specific seal and its
place and date.

## The rule that matters

**The image model never draws the photograph.** It draws only the seal. A script
does the layout, so the canvas size, the orientation rule, and the fidelity of
the photograph are guaranteed by arithmetic rather than by remembering them.

This is the whole point of the skill. Do not hand the whole frame to an image
model on your own initiative.

There is a second, equally supported path where the model does render everything,
documented in `reference/full-composite-path.md`. Take it when the user wants the
photograph **reinterpreted rather than preserved** — rendered as a woodblock,
risograph, screen print, engraving, or line drawing — or when the source is too
degraded to carry the frame, or when faces or plates should be abstracted away.
`compose.py` cannot produce those: it pastes a photograph, by design.

Read that file before taking the path. Two things there are easy to get wrong:
state the resolved geometry as fact rather than leaving a conditional in the
prompt, and gate a stylised batch with `--metric structural`, because a line-art
treatment inverts tone and scores negative on the default tone test despite being
perfectly faithful.

Do not switch paths to fix the seal, caption, paper, or placement. Those are
flags on the default path.

## Setup

Scripts live in `scripts/` and need Python with Pillow, numpy, and pillow-heif:

```bash
pip install -r scripts/requirements.txt
```

Run scripts from inside `scripts/`, or add it to `PYTHONPATH`.

## Batch conventions

These are the defaults. The user does not have to restate them, and you should
not ask about them unless something contradicts what you find on disk.

**Folders.** Sources in `source/`, generated seals in `seals/`, finished
composites in `output/`. Metadata in `manifest/metadata.csv`, falling back to
`metadata.csv` at the project root.

**Output naming.** The output basename is always identical to the source
basename; only the extension changes, to `.webp`.

```
source/IMG_3982.heic  ->  output/IMG_3982.webp
```

Never renumber, re-slug, prettify, or append to a basename. If a source has an
unusual name, it keeps it.

**Row selection.** When the user names rows — "rows 112 to 121" — those are
**data rows, 1-indexed, excluding the header**. Data row 112 is line 113 of the
file. Never guess this: `plan_batch.py` resolves it and prints the filenames, so
confirm the first and last filename against what the user expects before
generating anything.

**Captions.** Look each source up in the metadata CSV by filename and build three
lines:

```
<place>
<city>, <country>
<MONTH_NAME> <year>
```

For example:

```
Yokohama Red Brick Warehouse
Yokohama, Japan
OCT 2024
```

Use the CSV's own `month_name` — do not translate, reformat, or re-derive it from
the numeric month. Omit a line whose fields are all empty rather than printing a
stray comma.

**Resolve the whole batch before generating.** One command produces the exact
per-photo source path, seal path, caption lines, and output path:

```bash
python plan_batch.py --csv manifest/metadata.csv --rows 112-121
```

It prints ready-to-run `compose.py` commands, or `--json` for a machine-readable
plan, or `--check` to confirm every source exists first. Use it rather than
reading the CSV by eye: it is what makes the row numbering, the caption format,
and the basenames correct by construction instead of by care.

## Workflow

### 1. Get the facts before writing any prompt

```bash
python inspect_source.py <files-or-directory>
```

This applies EXIF rotation first — a rotated iPhone frame is otherwise misread as
the opposite orientation — and prints, per photo, the orientation, which side the
paper goes on, the exact pixel boxes, and the photograph's **measured palette**.
Read it. Do not infer orientation by eye from a preview, and do not describe the
colours from memory — the Palette line goes into the seal prompt verbatim.

### 2. Look at each photograph

Open every source at full size. Identify what the seal has to carry: the subject,
its distinctive silhouette, the viewpoint, the dominant hues, any legible signage
or numbers, and how many of the important things there are.

Note the composition too, not just the subject — what flanks it, how deep the view
runs, how much sky. Then decide which the seal is about. A tower at the end of an
avenue is a picture of the avenue as much as of the tower, and wants the whole
view. A sculpture, a pumpkin, a blossoming branch is its own subject, and the seal
should be that subject with the surroundings reduced to a stroke or dropped.

For a batch, run `plan_batch.py` once (see **Batch conventions**) and work from
its output. Do not reopen the CSV per photo, and do not transcribe captions by
hand.

### 3. Design the seal

Pick the shape from the subject, not from habit:

| Subject | Shape |
|---|---|
| compact rounded subjects, faces, icons, ceremonial motifs | circle or oval |
| signage, dense architecture, storefronts | square frame |
| rows, processions, coastlines, wide landscapes | panoramic ridge |
| windows, doors, portals, vaulted subjects | arch |
| distinctive buildings, vehicles, trees, statues, objects | irregular silhouette |
| a single dominant subject, surroundings dropped | no boundary at all |

Choose one dominant spot colour drawn from the photograph's own palette, with the
supporting inks subordinate to it — subordinate in how much of the seal they
cover, not necessarily drained of colour. A seal can be genuinely colourful. What
makes it quiet is its size, its ink weight and its blank surround, not a washed
palette: a pumpkin that is vividly yellow gets a vividly yellow seal.

Two habits separate the seals that work from the ones that merely pass:

- **No boundary is the common case.** Most of the best seals are simply the inked
  subject on paper. Reach for a bounded shape when the subject genuinely wants a
  frame — signage, a vaulted portal, a dense storefront — not by default. A
  reflexive circle is the first step toward a badge.
- **Spend detail unevenly.** The subject gets the dense, fine pressing; the
  surroundings get a fraction of it, or nothing. It is the *uniformity* of detail
  that makes a seal read as a small copy, never the amount of it — a seal cannot
  be too faithful, only too evenly rendered.

The shape is the seal's outer boundary, and a seal may have none — several of the
best are simply the inked subject sitting on the paper. The shape does not dictate
how much of the scene goes inside it: an arched or circular seal can still hold
the full view, its flanking buildings and its sky.

Paste the **Palette** line from `inspect_source.py` straight into the prompt, and
pick the dominant and supporting inks from it rather than from memory. This is the
single most effective guard against the seal drifting to a stock palette.

Decide the **focus** too, and say it in the prompt. If one subject dominates the
photograph, center the seal on it and name what the surroundings reduce to — "one
loose stroke of pale blue for the sea" — or say they are dropped. If the
composition is the point, keep the whole view. Both are correct; choosing is the
work.

Subject focus is not the same as cutting the subject out. What physically carries
or contains the subject usually belongs with it — the plate under the dessert, the
pier under the pumpkin, the branch the blossoms are on. Those are part of the
thing, and a seal that drops them leaves the subject floating. What goes is the
wider environment: the table, the room, the sky, the shadow across the floor. The
useful question is not "what is the subject" but "where does the subject stop".

### 4. Generate the seal

Start by looking, not by filling in a form. The seal that works is the one that
answers *this* photograph: what the subject is, where it stops, which detail
carries its identity, which colour leads. Those judgments are the whole job, and
nothing downstream can supply them.

`build_prompt.py` handles the half that is the same every time — it measures the
palette and emits the invariant clauses (ink character, uneven pressure,
derived-not-designed, the negative list) so none of them can be half-remembered:

```bash
python build_prompt.py --photo source/IMG_9001.heic \
  --subject "a mound of shaved ice with mandarin segments on a metal plate" \
  --focus subject --keep "the metal plate and the spoon lying on it" \
  --drop "the wooden table and its shadow" \
  --detail "the shaved-ice texture, the segments, the banana slices" \
  --lead-ink "the warm orange of the syrup" --support "a cool grey for the plate"
```

Treat its output as a **draft to extend, not a prompt to send**. It guards the
floor — it stops a dropped clause turning a seal into a poster — but it cannot
raise the ceiling, and a long invariant block dilutes the specific facts if you
add nothing to it. Whatever you noticed in the photograph that the flags cannot
say, write into the prompt: the way the stem leans, that the dots crowd at the
ribs and thin across the faces, that the far hills read as one flat band. That
sentence is usually the difference between a competent seal and a good one.

Read `reference/seal-prompt.md` for what each clause is doing and why, and for its
**Calibration** section — accepted seals described in detail, which give you a
target to aim at rather than only a list of things to avoid. Prohibitions alone
produce a cautious seal, not a good one.

The seal is generated **alone**,
on its own near-white ground, with no caption and no border around the whole
image — the script adds the caption and places the seal.

**With no image-generation tool of your own** (Claude Code, for example): if an
`OPENAI_API_KEY` is available — in the environment or a `.env` in the project or
this skill's folder — write each finished prompt to `seals/prompts/<stem>.txt`
and run

```bash
python generate_seal.py ../seals/prompts/*.txt
```

which draws each seal through OpenAI's image API into `seals/<stem>_seal.png`,
skipping seals that already exist. Then continue from `check_seal.py`. Never ask
the user to paste a key into the chat; they put it in `.env` themselves.

If there is no key either: do not skip the seal, and do not draw one yourself in SVG or with a
script — a seal is the one part that has to come from an image model. Finish
every prompt, write each to `seals/prompts/<stem>.txt`, and tell the user which
files to generate and where to save them: `seals/<stem>_seal.png`, PNG. Wait for
them, then continue from `check_seal.py`.

One call per photo. No speculative variants. For batches, finalise every prompt
first, then run 2–3 concurrent calls. Concurrency changes scheduling only: never
trade away model quality, prompt specificity, or source resolution for speed.

Then check each seal against its photograph before spending a composite on it:

```bash
python check_seal.py --photo source/IMG_4705.heic --seal seals/IMG_4705_seal.png
```

It compares the seal's inks to the photograph's measured palette and flags
substituted stock colours, punched-up saturation, and lightness drift. Advisory,
not a gate — it tells you where to look, and your eyes decide. A flagged seal is
usually a reseal with the Palette line pasted in, not something to accept.

### 5. Composite

```bash
python compose.py --photo source/IMG_1443.heic --seal tmp/IMG_1443_seal.png \
  --caption "Kiyomizu-dera" --caption "Kyoto, Japan" --caption "NOV 2019" \
  --out output/IMG_1443.webp
```

Defaults already produce the house format: 2048×2048 WebP at quality 92, paper
below for landscape and on the right for portrait, the photo at its true aspect
ratio, a straight seam, and generous blank paper. `--help` lists every knob.

A sidecar `.webp.json` records the exact settings, so any later revision is a
rerun rather than a re-derivation.

The seal is scaled to fill its panel, so how many pixels the generated art
happens to contain never decides how large the seal sits on the paper. When the
art is small enough that filling means a real enlargement, the run prints a note:
the composite is still correct, but the seal will be soft, and the fix is to
regenerate the seal larger rather than to accept it.

Each photo also gets its own sampled look — caption face, size, weight, ink
texture, tracking, colour, alignment, placement, paper tone and grain, seal
scale. See **Variation** below. You do not have to ask for this or configure it;
it is on by default.

### 6. Verify, then look

```bash
python verify.py --source-dir source --output-dir output --min-corr 0.985
```

This fails the batch on a non-square canvas, a paper band on the wrong side, or a
photo region that does not match the original. It is a gate, not a substitute for
looking: open every output at full size afterwards and judge the seal, the ink,
the caption spelling, and the balance of the paper.

Judge the seal **beside its photograph**, in the finished composite, never alone.
What you are checking is not whether it resembles the source — it should, closely
and unmistakably — but whether it resembles it the way a stamp does rather than
the way a reproduction does. A seal rendered evenly, at uniform sharpness, reads
as a small copy however good it looks by itself.

For batch triage, use contact sheets of at most four outputs so each stays large
enough to read, then open anything ambiguous on its own.

### 7. Revise

Most revisions are script flags, which cost nothing and cannot disturb the photo:

| Request | Change |
|---|---|
| `缩小 10%` / smaller seal | `--seal-scale 0.9` |
| `放大` / larger seal | `--seal-scale 1.15` |
| `移动到左上` / move the group | `--anchor top-left` |
| `纸张不要那么旧` / less aged paper | `--paper-tone 242,240,235`, lower `--mottle` |
| `纸张质地更细` / finer paper | lower `--grain`, e.g. `--grain 1.2` |
| caption too strong | `--caption-opacity 0.72` |
| caption wording or spelling | edit `--caption` values |
| seal ink too heavy | `--seal-strength 0.85` |
| `印章太干净` / seal came back mechanically even | `--seal-wear 0.6`. Prefer reseal­ing with `--press starved` — the model places the wear better than the filter can |
| seal less clear on the paper than the artwork was | `--seal-wear` should be 0 (the default). Also check `--seal-knockout`: on a seal with pale washes, lower it to `8` |
| every seal in the batch equally half-legible | that is the press grade and wear not varying. Both fluctuate per photograph by default — check that `--press` and `--seal-wear` were not pinned for the whole batch |
| caption too heavy or too dark | `--caption-opacity 0.72 --caption-weight 0` |
| caption too thin or spindly | `--caption-weight 0.3`. Do not fix this with opacity — pale is the ink, not the stroke |
| caption too pale or patchy | `--caption-wear 0.1`. Also check `--caption-tint`: a pale seal ink drags the caption toward the paper |
| caption too clean, wants a worn ribbon | `--caption-wear 0.7` |
| caption unevenness looks mechanical | `--caption-strike 0.65` |
| stack caption under the seal | `--layout stacked` |
| pale box around the seal | raise `--seal-knockout`, e.g. `24` |
| this one's look is wrong, try again | `--seed 41` (any number) |
| the batch looks too samey | raise `--variation`, e.g. `0.85` |
| the batch looks inconsistent | lower `--variation`, e.g. `0.35` |
| make them all identical again | `--variation 0` |

Only a change to the seal *artwork* — shape, border, ink colour, wear — needs a
new generation. Regenerate the seal alone and re-composite; never regenerate an
accepted composite.

Full mapping, including the Chinese revision phrases, is in
`reference/revisions.md`.

## Variation

A batch where every caption sits in the same place in the same face at the same
weight reads as a template. `compose.py` therefore samples a look per photo,
within curated ranges that all stay inside the house style.

The seed defaults to a checksum of the photo's filename. Two consequences worth
knowing:

- Each photo in a batch differs from its neighbours automatically.
- Any one photo re-composites **identically** every time, so a revision changes
  only what you asked it to change.

What varies: caption face, size, opacity, tracking, line spacing, stroke weight,
ink texture, per-glyph wobble and strike, alignment, and whether it takes the
seal's colour or stays neutral; the group's layout and placement; seal scale, ink
density, and press wear; paper tone, grain, mottle, margin, and gap.

What never varies: the canvas size, the orientation rule, the photograph.

- `--seed N` rerolls one photo's look. The seed is printed on every run and
  recorded in the sidecar, so a look you like can be pinned.
- `--variation 0` reproduces the fixed house default exactly.
- `--variation 0.3` keeps the differences subtle; `1.0` uses the full range.
- Any explicit flag overrides the sampled value for that property alone.
- The face pool is small and entirely monospaced — Courier New and Courier. Book
  serifs read as a modern publication, plain sans monospace reads as a code
  editor, and American Typewriter, at every weight, reads as a thin spindly
  serif under this format's pale ink. The even rhythm of a monospaced face is
  much of what makes a caption look struck by a machine rather than set by a
  designer. `--font` pins any face when a photo wants one, including the bold
  Couriers that are kept out of the sample.
- Caption ink is one control, not four. `--caption-wear` is the ribbon's
  condition: fresh ink is even and reasonably dark, a dry ribbon is pale, patchy
  and visibly uneven letter to letter. It drives opacity, mottling, per-glyph
  strike and stroke weight together, because on a real machine those go together
  — dark confident ink riddled with dropout, or pale ink struck with perfect
  consistency, are combinations that never occur and both read as an effect
  applied to text. It fluctuates per photograph and leans fresh, for the same
  reason the seal's press does. Any single property can still be set explicitly,
  which is what makes "drier, but keep it this dark" expressible.
- Caption stroke weight is never thinned below the face's own. These are light
  faces already, and paleness belongs in the ink colour rather than in the
  stroke — a struck letter is a solid slab of ribbon ink that happens to be
  grey, not a hairline.
- The caption is pale but never faint to the point of disappearing. Whatever ink,
  tint and opacity get sampled, `compose.py` darkens the ink until what actually
  lands on the paper clears a minimum contrast. Faintness is a look; illegibility
  is a bug, and a pale seal ink plus a low opacity used to produce one silently.

When the user says a batch looks too samey, raise `--variation`. When they say it
looks inconsistent, lower it. Neither is a reason to regenerate a seal.

## Seal quality

A seal is judged on seven separate axes. They fail in different directions and
fixing one must not undo another.

**1. Pressure — uneven, part crisp and part starved.** A real stamp never inks
evenly: the block takes ink in some passages and is starved in others, and both
happen inches apart in one impression. `compose.py` supplies this — `--seal-wear`
varies pressure across the seal at final size, breaking strokes into specks and
skips in some regions while leaving others sharp. So the prompt asks for fine
grain and eaten edges, and the script adds the regional unevenness on top. If a
seal still looks mechanically clean, raise `--seal-wear`; that is a flag, not a
reseal.

**2. Likeness — close, and resolved to a degree that varies.** The seal should look very much
like the photograph: the same object, the same arrangement, the same colours,
recognisable at a glance as the thing that was photographed. Resemblance is not
the enemy and should not be traded away for stylishness.

What makes it a seal rather than a small photograph is that it is not equally
clear everywhere. Some passages resolve fully — enough to identify the subject
beyond doubt — while others dissolve into grain, break up, or drop out, and the
eye completes them. That selective clarity is the whole effect: it is what keeps
the impression from being too real, and what makes it read as artistic rather
than reproduced. A seal that is uniformly sharp is a copy; a seal that is
uniformly vague is a smudge; the good one is both at once, in different places.

How *much* resolves has to change between photographs, and this is the property
most likely to come out the same ten times running. A hand inking a pad and
pressing it does not repeat itself; a drawer of stamped papers holds clean
impressions and half-starved ones side by side. If every seal in a batch is
equally half-legible, the unevenness stops reading as pressure and starts reading
as one effect applied to everything — which is the failure it was meant to avoid.
This is the prompt's job, not a post-process. `build_prompt.py --press` picks an
impression grade per photograph — crisp / normal / starved, weighted roughly
40 / 45 / 15 — so the model varies the impression *while drawing it*. A filter
applied afterwards can only remove ink, never decide where the ink should have
been thin, and running one over a seal that already varies well starves it twice.
`compose.py --seal-wear` therefore defaults to 0, and exists to rescue a seal that
came back mechanically even rather than to supply the character by default.
They compound, so an occasional pairing of a starved grade with a high wear
overshoots — lower `--seal-wear` rather than reseal.

Blank paper inside the impression is the thing to watch. It costs likeness faster
than it buys character: the subject has to stay identifiable at every grade, and
"under-inked" is the target rather than "incomplete".

Coarseness serves the same end. A slightly rough, granular impression reads as a
physical object pressed onto paper. It is also, in practice, what keeps the seal
from looking machine-made: the tell of a generated image is *evenness* — even
detail, even wear, even spacing, tidy symmetry. Irregularity at every scale is
the cure, and it has to be real irregularity rather than a texture laid over the
top.

**3. Impression — inked and affixed, not printed as a poster.** This is the axis
that matters most and the one easiest to lose. A seal is a physical object that
was inked and pressed onto paper: fine grain, stipple, softly broken edges,
uneven pressure. The target word is 钤印 — a stamp affixed to a page.

The failure it guards against is the **linocut poster**: large flat fields of
solid colour, heavy slabs, thick graphic outlines, three saturated inks, big
simple shapes. Asking for "a print in limited inks" pulls hard that way. It looks
competent on its own and overwhelms the photograph it sits beside.

Detail is not the enemy — smooth tone is. A blossom seal should have individual
petals; a bronze should keep its modelling. What must not happen is that detail
arriving as photographic gradient. It arrives as ink grain.

Say **"inked and pressed onto paper"**, never "cut coarse", "flat inks", or
"carved block". Those phrasings produce the poster.

**4. Focus — a choice, per photograph.** A seal is not obliged to carry the whole
frame. Two correct modes:

- *Whole view* — the composition the camera saw, its depth and flanking elements.
- *Subject focus* — the primary subject with whatever physically carries it,
  surroundings reduced to a single loose stroke or dropped entirely. Right when
  one subject dominates: a sculpture, a pumpkin, a blossoming branch.

Omitting a background is allowed. Inventing one is not.

**5. Provenance — derived, not designed.** What the seal shows must be in the
photograph, in the same place, same number, same irregularity. Nothing added,
rearranged, evenly spaced, or symmetrised. The attractor to resist is the retro
travel badge — a shield or roundel, symmetrical cypresses, evenly spaced ships,
lollipop figures. A shield is not in the shape vocabulary at all.

**6. Not a processed photograph.** Never threshold, halftone-screen, dither,
posterise, duotone, trace, or auto-vectorise the source. Those keep every pixel
and press nothing; the result reads as a photocopy beside the photograph.

**7. Colour — the photograph's own, measured.** `inspect_source.py` prints a
Palette line with real hex values and each colour's share of the frame. Paste it
into the prompt. "Preserve the colour memory" is an adjective, and a model will
substitute a stock palette for it — pale stucco comes back brick red, a pastel
sunset comes back saturated navy.

The rule is fidelity, in both directions. Keep every element at its real hue
*and* lightness: never deepen or saturate a colour to make the print look bolder,
and equally never grey it down or wash it out in the name of restraint. A seal is
as colourful as its photograph is. Draining a strong colour is the same error as
inventing one — it just fails quietly instead of loudly.

- Fine granular pressed ink: stipple, grain, softly broken edges, uneven pressure.
- Small, light and quiet — closer to a botanical stamp or a library mark than to
  a poster.
- Wear is irregular, non-periodic, varied in scale, and responsive to ink
  coverage. Never worm-like squiggles, maze patterns, moiré, fingerprint loops,
  ornamental curls, or uniform procedural noise. Treat any of these as a failed
  seal and regenerate it.
- A square seal shows a complete, unmistakably four-sided worn ink border — worn
  corners and broken ink are welcome, a clean digital frame is not.
- A circular seal stays visibly circular through its dry-ink gaps.
- A silhouette seal keeps the subject's defining outline and is not boxed into a
  generic rectangle.
- Signs, numbers, faces, and defining structure stay legible enough to identify
  the source.

## Guardrails

- One flat composite per photo. Not a book mockup, scrapbook, poster
  presentation, or before/after board.
- Never crop, extend, outpaint, retouch, or repaint the source photograph. The
  script does not, and neither should any prompt you write.
- No gradient, dissolve, feather, page turn, gutter, overlap, diagonal split, or
  decorative separator at the seam.
- Do not let the seal dominate the paper or eat its quiet negative space.
- No decorative labels, logos, watermarks, dense copy, or invented objects.
- Return one finished asset per photo and report every saved path.
- Delete intermediate seals and test renders; keep only the final assets.

## Batch efficiency boundary

Save time through bounded parallel generation, shared metadata preparation,
grouped review, flag-only revisions, and one final export. Never save time by
lowering model quality, weakening a prompt, skipping a source, shrinking review
previews below a useful size, accepting a failed result, or lowering the export
specification.

## Reference

- `scripts/plan_batch.py --help` — resolve rows, captions, and output paths.
- `scripts/build_prompt.py --help` — assemble the seal prompt from facts.
- `scripts/check_seal.py --help` — compare a seal's colours to its photograph.
- `reference/seal-prompt.md` — the seal generation prompt, four calibration
  seals, and worked examples.
- `reference/revisions.md` — revision phrases mapped to flags or reseals.
- `reference/checklist.md` — what to check by eye once verify.py passes.
- `reference/full-composite-path.md` — the fallback path where a model renders
  the whole frame, and how to keep it honest.
