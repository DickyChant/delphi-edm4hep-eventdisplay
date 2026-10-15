"""Build the manifest that the GitHub Pages viewer and editor read.

Scans docs/events/*.json (the figure JSON written by `delphi-display`) and writes
docs/events/index.json. The pages are static: publishing an event is committing its JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def build_index(docs: Path) -> dict:
    events = []
    for js in sorted((docs / "events").glob("*.json")):
        if js.name == "index.json" or js.name.endswith((".schema.json", ".3d.json", ".flow2d.json", ".flow3d.json")):
            continue  # sidecars of an event, not events of their own
        try:
            fig = json.loads(js.read_text())
        except json.JSONDecodeError:
            print(f"skipping {js.name}: not valid JSON", file=sys.stderr)
            continue
        meta = (fig.get("layout") or {}).get("meta") or {}
        title = meta.get("title") or ""
        if meta.get("run") is not None:
            label = f"run {meta['run']}, event {meta['event']}"
            title = f"{label} — {title}" if title else label
        events.append(
            {
                "key": js.stem,
                "file": f"events/{js.name}",
                "title": title or js.stem,
                "run": meta.get("run"),
                "event": meta.get("event"),
                "source": meta.get("source"),
                "entry": meta.get("entry"),
                "n_charged": meta.get("n_charged"),
                "n_neutral": meta.get("n_neutral"),
                "btag": meta.get("btag"),
                "note": meta.get("note"),
                "bytes": js.stat().st_size,
                "schema": f"events/{js.stem}.schema.json" if (docs / "events" / f"{js.stem}.schema.json").exists() else None,
                "figure3d": f"events/{js.stem}.3d.json" if (docs / "events" / f"{js.stem}.3d.json").exists() else None,
                "figureflow2d": f"events/{js.stem}.flow2d.json" if (docs / "events" / f"{js.stem}.flow2d.json").exists() else None,
                "figureflow3d": f"events/{js.stem}.flow3d.json" if (docs / "events" / f"{js.stem}.flow3d.json").exists() else None,
            }
        )
    return {"events": events}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="delphi-pages", description="rebuild docs/events/index.json from the published figure JSON")
    ap.add_argument("--docs", default="docs", help="docs directory (default: docs)")
    a = ap.parse_args(argv)
    docs = Path(a.docs)
    if not (docs / "events").is_dir():
        raise SystemExit(f"no {docs}/events directory")
    index = build_index(docs)
    out = docs / "events" / "index.json"
    out.write_text(json.dumps(index, indent=1))
    print(f"wrote {out}: {len(index['events'])} event(s)")
    for ev in index["events"]:
        print(f"  {ev['key']:32s} {ev['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
