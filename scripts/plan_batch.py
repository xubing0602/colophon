"""Turn metadata rows into the exact compose.py commands for a batch.

Removes the three mistakes that a hand-built batch makes: selecting the wrong
rows (the header line makes row numbers ambiguous), formatting a caption
inconsistently, and letting an output basename drift from its source.

Row numbers here are DATA rows, 1-indexed, with the header excluded -- so
`--rows 112-121` means the 112th photo, which is line 113 of the file. That is
the same numbering a spreadsheet shows when the header is frozen.

Arguments:
  --csv PATH            Metadata CSV. Required. Needs a column naming the source
                        file; place/city/country/month_name/year are used for the
                        caption when present.
  --source DIR          Directory of source photographs. Default "source".
  --output DIR          Directory for finished composites. Default "output".
  --seals DIR           Directory for generated seal artwork. Default "seals".
  --rows SPEC           Which data rows, 1-indexed, header excluded. Accepts
                        ranges and lists: "112-121", "3", "1-10,25,40-42".
  --files NAMES         Comma-separated source filenames or stems instead of row
                        numbers. Matched against the CSV's file-name column.
  --all                 Every row in the CSV.
  --ext EXT             Output extension. Default "webp".
  --caption-fields SPEC Semicolon-separated caption lines, each a comma-separated
                        list of column names joined with ", ". Default
                        "place;city,country;month_name,year" which yields
                        "Chaoyang Road" / "Beijing, China" / "MAR 2026".
  --file-column NAME    Column holding the source filename. Default: auto-detect
                        among file_name, filename, file, source, name.
  --json                Emit a JSON plan instead of shell commands.
  --check               Only report which sources are missing or unmatched.

Examples:
  python plan_batch.py --csv manifest/metadata.csv --rows 112-121
  python plan_batch.py --csv manifest/metadata.csv --rows 112-121 --json
  python plan_batch.py --csv manifest/metadata.csv --files IMG_4705.heic,IMG_6773.heic
"""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import sys
from pathlib import Path

FILE_COLUMNS = ["file_name", "filename", "file", "source", "name"]
DEFAULT_CAPTION = "place;city,country;month_name,year"


def parse_rows(spec: str) -> list[int]:
    """"1-10,25,40-42" -> [1..10, 25, 40, 41, 42], preserving order, de-duplicated."""
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part[1:]:
            lo_s, hi_s = part.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            if lo > hi:
                lo, hi = hi, lo
            out += list(range(lo, hi + 1))
        else:
            out.append(int(part))
    seen: set[int] = set()
    return [n for n in out if not (n in seen or seen.add(n))]


def detect_file_column(fieldnames: list[str], explicit: str | None) -> str:
    if explicit:
        if explicit not in fieldnames:
            raise SystemExit(f"error: column {explicit!r} not in CSV; have {fieldnames}")
        return explicit
    for cand in FILE_COLUMNS:
        if cand in fieldnames:
            return cand
    raise SystemExit(
        f"error: no file-name column found; looked for {FILE_COLUMNS}, CSV has {fieldnames}. "
        "Pass --file-column."
    )


def build_caption(row: dict, spec: str) -> list[str]:
    """Render caption lines from column names, skipping lines with nothing in them."""
    lines = []
    for group in spec.split(";"):
        cols = [c.strip() for c in group.split(",") if c.strip()]
        values = [str(row.get(c, "") or "").strip() for c in cols]
        values = [v for v in values if v]
        if not values:
            continue
        # "city, country" joins with a comma; "month_name year" with a space.
        joiner = ", " if len(cols) > 1 and "year" not in cols else " "
        lines.append(joiner.join(values))
    return lines


def resolve_source(name: str, source_dir: Path) -> Path | None:
    """Find the source file, tolerating a CSV extension that no longer matches."""
    exact = source_dir / name
    if exact.exists():
        return exact
    stem = Path(name).stem
    matches = sorted(p for p in source_dir.glob(f"{stem}.*") if p.is_file())
    return matches[0] if matches else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--source", default="source")
    ap.add_argument("--output", default="output")
    ap.add_argument("--seals", default="seals")
    ap.add_argument("--rows")
    ap.add_argument("--files")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--ext", default="webp")
    ap.add_argument("--caption-fields", default=DEFAULT_CAPTION)
    ap.add_argument("--file-column")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not (args.rows or args.files or args.all):
        raise SystemExit("error: choose rows with --rows, --files, or --all")

    with open(args.csv, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise SystemExit("error: CSV has no header row")
        file_col = detect_file_column(list(reader.fieldnames), args.file_column)
        rows = list(reader)

    source_dir = Path(args.source)
    output_dir = Path(args.output)
    seals_dir = Path(args.seals)

    selected: list[tuple[int, dict]] = []
    if args.all:
        selected = list(enumerate(rows, start=1))
    elif args.rows:
        for n in parse_rows(args.rows):
            if 1 <= n <= len(rows):
                selected.append((n, rows[n - 1]))
            else:
                print(f"warning: row {n} is outside 1-{len(rows)}", file=sys.stderr)
    else:
        wanted = [w.strip() for w in args.files.split(",") if w.strip()]
        by_name = {r[file_col]: (i, r) for i, r in enumerate(rows, start=1)}
        by_stem = {Path(r[file_col]).stem: (i, r) for i, r in enumerate(rows, start=1)}
        for w in wanted:
            hit = by_name.get(w) or by_stem.get(Path(w).stem)
            if hit:
                selected.append(hit)
            else:
                print(f"warning: {w!r} not found in {args.csv}", file=sys.stderr)

    plan = []
    missing = 0
    for n, row in selected:
        name = row[file_col]
        src = resolve_source(name, source_dir)
        stem = Path(name).stem
        if src is None:
            missing += 1
        plan.append(
            {
                "row": n,
                "file_name": name,
                "stem": stem,
                "source": str(src) if src else None,
                "seal": str(seals_dir / f"{stem}_seal.png"),
                "output": str(output_dir / f"{stem}.{args.ext.lstrip('.')}"),
                "caption": build_caption(row, args.caption_fields),
            }
        )

    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 1 if missing else 0

    if args.check:
        for item in plan:
            state = "OK     " if item["source"] else "MISSING"
            print(f"{state} row {item['row']:>4}  {item['file_name']}")
        print(f"\n{len(plan) - missing}/{len(plan)} sources present")
        return 1 if missing else 0

    print(f"# {len(plan)} photo(s) from {args.csv}")
    if missing:
        print(f"# WARNING: {missing} source file(s) not found under {source_dir}/")
    print(f"# seals expected at {seals_dir}/<stem>_seal.png\n")
    for item in plan:
        if not item["source"]:
            print(f"# row {item['row']}: {item['file_name']} -- SOURCE MISSING, skipped")
            continue
        caps = " ".join(f"--caption {shlex.quote(c)}" for c in item["caption"])
        print(
            f"python compose.py --photo {shlex.quote(item['source'])} "
            f"--seal {shlex.quote(item['seal'])} {caps} "
            f"--out {shlex.quote(item['output'])}"
        )
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
