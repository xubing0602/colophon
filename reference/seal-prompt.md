# Seal prompt

The seal is generated **alone**. Nothing in this prompt should mention the
photograph's placement, the square canvas, the seam, or the caption — `compose.py`
owns all of that. Keeping those instructions out is what stops them from being
half-remembered and half-applied.

## The target, in one line

**A small seal, inked and pressed onto paper.** Not a poster, not a linocut, not
a filtered photograph. The feel of 钤印 — a stamp affixed to a page.

## Use the script

`build_prompt.py` emits this prompt with the palette already measured and every
invariant clause intact:

```bash
python build_prompt.py --photo source/IMG_9001.heic \
  --subject "..." --focus subject --keep "..." --drop "..." \
  --detail "..." --lead-ink "..." --support "..."
```

The template below is what it produces, kept here so you can see what each clause
is for and judge whether a photograph needs something the flags cannot express.
Retyping it by hand is the main way seals drift between photographs, so start
from the script's output and add to it rather than rebuilding it from scratch.

## Template

Replace bracketed values with facts visible in the source. Delete unused lines.

```text
Asset type: one small hand-pressed seal impression, inked and affixed to paper -- the character of a rubber stamp or a Japanese hanko pressed by hand. Alone on blank paper.

Subject: [subject, in one concrete phrase — e.g. "a cherry branch in full blossom against a dark ground"].

FOCUS. [Choose one and delete the other:]
[Whole view: Keep the composition the camera saw -- the framing, the depth, the flanking elements, the ground and sky.]
[Subject focus: Center on [the primary subject]. Reduce the surroundings to a light suggestion -- a single loose stroke of [colour] for [the sea / the sky / the ground] -- or leave them out entirely. The seal does not have to carry the whole photograph; when one subject dominates, let it be the seal and let the rest fall away.]

INK CHARACTER. Fine, granular and delicate. The impression is built from small ink grain, stipple and softly broken edges -- ink sitting on absorbent paper, with the pressure uneven and the edges eaten slightly. Detail survives and is wanted: individual petals, dots, leaves, mouldings, railings, figures. It survives as fine ink marks and grain, never as smooth photographic tone or gradient.

LIKENESS. The seal should look very much like the photograph -- the same object, the same arrangement, the same colours, recognisable at a glance as the thing that was photographed. Do not stylise the subject away or simplify it into a motif; resemblance is wanted. [Then pick ONE of the three impression grades below and paste it here.] Slight coarseness throughout is wanted, and every irregularity should be genuinely irregular -- never a repeated texture, never evenly distributed, never tidy or symmetrical.

  crisp:   This impression came out well. It took the ink cleanly and most of it resolves: the subject is fully legible throughout, with only a few passages going grainy or thinning at an edge. Still a pressed mark rather than a photograph -- the texture is ink grain, the edges are slightly eaten -- but a clean, confident one.

  normal:  This impression is ordinary: mostly it took the ink, in places it did not. Much of the subject resolves fully, enough to identify it beyond doubt, while other passages go coarse, break up, or thin away and let the eye complete them. Do not render the whole impression at one even level of sharpness -- the unevenness is what makes this a pressed mark rather than a picture.

  starved: This impression came out dry. Whole passages are starved and broken, showing paper through, while a few areas still took the ink properly and read clearly. It should look under-inked rather than incomplete: even at its most broken the subject stays identifiable, and enough of it resolves that the eye can assemble the rest.

UNEVEN PRESSURE. The block did not ink evenly. Some passages took the ink fully and stay sharp; others are starved, showing the paper through, with strokes broken into specks and small skips. The two sit close together in one impression, and where the ink failed is irregular -- not a border effect, not a gradient, not an even distressed overlay across everything.

NOT a bold graphic reduction. No large flat fields of solid colour, no heavy linocut slabs, no thick graphic outlines, no poster-style simplification, no screen-print flattening into a few big shapes. The seal is delicate and fine-grained, not emphatic.

NOT a processed photograph. Do not threshold, halftone-screen, dither, posterise, duotone, trace or auto-vectorise the photograph. Those keep every pixel and press nothing.

DERIVED, NOT DESIGNED. This seal comes from one specific photograph. What it does show must be visible in that photograph, in the same place, in the same number, at the same relative size, with the same irregularity. Do not add, rearrange, evenly space, symmetrise, tidy, or idealise. Do not substitute generic stock elements -- identical cypresses, a neat skyline, lollipop figures -- for what the photograph shows. Omitting the background is allowed; inventing one is not.

This is not a badge, crest, emblem, logo, patch, or travel label. The only boundary is the shape named below, and a seal may have no boundary at all.

Shape: [a circular seal | a square-framed seal | a low panoramic ridge | an arched seal | an irregular silhouette following the subject's own outline | no boundary -- the inked subject alone on the paper].
[For a square seal only: Enclose the motif in one complete, unmistakably square ink border, all four sides visible. Worn corners, uneven pressure, and slight broken ink are wanted; a clean digital frame, photo mat, or generic rectangle is not.]
[For a silhouette or unbounded seal: Follow the subject's own outline. Do not enclose it in a rectangle or any generic frame.]

Colour: take every ink from the photograph itself. Its measured palette is: [paste the Palette line from inspect_source.py]. Keep each element at its real hue and lightness: pale stucco stays pale, a pastel sky stays pastel, white stays white. [Dominant ink, drawn from that palette] leads, with [supporting inks, also from that palette] kept subordinate to it in how much of the seal they cover. Colour that is strong in the photograph stays strong here: do not substitute a stock retro-travel or national-park palette, do not deepen or saturate a colour to make the print look bolder, and equally do not grey down, wash out or desaturate a colour that is genuinely vivid in the source. The seal may be colourful; what keeps it quiet is its small size and light ink weight, not a drained palette.

Scale and weight: small, light and quiet on the page -- quiet in size and ink weight, not in colour. It should read as something pressed by hand at stamp size, delicate rather than emphatic, closer to a botanical stamp or a library mark than to a poster.

Surround: outside the seal's own edge, plain near-white empty paper, with a generous clean margin on all four sides. Nothing besides the single impression in the frame.

Output: a single seal, centred, filling roughly two thirds of the frame.

Do not include: any caption, lettering, date, place name, or number that is not physically part of the subject; any border or frame around the whole image; drop shadows; paper texture; torn edges; a mockup; multiple stamps; a sticker, badge, crest, shield, coat of arms, emblem, logo, patch, roundel, medallion, banner, ribbon, laurel, scroll, or travel-label look; symmetrical, evenly spaced, tidied or idealised arrangement; generic stock elements standing in for what the photograph shows; invented content; recoloured or stock-palette inks; bold poster reduction; large flat colour fields; heavy linocut slabs; thick graphic outlines; glossy finish; clean vector flatness; smooth gradients or blends; continuous photographic tone; repeated worm-like squiggles; maze patterns; moiré; fingerprint-like loops; ornamental curls; tiled or uniform noise fill.
```

