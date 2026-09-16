"""Demo / proof trigger — research a few apps live and print structured rows."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.run_research import load_apps, process_one  # noqa: E402

console = Console()


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Live proof: research a few apps end-to-end")
    parser.add_argument("--ids", default="2,61,71,81", help="Comma-separated app ids")
    parser.add_argument("--out", default=str(ROOT / "output" / "demo_run.json"))
    args = parser.parse_args()

    want = {int(x.strip()) for x in args.ids.split(",") if x.strip()}
    apps = [a for a in load_apps() if a.id in want]
    results = []
    for seed in apps:
        console.print(f"[bold]Researching[/bold] {seed.id} {seed.name}...")
        r = process_one(seed)
        results.append(r)
        console.print(
            f"  auth={r.auth_methods} access={r.access_model} "
            f"build={r.buildability} conf={r.confidence:.2f}"
        )

    Path(args.out).write_text(
        json.dumps({"results": [r.model_dump() for r in results]}, indent=2)
    )

    table = Table(title="Demo research results")
    table.add_column("ID")
    table.add_column("App")
    table.add_column("Auth")
    table.add_column("Access")
    table.add_column("Verdict")
    table.add_column("Evidence")
    for r in results:
        table.add_row(
            str(r.id),
            r.name,
            ", ".join(r.auth_methods),
            r.access_model,
            r.buildability,
            (r.evidence_urls[0] if r.evidence_urls else "—")[:48],
        )
    console.print(table)
    console.print(f"[green]Saved {args.out}[/green]")


if __name__ == "__main__":
    main()
