#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bootstrap_last30days import ensure_skill_root
from common import CONFIG_DIR, ROOT_DIR, load_yaml


DATA_DIR = ROOT_DIR / "data" / "last30days"
DB_PATH = DATA_DIR / "research.db"
BRIEFS_DIR = DATA_DIR / "briefs"
OUTPUT_DIR = DATA_DIR / "out"

DAY_TO_CRON = {
    "monday": "1",
    "tuesday": "2",
    "wednesday": "3",
    "thursday": "4",
    "friday": "5",
    "saturday": "6",
    "sunday": "0",
}


@dataclass
class Last30DaysRuntime:
    topics_cfg: dict[str, Any]
    skill_root: Path
    watchlist_module: Any
    briefing_module: Any


def _load_module(module_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_schedule(topic: dict) -> str:
    cadence = topic.get("cadence", "daily")
    if cadence == "daily":
        return "0 8 * * *"
    if cadence == "weekdays":
        return "0 8 * * 1-5"
    if cadence == "weekly":
        day = (topic.get("day_of_week") or "monday").lower()
        return f"0 8 * * {DAY_TO_CRON.get(day, '1')}"
    raise SystemExit(f"Unsupported cadence in topics.yaml: {cadence}")


def load_runtime() -> Last30DaysRuntime:
    topics_cfg = load_yaml(CONFIG_DIR / "topics.yaml")
    skill_root = ensure_skill_root()
    scripts_dir = skill_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("LAST30DAYS_OUTPUT_DIR", str(OUTPUT_DIR))

    watchlist_module = _load_module("news_watchlist_local", scripts_dir / "watchlist.py")
    briefing_module = _load_module("news_briefing_local", scripts_dir / "briefing.py")

    for store_module in {watchlist_module.store, briefing_module.store}:
        store_module._db_override = DB_PATH
        store_module.init_db(DB_PATH)

    briefing_module.BRIEFS_DIR = BRIEFS_DIR

    return Last30DaysRuntime(
        topics_cfg=topics_cfg,
        skill_root=skill_root,
        watchlist_module=watchlist_module,
        briefing_module=briefing_module,
    )


def configured_topics(runtime: Last30DaysRuntime) -> list[dict]:
    return runtime.topics_cfg.get("topics", [])


def sync_topics(runtime: Last30DaysRuntime, prune: bool = False) -> dict:
    store = runtime.watchlist_module.store
    configured = configured_topics(runtime)
    expected_names = {topic["name"] for topic in configured}
    current_names = {topic["name"] for topic in store.list_topics()}

    added_or_updated = []
    removed = []
    for topic in configured:
        store.add_topic(
            topic["name"],
            search_queries=[topic["query"]],
            schedule=build_schedule(topic),
        )
        added_or_updated.append(
            {
                "name": topic["name"],
                "level": topic["level"],
                "cadence": topic.get("cadence", "daily"),
                "query": topic["query"],
            }
        )

    if prune:
        for extra_name in sorted(current_names - expected_names):
            store.remove_topic(extra_name)
            removed.append(extra_name)

    return {
        "added_or_updated": added_or_updated,
        "removed": removed,
        "configured_count": len(configured),
        "db_path": str(DB_PATH),
    }


def list_topics(runtime: Last30DaysRuntime) -> list[dict]:
    return runtime.watchlist_module.store.list_topics()


def run_topic(runtime: Last30DaysRuntime, topic_name: str) -> dict:
    topic = runtime.watchlist_module.store.get_topic(topic_name)
    if not topic:
        raise SystemExit(f"Topic not found in repo-local watchlist: {topic_name}")
    return runtime.watchlist_module._run_topic(topic)


def generate_briefing(runtime: Last30DaysRuntime, date_value: str | None = None, use_saved: bool = False) -> dict:
    if use_saved:
        return runtime.briefing_module.show_briefing(date_value)
    return runtime.briefing_module.generate_daily()