## Why the constraints are shaped this way

**"Inked and affixed."** The single most useful framing. A seal is a physical
object that was inked and pressed — that is where the fine grain, the broken
edges and the uneven pressure come from. Ask for a *print* and you get poster
art; ask for a *stamp pressed onto paper* and you get the right thing.

**"Likeness" plus one impression grade.** Resemblance is wanted — a seal that no
longer looks like its photograph has failed, and stylishness is not worth trading
it for. What separates it from a small reproduction is not less likeness but
uneven resolution: parts fully resolved, parts dissolving into grain, the eye
filling the gap. That is also what stops the result looking machine-made, because
the tell of a generated image is evenness — even detail, even wear, even spacing,
tidy symmetry.

The reason this comes in three grades rather than one fixed clause is that *how
much* resolves has to change between photographs. A hand inking a pad and pressing
it does not repeat itself: a drawer of real stamped papers holds clean impressions
and half-starved ones side by side. Ask for the same degree of breakup every time
and you get the opposite of what the unevenness was for — ten seals that are all
identically half-legible, which reads as one effect applied ten times rather than
as a stamp used again and again. `build_prompt.py --press` picks a grade per
photograph, weighted roughly 40% crisp / 45% normal / 15% starved — clean is the
common case and a dry impression the occasional one. Writing by hand, vary it
yourself in about those proportions.

Both grades and `compose.py --seal-wear` act on the same property, from opposite
ends — the grade decides what the model renders, the wear decides what the press
takes off it. They compound, so a `starved` grade that also draws a high wear can
overshoot. That is a `--seal-wear 0.25` fix, not a reseal.

**"Fine and granular, detail survives."** Detail is not the enemy — smooth tone
is. A blossom seal should have individual petals; a sculpture seal should have
the modelling of the bronze. What must not happen is that detail arriving as
photographic gradient. It arrives as grain.

