#!/usr/bin/env python3
"""Pre-fill the metadata CSV from each photo's EXIF, so captions start as a draft.

Reads the capture date and GPS position embedded in every photo in source/,
then looks the position up on OpenStreetMap (Nominatim) for city, state and
country. The result is manifest/metadata.csv in the format plan_batch.py reads.
Open it, correct what is wrong, fill in what is missing, and use it -- or don't.

It only ever fills empty cells. A value already in the CSV, typed by hand or
from an earlier run, is never overwritten, and existing rows keep their order,
so row numbers used for batches ("rows 112-121") stay valid. Photos not yet in
the CSV are appended at the end, in filename order.

`place`, the caption's first line, is left empty by default: what to call the
spot is a judgment a geocoder makes badly ("Chaoyang Road" vs "the corner by the
bakery"). --suggest-place fills it with OpenStreetMap's name for the spot as a
starting point to edit.

Geocoding sends each photo's coordinates to nominatim.openstreetmap.org, at
most one request per second as its usage policy requires. Photos taken within
about 10 m of each other share one lookup. --no-geocode keeps everything local.

Arguments:
  --root DIR        Project folder holding source/ and manifest/. Default: the
                    current directory.
  --source DIR      Folder of photographs. Default: <root>/source.
  --csv PATH        CSV to create or update. Default: <root>/manifest/metadata.csv,
                    or <root>/metadata.csv if only that one exists.
  --no-geocode      Read EXIF only; leave city, state and country for you.
  --suggest-place   Also fill empty `place` cells with OpenStreetMap's name for
                    the spot (a building, park, street or neighbourhood).
  --dry-run         Report what would change without writing the CSV.

Examples:
  python update_metadata.py --root ~/photos/japan-2026 --dry-run
  python update_metadata.py --root ~/photos/japan-2026
  python update_metadata.py --root ~/photos/japan-2026 --suggest-place
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from stamp_lib import exif_summary

FIELDS = [
    "file_name", "place", "city", "state", "country", "lat", "lng",
    "year", "month", "month_name", "day",
]
IMAGE_SUFFIXES = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "colophon-skill/1.0 (+https://github.com/xubing0602/colophon)"
PLACE_KEYS = (
    "tourism", "amenity", "building", "historic", "leisure", "man_made",
    "road", "neighbourhood", "suburb", "quarter",
)


def format_dms(decimal: float | None, axis: str) -> str:
    if decimal is None:
        return ""
    direction = ("N" if decimal >= 0 else "S") if axis == "lat" else ("E" if decimal >= 0 else "W")
    absolute = abs(decimal)
    degrees = int(absolute)
    minute_value = (absolute - degrees) * 60
    minutes = int(minute_value)
    seconds = round((minute_value - minutes) * 60, 3)
    if seconds >= 60:
        seconds = 0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        degrees += 1
    seconds_text = f"{seconds:.3f}".rstrip("0").rstrip(".")
    return f'{degrees}° {minutes}\' {seconds_text}" {direction}'


def duplicate_stem_warnings(image_paths: list[Path], csv_names: list[str]) -> list[str]:
    """Outputs are named <stem>.webp, so IMG_1.heic and IMG_1.jpg would collide."""
    by_stem: dict[str, list[str]] = {}
    for name in [p.name for p in image_paths] + csv_names:
        names = by_stem.setdefault(Path(name).stem.casefold(), [])
        if name not in names:
            names.append(name)
    return [
        f"warning: {', '.join(names)} share a base name and would write the same output file"
        for names in by_stem.values() if len(names) > 1
    ]


REGION_SUFFIXES = (" Prefecture", " Province", " Metropolis", " Municipality", " Region")


class Geocoder:
    """Nominatim reverse lookups at most once a second, with two caches: spots
    within about 10 m share one street-level lookup, and each region (state,
    prefecture, province) is looked up once at its own level.

    The region lookup fixes how OpenStreetMap files city-regions: a Beijing
    street's `city` is "Dongcheng District" and a Tokyo street's is "Chiyoda",
    with no state at all. One level up they are simply "Beijing" and "Tokyo"."""

    def __init__(self) -> None:
        self.last = 0.0
        self.spots: dict[tuple[float, float], dict[str, str]] = {}
        self.regions: dict[str, dict] = {}

    def _get(self, lat: float, lng: float, zoom: int) -> dict:
        time.sleep(max(0.0, 1.0 - (time.monotonic() - self.last)))
        query = urlencode({
            "format": "jsonv2", "lat": f"{lat:.7f}", "lon": f"{lng:.7f}",
            "zoom": str(zoom), "addressdetails": "1", "accept-language": "en",
        })
        request = Request(f"{NOMINATIM_URL}?{query}", headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=20) as response:  # nosec B310: fixed HTTPS endpoint
                return json.load(response)
        finally:
            self.last = time.monotonic()

    def lookup(self, lat: float, lng: float) -> dict[str, str]:
        key = (round(lat, 4), round(lng, 4))
        if key in self.spots:
            return self.spots[key]
        payload = self._get(lat, lng, 18)
        address = payload.get("address", {})
        city = next((address[k] for k in ("city", "town", "village", "municipality", "county") if address.get(k)), "")
        state = next((address[k] for k in ("state", "province", "region") if address.get(k)), "")
        region_key = address.get("ISO3166-2-lvl4") or address.get("country_code", "")
        if region_key not in self.regions:
            try:
                self.regions[region_key] = self._get(lat, lng, 5)
            except Exception:  # noqa: BLE001 - the street-level answer still stands
                self.regions[region_key] = {}
        region = self.regions[region_key]
        region_name = region.get("name", "")
        for suffix in REGION_SUFFIXES:
            region_name = region_name.removesuffix(suffix)
        if region.get("addresstype") == "city" and region_name:
            city = region_name                    # Beijing, Tokyo, Shanghai
        state = region_name or state
        for suffix in REGION_SUFFIXES:
            state = state.removesuffix(suffix)
        place = payload.get("name") or next((address[k] for k in PLACE_KEYS if address.get(k)), "")
        self.spots[key] = {"place": place, "city": city, "state": state,
                           "country": address.get("country", "")}
        return self.spots[key]


def missing(row: dict[str, str], field: str) -> bool:
    return not row.get(field, "").strip()


def fill_from_exif(row: dict[str, str], exif: dict) -> None:
    text = exif.get("datetime_original") or exif.get("datetime") or ""
    if text:
        try:
            taken = datetime.strptime(text.strip()[:19], "%Y:%m:%d %H:%M:%S")
        except ValueError:
            print(f"warning: {row['file_name']}: unreadable EXIF date {text!r}", file=sys.stderr)
        else:
            values = {"year": str(taken.year), "month": str(taken.month),
                      "month_name": taken.strftime("%b").upper(), "day": str(taken.day)}
            for field, value in values.items():
                if missing(row, field):
                    row[field] = value
    if "gps" in exif:
        lat, lng = exif["gps"]
        if missing(row, "lat"):
            row["lat"] = format_dms(lat, "lat")
        if missing(row, "lng"):
            row["lng"] = format_dms(lng, "lng")


def status(before: dict[str, str], row: dict[str, str]) -> str:
    if not before.get("file_name"):
        return "  (new)"
    return "  (filled in)" if row != before else ""


def fmt_secs(s: float) -> str:
    s = int(s)
    return f"{s // 60}m{s % 60:02d}s"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--source", type=Path, default=None)
    ap.add_argument("--csv", type=Path, default=None)
    ap.add_argument("--no-geocode", action="store_true")
    ap.add_argument("--suggest-place", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    root = a.root.expanduser().resolve()
    source = (a.source or root / "source").expanduser()
    csv_path = a.csv
    if csv_path is None:
        csv_path = root / "manifest" / "metadata.csv"
        if not csv_path.exists() and (root / "metadata.csv").exists():
            csv_path = root / "metadata.csv"
    if not source.is_dir():
        ap.error(f"no source folder at {source}")

    existing: dict[str, dict[str, str]] = {}
    extra_fields: list[str] = []
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            extra_fields = [f for f in (reader.fieldnames or []) if f not in FIELDS]
            for row in reader:
                if row.get("file_name"):
                    existing[row["file_name"]] = {f: row.get(f) or "" for f in FIELDS + extra_fields}
    fields = FIELDS + extra_fields     # keep any columns the user added

    images = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    for warning in duplicate_stem_warnings(images, list(existing)):
        print(warning, file=sys.stderr)

    rows = list(existing.values())
    geo_fields = ["city", "state", "country"] + (["place"] if a.suggest_place else [])
    geocoder = Geocoder()
    changes, added, no_date, no_gps = 0, 0, [], []
    t0 = time.time()
    print(f"{len(images)} photo(s) in {source}, {len(existing)} row(s) already in {csv_path}")

    for i, path in enumerate(images, 1):
        row = existing.get(path.name)
        if row is None:
            row = {f: "" for f in fields}
            row["file_name"] = path.name
            rows.append(row)
            added += 1
        before = row.copy()
        exif = exif_summary(path)
        fill_from_exif(row, exif)
        if missing(row, "year"):
            no_date.append(path.name)
        if "gps" not in exif:
            no_gps.append(path.name)

        if not a.no_geocode and "gps" in exif and any(missing(row, f) for f in geo_fields):
            try:
                found = geocoder.lookup(*exif["gps"])
            except Exception as error:  # noqa: BLE001 - leave these cells empty
                print(f"warning: {path.name}: geocoding failed: {error}", file=sys.stderr)
                found = {}
            for field in geo_fields:
                if missing(row, field) and found.get(field):
                    row[field] = found[field]

        if row != before and before.get("file_name"):
            changes += 1
        el = time.time() - t0
        caption = " / ".join(x for x in (row["place"], ", ".join(v for v in (row["city"], row["country"]) if v),
                                          " ".join(v for v in (row["month_name"], row["year"]) if v)) if x)
        print(f"[{i}/{len(images)}] {fmt_secs(el)} elapsed, ETA {fmt_secs(el / i * (len(images) - i))}  "
              f"{path.name}{status(before, row)}  {caption or '-'}", flush=True)

    if no_date:
        print(f"no capture date in EXIF ({len(no_date)}): {', '.join(no_date)}", file=sys.stderr)
    if no_gps:
        print(f"no GPS in EXIF ({len(no_gps)}): {', '.join(no_gps)}", file=sys.stderr)
    empty_place = sum(1 for r in rows if missing(r, "place"))
    if a.dry_run:
        print(f"dry run: {added} new row(s), {changes} filled in; nothing written")
        return 0
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"done in {fmt_secs(time.time() - t0)}: {added} new row(s), {changes} filled in, in {csv_path}")
    if empty_place:
        print(f"{empty_place} row(s) have no place; fill them in, or the caption starts at the city")
    return 0


if __name__ == "__main__":
    sys.exit(main())
