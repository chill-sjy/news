#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from last30days_bridge import DATA_DIR, load_runtime, sync_topics as bridge_sync_topics


def sync_topics(prune: bool = False, dry_run: bool = False) -> dict:
    runtime = load_runtime()
    if dry_run:
        topics = runtime.topics_cfg.get("topics", [])
        return {
            "added_or_updated": [
                {
                    "name": topic["name"],
                    "level": topic["level"],
                    "cadence": topic.get("cadence", "daily"),
                    "query": topic["query"],
                }
                for topic in topics
            ],
            "removed": [],
            "configured_count": len(topics),
            "db_path": str(DATA_DIR / "research.db"),
            "dry_run": True,
        }
    return bridge_sync_topics(runtime, prune=prune)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync repo topics into last30days watchlist.")
    parser.add_argument("--prune", action="store_true", help="Remove watchlist topics not present in config.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing.")
    args = parser.parse_args()

    result = sync_topics(prune=args.prune, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