**"Not a bold graphic reduction."** This has to be said explicitly. Asking for a
stamp in limited inks pulls hard toward the linocut poster: big flat shapes,
heavy outlines, three saturated colours. That look is competent and completely
wrong here — it overwhelms the photograph it sits beside.

**"Focus is a choice."** A seal is not obliged to carry the whole frame. When one
subject dominates — a sculpture, a pumpkin, a blossoming branch — the seal is
that subject, with the surroundings reduced to one loose stroke or dropped. Both
whole-view and subject-focus seals are correct; pick per photograph.

The `--keep` flag exists because subject focus is not cutting the subject out.
What physically carries or contains it comes along — the plate under the dessert,
the pier under the pumpkin, the branch the blossoms are on. Those are part of the
thing, and a seal that drops them leaves the subject floating. The wider
environment is what goes: the table, the room, the sky, the shadow. The question
is not "what is the subject" but "where does the subject stop".

**"Derived, not designed."** Asking for a stamp puts a model one short step from
the retro travel badge: a shield, a symmetrical row of cypresses, evenly spaced
ships. Those look competent and have nothing to do with your photograph.

**"Take every ink from the photograph."** "Preserve the colour memory" is an
adjective, and a model will quietly swap a stock palette in for it. Run
`inspect_source.py` and paste the Palette line it prints. Real hex values are
facts; colour memory is a wish.

**"Surround: plain, near-white, empty."** This is the ground *outside* the seal.
`compose.py` multiplies the seal into the real paper and knocks out its ground,
so a busy or dark surround survives as a visible rectangle.

**"Uneven pressure" is asked for and also added.** `compose.py` varies the press
pressure across the finished seal itself, at the size it is printed, which is the
only place fine specks and skips survive -- introduced at source resolution they
average back into haze when the seal is scaled down. Asking the model for it too
is not redundant: a seal generated with clean even ink and distressed afterwards
gets its wear applied to the wrong places, because the script can only starve ink
that is already there. The two compose. If a finished seal still looks
mechanically even, that is `--seal-wear`, not a reseal.

**"No caption or lettering."** The caption is real typewriter text at full
resolution, so it is spelled correctly and stays legible. Text drawn by an image
model is neither.

## Calibration — five seals that were accepted

Prohibitions alone leave a model without a target. These five are the house
standard. They differ in focus, shape and density, and what they share is the
thing to aim for: a small, finely grained impression that looks *affixed* to the
paper, carrying real detail without ever becoming a smooth picture.

They also differ from each other far more than the shared constraints would
suggest, and that is the point. The variety is not decoration applied on top — it
is what happens when each seal answers its own photograph. A batch that comes out
looking uniform usually means the photographs stopped being looked at, not that
the rules were followed too well.

Note what they are not: monochrome. Two are effectively one ink, three carry real
colour — the pumpkin's full-strength yellow against near-black dots, the sakura's
clear pink against olive. Colour follows the photograph. Restraint is a matter of
size and ink weight, and is spent there rather than on the palette.

**A bronze figure in a sculpture garden.** No boundary. The figure at full detail
— the modelling of the torso, the twist of the pose, the rough base — built
entirely from fine stipple in one muted olive-brown ink. The trees behind it and
the bench beside it survive as loose masses of the same ink, much lighter, and the
ground as two thin horizontal strokes. Whole view, but heavily weighted: the
statue is dense, everything else is breath.

**An art-deco tower under a clouded sky.** No boundary. The tower is the only
sharply pressed thing — its crown, the stepped setbacks, the window grid all
legible at stamp size in a cool grey. The cloud bank behind it is soft, torn,
mottled ink in pale grey and buff, with plenty of paper showing through. The
detail is concentrated exactly where the photograph's subject is; the sky is
atmosphere, not drawing.

**A polka-dot pumpkin on a pier.** No boundary. Subject focus at its purest: the
pumpkin alone, every dot present and irregular, the ribbing and the leaning stem
intact, in its real yellow with near-black dots. The sea is one loose horizontal
stroke of pale blue behind it. The pier, hills and sky are simply gone — and
nothing is missing.

**A cherry branch in blossom.** No boundary. A wide, low, panoramic sweep across
the paper. Individual five-petalled blossoms, buds, stamens and thin twigs, in a
soft pink with muted olive for the leaves and branch. Dense at the clusters, open
between them, exactly as the branch really was. Detail everywhere, tone nowhere.

