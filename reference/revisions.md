# Revisions

Two kinds. Most requests are the cheap kind.

## Flag revisions — rerun compose.py, no generation

The seal artwork is untouched, so these cost nothing and cannot disturb the
photograph. Start from the sidecar `.webp.json` written next to the output; it
records the exact flags used *and* the sampled look under `resolved_variation`,
so a revision is a rerun with one value changed.

Because most properties are sampled per photo, there are two different kinds of
request here. "Make the caption smaller" pins one property with a flag. "Try a
different look" rerolls all of them at once with `--seed`. Reach for the seed
only when the complaint is about the whole arrangement, not one property — a
reroll discards everything that was already right.

| Request | Flag |
|---|---|
| `缩小 10%` / make the seal smaller | `--seal-scale 0.9` |
| `放大一点` / make the seal larger | `--seal-scale 1.12` |
| seal came out tiny in the panel | should not happen — the seal fills its panel regardless of the art's resolution. If it does, check `--seal-scale`, and check the seal art for a stray mark far from the motif: the trim boxes to that mark and leaves the motif small inside it |
| seal looks soft or blurry | the art was small and was enlarged to fill the panel. The run prints a size note when this happens — regenerate the seal larger |
| `移动到左上` / top-left | `--anchor top-left` |
| `移动到右上` / top-right | `--anchor top-right` |
| `移动到左下` / bottom-left | `--anchor bottom-left` |
| `移动到右下` / bottom-right | `--anchor bottom-right` |
| `居中` / centre it | `--anchor center` |
| `纸张不要那么旧` / less aged paper | `--paper-tone 242,240,235 --mottle 1.6` |
| `纸张更暖` / warmer paper | `--paper-tone 240,235,224` |
| `纸张质地更细` / finer paper texture | `--grain 1.2` |
| paper texture too visible at all | `--grain 0.8 --mottle 1.4` |
| flat, dead paper | `--grain 2.4 --mottle 3.2` |
| caption too dark or too bold | `--caption-opacity 0.72 --caption-weight 0` |
| caption too pale, patchy or faded | `--caption-wear 0.1` for a fresh ribbon. Check `--caption-tint` too: a pale seal ink drags the caption toward the paper colour |
| caption too clean, looks typeset rather than typed | `--caption-wear 0.7` |
| caption should be drier but no paler | `--caption-wear 0.7 --caption-opacity 0.88` — the explicit flag overrides that one property of the ribbon |
| every caption in the batch equally faded | the ribbon fluctuates per photograph; check `--caption-wear` was not pinned across the batch, and that `--variation` is not near 0 |
| caption looks like a thin spindly serif | American Typewriter, which is proportionally spaced and too finely drawn for this format's pale ink. The family is out of the pool — if it appears, `--font` was pinned to it |
| caption too thin, undernourished | `--caption-weight 0.3`. Never fix thinness with opacity: the ink is meant to be pale, the stroke is not meant to be thin |
| caption letters all inked identically | `--caption-strike 0.65` |
| caption too small or too large | `--caption-size 30` |
| caption wording, spelling, or lines | edit the `--caption` values |
| different typewriter face | `--font "/System/Library/Fonts/Courier.ttc#0"` |
| seal ink too heavy | `--seal-strength 0.85` |
| `印章太干净` / seal looks machine-printed, too even | reseal with `--press starved`, which lets the model decide where the ink failed. `--seal-wear 0.6` is the fallback when a reseal is not worth it |
| seal is less clear on the paper than the generated artwork was | `--seal-wear` should be `0`, its default — it can only remove ink, so it compounds with wear the model already drew. On a seal with pale washes also lower `--seal-knockout` to `8` |
| seal too broken up, too much blank paper inside it | reseal with `--press crisp` or `normal`. Check `--seal-wear` is `0` |
| every seal in the batch is equally half-legible | the level is not fluctuating. `build_prompt.py --press` and `--seal-wear` both vary per photograph on their own; check neither was pinned across the batch, and that `--variation` is not near 0 |
| this photo deserves a cleaner impression | `--press crisp` when building the prompt, and `--seal-wear 0.2` when compositing |
| wear falls in the wrong places | `--seed N` — the wear pattern follows the look seed |
| `上下拼接` / paper below, against the house rule | `--band-side bottom` |
| `左右拼接` / paper on the right, against the house rule | `--band-side right` |
| caption beside the seal instead of under it | `--layout split` |
| caption under the seal instead of beside it | `--layout stacked` |
| more blank paper around the group | raise `--margin`, e.g. `0.10` |
| pale rectangle visible around the seal | raise `--seal-knockout`, e.g. `24` |
| faint parts of the seal disappearing | lower `--seal-knockout`, e.g. `8` |
| caption ink should match the seal colour | `--caption-tint 0.75` |
| caption ink should stay neutral grey | `--caption-tint 0` |
| caption letters too thin | `--caption-weight 0.3`. Too fat: `--caption-weight 0`. Paleness belongs in the ink, so lighten with `--caption-opacity`, never a negative weight |
| caption too clean, wants more press wear | `--caption-texture 0.35` |
| caption too eroded to read | `--caption-texture 0.05` |
| caption lines too tight or too loose | `--caption-spacing 1.5` / `1.8` |
| caption letters too tight | `--caption-tracking 2` |
| caption should hang off the seal's right edge | `--caption-align right` |
| a different caption face | `--font "/System/Library/Fonts/Courier.ttc#1"` for Courier Bold (the `#N` picks a weight inside a .ttc) |
| caption shows an empty box for an accent or apostrophe | already handled — unsupported characters are substituted automatically and the run prints a note. If you see one, report the face |
| caption face looks like a code editor, or like a book | should not happen — plain sans monos and book serifs are both excluded from the pool. Check whether `--font` was pinned to one |
| `换一个样式` / try a different look for this one | `--seed 41`, any number |
| the batch looks too samey | `--variation 0.85` |
| the batch looks inconsistent | `--variation 0.35` |
| make every composite match exactly | `--variation 0` |

