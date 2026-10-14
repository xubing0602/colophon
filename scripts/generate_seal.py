#!/usr/bin/env python3
"""Generate seal artwork from finished prompts with OpenAI's image API.

For agents that cannot generate images themselves -- Claude Code, or a plain
terminal. Codex does not need this: it draws the seal with its own image tool.

The prompts come from build_prompt.py, extended by whoever looked at the
photograph, and are saved one per photo as seals/prompts/<stem>.txt. Each one
becomes seals/<stem>_seal.png, which is exactly where compose.py and
plan_batch.py expect it. Seals that already exist are skipped, so a stopped
batch picks up where it left off and an accepted seal is never paid for twice.

The key is read from the OPENAI_API_KEY environment variable, or from a .env
file in the current directory or the skill's own directory. It is never
printed.

Arguments:
  PROMPT ...          Prompt files to generate, e.g. seals/prompts/*.txt. Each
                      file's stem names its photo: seals/prompts/IMG_4705.txt
                      becomes seals/IMG_4705_seal.png.
  --seals-dir DIR     Where seals are written. Default: the parent of the
                      prompt file's directory when that directory is called
                      "prompts" (so seals/prompts/x.txt -> seals/x_seal.png),
                      else the prompt file's own directory.
  --out PATH          Output file. Only with a single prompt file; overrides
                      the derived name.
  --model NAME        Image model. Default: COLOPHON_IMAGE_MODEL from the
                      environment or .env, else gpt-image-2. Any model the
                      images API accepts works, e.g. gpt-image-1.5 or a
                      gpt-image-2.5 variant.
  --size WxH          1024x1024 (default), 1536x1024 or 1024x1536. The seal is
                      generated alone and compose.py scales it into the panel,
                      so square is right for nearly every seal.
  --quality Q         low, medium, high (default), xhigh, max or auto, as far
                      as the model supports them. Low and medium are cheaper
                      but lose the fine ink grain the seal depends on.
  --concurrency N     Seals generated at the same time. Default 2; the skill
                      allows 2-3. Concurrency changes scheduling only, never
                      the model, quality or prompt.
  --redo              Regenerate seals that already exist.
  --dry-run           Print what would be generated and exit. No API call, no
                      key needed.

Example:
  python generate_seal.py ../seals/prompts/*.txt
  python generate_seal.py ../seals/prompts/IMG_4705.txt --quality high --redo
"""

from __future__ import annotations

import argparse
import base64
import io
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gpt-image-2"
SIZES = ("1024x1024", "1536x1024", "1024x1536")
QUALITIES = ("low", "medium", "high", "xhigh", "max", "auto")


def load_dotenv_values() -> dict[str, str]:
    """KEY=value lines from ./.env, then the skill's .env. No dependency on
    python-dotenv; quotes around a value are stripped."""
    values: dict[str, str] = {}
    for path in (SKILL_DIR / ".env", Path.cwd() / ".env"):     # cwd wins
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip("'\"")
    return values


def setting(name: str, env: dict[str, str], default: str | None = None) -> str | None:
    return os.environ.get(name) or env.get(name) or default


def seal_path(prompt: Path, seals_dir: Path | None) -> Path:
    if seals_dir is None:
        seals_dir = prompt.parent.parent if prompt.parent.name == "prompts" else prompt.parent
    return seals_dir / f"{prompt.stem}_seal.png"


def fmt_secs(s: float) -> str:
    s = int(s)
    return f"{s // 60}m{s % 60:02d}s"


def generate(client, model: str, prompt: str, size: str, quality: str) -> bytes:
    """One seal, as PNG bytes. The prompt asks for near-white paper around the
    impression; an opaque background keeps it that way for compose.py's
    knockout, rather than a transparent ground it was not tuned for."""
    resp = client.images.generate(
        model=model, prompt=prompt, size=size, quality=quality,
        n=1, background="opaque", output_format="png",
    )
    data = resp.data[0]
    if getattr(data, "b64_json", None):
        return base64.b64decode(data.b64_json)
    raise RuntimeError("the API returned no image data")


def check_png(raw: bytes) -> tuple[int, int]:
    from PIL import Image
    with Image.open(io.BytesIO(raw)) as im:
        im.verify()
    with Image.open(io.BytesIO(raw)) as im:
        return im.size


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("prompts", nargs="+", type=Path)
    ap.add_argument("--seals-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--size", choices=SIZES, default="1024x1024")
    ap.add_argument("--quality", choices=QUALITIES, default="high")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.out and len(a.prompts) != 1:
        ap.error("--out works with a single prompt file only")
    missing = [p for p in a.prompts if not p.is_file()]
    if missing:
        ap.error("prompt file not found: " + ", ".join(map(str, missing)))

    env = load_dotenv_values()
    model = a.model or setting("COLOPHON_IMAGE_MODEL", env, DEFAULT_MODEL)
    jobs, skipped = [], []
    for p in a.prompts:
        out = a.out or seal_path(p, a.seals_dir)
        if out.exists() and not a.redo:
            skipped.append(out)
            continue
        text = p.read_text().strip()
        if not text:
            ap.error(f"{p} is empty")
        jobs.append((p, out, text))

    print(f"{len(jobs)} seal(s) to generate with {model} ({a.size}, quality {a.quality}); "
          f"{len(skipped)} already exist" + (" (pass --redo to replace them)" if skipped else ""))
    for p, out, text in jobs:
        print(f"  {p}  ->  {out}  ({len(text.split())} words)")
    if a.dry_run or not jobs:
        return 0

    key = setting("OPENAI_API_KEY", env)
    if not key:
        print("No OPENAI_API_KEY. Put it in the environment, or in a .env file in this "
              "directory or the skill's directory:\n  OPENAI_API_KEY=sk-...", file=sys.stderr)
        return 2
    try:
        import openai
    except ImportError:
        print("The openai package is missing: pip install openai", file=sys.stderr)
        return 2
    client = openai.OpenAI(api_key=key, max_retries=3, timeout=300)

    lock = threading.Lock()
    t0 = time.time()
    done, failed = 0, []

    def one(job):
        p, out, text = job
        t = time.time()
        raw = generate(client, model, text, a.size, a.quality)
        w, h = check_png(raw)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
        return out, w, h, time.time() - t

    with ThreadPoolExecutor(max_workers=max(1, a.concurrency)) as ex:
        futs = {ex.submit(one, j): j for j in jobs}
        for f in as_completed(futs):
            p = futs[f][0]
            with lock:
                done += 1
                el = time.time() - t0
                eta = el / done * (len(jobs) - done)
                try:
                    out, w, h, took = f.result()
                    print(f"[{done}/{len(jobs)}] {fmt_secs(el)} elapsed, ETA {fmt_secs(eta)}  "
                          f"{out}  {w}x{h}  {took:.0f}s", flush=True)
                except Exception as e:      # keep the rest of the batch going
                    failed.append(p)
                    print(f"[{done}/{len(jobs)}] FAILED {p}: {e}", file=sys.stderr, flush=True)

    print(f"done in {fmt_secs(time.time() - t0)}: {len(jobs) - len(failed)} generated, "
          f"{len(failed)} failed")
    if failed:
        print("rerun to retry the failures; finished seals are skipped", file=sys.stderr)
    print("next: check_seal.py on each, then compose.py")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
