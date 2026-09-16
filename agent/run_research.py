"""Run toolkit research across the 100-app set."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.fetch_docs import fetch_docs_for_app  # noqa: E402
from agent.researcher import maybe_composio_context, research_app  # noqa: E402
from agent.schema import AppSeed, ResearchResult  # noqa: E402

console = Console()


def load_apps() -> list[AppSeed]:
    raw = json.loads((ROOT / "data" / "apps.json").read_text())
    return [AppSeed(**a) for a in raw]


def load_existing(path: Path) -> dict[int, dict]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {int(r["id"]): r for r in data.get("results", [])}


def save_results(path: Path, results: list[ResearchResult], meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": meta,
        "results": [r.model_dump() for r in sorted(results, key=lambda x: x.id)],
    }
    path.write_text(json.dumps(payload, indent=2))


def process_one(seed: AppSeed) -> ResearchResult:
    docs = fetch_docs_for_app(seed.name, seed.hint)
    result = research_app(seed, docs=docs)
    composio_note = maybe_composio_context(seed)
    if composio_note:
        result.raw_notes = (result.raw_notes + " | " + composio_note).strip(" |")
    return result


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Research agent for Composio toolkit readiness")
    parser.add_argument("--ids", type=str, default="", help="Comma-separated app ids, e.g. 1,2,61")
    parser.add_argument("--limit", type=int, default=0, help="Only first N apps")
    parser.add_argument("--concurrency", type=int, default=int(os.getenv("MAX_CONCURRENCY", "4")))
    parser.add_argument("--out", type=str, default=str(ROOT / "output" / "results_pass1.json"))
    parser.add_argument("--resume", action="store_true", help="Skip ids already in output")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        console.print("[red]OPENAI_API_KEY missing in .env[/red]")
        sys.exit(1)

    apps = load_apps()
    if args.ids:
        want = {int(x.strip()) for x in args.ids.split(",") if x.strip()}
        apps = [a for a in apps if a.id in want]
    if args.limit:
        apps = apps[: args.limit]

    out_path = Path(args.out)
    existing = load_existing(out_path) if args.resume else {}
    todo = [a for a in apps if a.id not in existing]
    done: list[ResearchResult] = [ResearchResult(**v) for v in existing.values()]

    console.print(f"[bold]Researching {len(todo)} apps[/bold] (skipping {len(apps) - len(todo)}) → {out_path}")
    meta = {
        "pass": "pass1",
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "composio_enabled": bool(os.getenv("COMPOSIO_API_KEY")),
    }

    errors: list[str] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("apps", total=len(todo))
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
            futures = {pool.submit(process_one, seed): seed for seed in todo}
            for fut in as_completed(futures):
                seed = futures[fut]
                try:
                    result = fut.result()
                    done.append(result)
                    save_results(out_path, done, meta)
                    progress.console.print(
                        f"  [{result.id:03d}] {result.name}: {result.buildability} "
                        f"(conf={result.confidence:.2f})"
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{seed.id} {seed.name}: {exc}")
                    progress.console.print(f"  [red]FAIL[/red] {seed.name}: {exc}")
                progress.advance(task)

    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    meta["errors"] = errors
    save_results(out_path, done, meta)
    console.print(f"[green]Saved {len(done)} rows → {out_path}[/green]")
    if errors:
        console.print(f"[yellow]{len(errors)} errors[/yellow]")


if __name__ == "__main__":
    main()