### Splice orientation

The house rule is derived from the source, not chosen: landscape gets paper
below, portrait gets paper on the right. `--band-side` overrides it, but only
when the user explicitly asks for the other arrangement — never to make a seal
fit better. Pass the same `--band-side` to `verify.py`, or it will correctly
report the band as being on the wrong side.

Overriding usually forces the photo to be inset with margins rather than bleeding
to the edges, because the band on the unnatural side has to be carved out of the
picture's own dimension. That is expected, and the photo is still uncropped.

## Reseal revisions — regenerate the seal only

These change the artwork, so they need one generation. Use the reseal prompt at
the end of `reference/seal-prompt.md`, then re-composite with the sidecar's flags.

| Request | Change |
|---|---|
| `方形边框` / add a square border | add one complete worn four-sided ink frame around the existing motif |
| `圆形图章` / circular seal | recast the motif inside a circular hand-pressed boundary |
| `异形章` / silhouette seal | follow the subject's own outline, no enclosing rectangle |
| `不要那么规整` / less tidy | roughen the ink boundary with restrained missing ink and eaten edges — not a torn-paper collage |
| `保留原来的颜色` / keep the original colours | restate the source hue relationships from the Palette line, each element at its real hue and lightness |
| seal washed out, colours drained | reseal at the photograph's real saturation. Quiet means small and lightly inked, not desaturated — name the colour and its strength ("the pumpkin is a full, vivid yellow") |
| different spot colour | name the new dominant ink concretely |
| seal looks photographic rather than pressed | push the *medium*, not the crop: more ink grain and stipple, softly broken edges, more uneven pressure and ink loss. Do not remove scene content to fix this |
| seal looks like a travel badge, crest, or logo | reseal with the DERIVED-NOT-DESIGNED clause emphasised: same elements, same places, same counts, same unevenness; no shield, roundel, banner, or stock icons |
| seal invented or rearranged things | name what is wrong ("there are three boats, not five, and they are not evenly spaced") and reseal |
| seal colours drifted from the photo | paste the Palette line from `inspect_source.py` into the reseal prompt and name the offending element ("the towers are pale stucco #d8cbb0, not brick red") |
| seal reads as a photocopy or halftone of the photo | reseal emphasising INKED AND PRESSED: hand-placed stipple, ink grain, edges eaten by the paper. No threshold, halftone screen, dither, duotone, or auto-trace of the photograph |
| seal looks like a poster or linocut | reseal asking for "inked and pressed onto paper", fine grain and stipple, delicate not emphatic. Never say "cut coarse", "flat inks", or "carved block" — those phrasings cause it |
| seal too flat and simplified, lost its detail | keep the detail, express it as fine ink grain rather than as flat shapes |
| seal should be just the subject | reseal with subject focus: centre the subject, reduce surroundings to one loose stroke or drop them |
| seal should show the whole view | reseal with whole-view focus: the framing, depth and flanking elements |
| seal reads as a small reproduction | it is an evenness problem, not a likeness problem. Do not reduce the resemblance — reseal asking for uneven resolution: some passages fully resolved, others dissolving into grain or dropping away, with a coarser impression overall |
| seal looks machine-made or AI-like | evenness is the tell. Reseal asking for irregularity that is genuinely irregular — uneven detail, uneven wear, nothing tidy, symmetrical, evenly spaced or repeated |
| seal no longer looks like the photo | likeness was traded for style. Reseal naming the subject, its arrangement and its real colours, and keep the unevenness in the rendering rather than in the resemblance |
| seal too faithful, reads as a traced copy of the photo | it is a tone problem, not a detail problem: the impression is carrying smooth photographic gradient. Reseal asking for the same detail rebuilt out of ink grain and stipple, with uneven pressure and broken edges. Keep the composition and keep the detail |
| seal too crude, scene no longer readable | finer grain and one more muted ink — not bigger flat shapes, which is the poster failure |
| worm-like, maze, moiré, or looping fill inside the seal | regenerate; this is a failed seal, never accept it |

## Never

- Never regenerate an accepted composite to make an unrelated change.
- Never change the photograph to make the seal easier to design.
- Never apply a revision to more outputs than the user asked about.