**A kakigori on a metal plate.** No boundary. The clearest case of likeness done
right: set beside the photograph it is obviously the same dessert, in the same
colours — the syrup's warm orange, cream white, a cool grey for the plate — and
nothing has been stylised away. What keeps it from being a small photograph is
that the clarity is not even. The mandarin segments and the banana slices at the
crown resolve fully; the body of the shaved ice goes coarse and grainy and part of
the plate's rim simply thins out. It is legible enough to name and rough enough
not to be real. The metal plate and the spoon come along because they carry the
subject; the wooden table and its shadow are gone. The seal ends where the object
ends.

Four patterns are worth extracting:

- **Most good seals have no boundary at all.** The bounded shapes in the table
  are for when the subject genuinely wants a frame — signage, a vaulted portal, a
  dense storefront. Reaching for a circle by default is what starts a seal down
  the badge road.
- **Detail is spent unevenly.** The subject gets the fine, dense pressing; the
  surroundings get a fraction of that, or nothing. A seal with uniform detail
  across the whole frame is the one that reads as a shrunken copy of the
  photograph.
- **Likeness is not the risk; evenness is.** All five are plainly recognisable as
  their photographs, in their photographs' colours, and none of them has been
  simplified into a motif. What makes each one a mark rather than a copy is that
  it resolves in some places and dissolves in others. Reducing likeness to make a
  seal feel more designed trades away the thing that makes it worth having.
- **The subject includes what carries it.** The plate under the dessert, the pier
  under the pumpkin, the branch the blossoms are on, the base under the bronze —
  each of those is part of the thing, and a seal that drops them leaves the
  subject floating. What goes is the wider environment: the table, the room, the
  sky, the shadow on the floor. The question is not *what is the subject* but
  *where does the subject stop*, and answering it deliberately is most of what
  separates a seal that feels placed from one that feels cut out.

## Worked example — subject focus

For a photograph of a yellow polka-dot pumpkin on a concrete pier, sea and hills
behind it.

```text
Asset type: one small hand-pressed seal impression, inked and affixed to paper -- the character of a rubber stamp or a Japanese hanko pressed by hand. Alone on blank paper.

Subject: a large yellow pumpkin covered in black dots, standing on a concrete pier by the sea.

FOCUS. Center on the pumpkin. Reduce the surroundings to a light suggestion -- one loose horizontal stroke of pale blue behind and beside it for the sea -- and leave out the pier, the hills and the sky.

INK CHARACTER. Fine, granular and delicate. The impression is built from small ink grain, stipple and softly broken edges -- ink sitting on absorbent paper, with the pressure uneven and the edges eaten slightly. Detail survives and is wanted: every dot on the pumpkin, its ribbed segments, the curl of the stem. It survives as fine ink marks and grain, never as smooth photographic tone or gradient.

NOT a bold graphic reduction. No large flat fields of solid colour, no heavy linocut slabs, no thick graphic outlines, no poster-style simplification. The seal is delicate and fine-grained, not emphatic.

NOT a processed photograph. Do not threshold, halftone-screen, dither, posterise, duotone, trace or auto-vectorise the photograph.

DERIVED, NOT DESIGNED. The dots are the size and spacing they actually are, dense at the ribs and sparser across the faces. The stem leans the way it leans. Do not tidy or regularise them.

Shape: no boundary -- the inked pumpkin alone on the paper.

Colour: take every ink from the photograph itself. Its measured palette is: mid moderately saturated yellow #d9b83c (18% of the frame); very dark neutral grey #1c2029 (14%); light muted blue #a8c4d8 (31%); mid muted blue #6d94b4 (22%). The yellow leads at its real strength -- this pumpkin is vividly yellow and the seal should be too -- with the near-black dots and one pale blue stroke subordinate to it in coverage. Do not deepen or saturate a colour to make the print look bolder, and do not wash the yellow out to make it look restrained.

Scale and weight: small, light and quiet on the page — delicate rather than emphatic, closer to a botanical stamp than to a poster.

Surround: outside the seal's own edge, plain near-white empty paper, with a generous clean margin on all four sides.

Output: a single seal, centred, filling roughly two thirds of the frame.

Do not include: [full negative list from the template].
```

## Reseal prompt

When only the seal artwork is wrong, regenerate the seal — not the composite.

```text
Regenerate this seal impression. Change only: [focus | shape | ink character | colour | which features are kept].

Requested change: [precise instruction].

Keep everything else: the same subject, the same source photograph, the same fine granular pressed-ink character, the same near-white empty surround, the same generous margin, no caption, no frame around the whole image.
```

Then re-run `compose.py` with the flags the sidecar `.webp.json` records.
