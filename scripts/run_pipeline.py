#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date

from build_digest import build_report, write_report
from common import parse_iso_date
from last30days_bridge import configured_topics, load_runtime, run_topic
from render_feed import render_site
from sync_watchlist import sync_topics

WEEKDAY_NAMES = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}


def topic_is_due(topic: dict, target_date: date) -> bool:
    cadence = topic.get("cadence", "daily")
    weekday_name = WEEKDAY_NAMES[target_date.weekday()]

    if cadence == "daily":
        return True
    if cadence == "weekdays":
        return target_date.weekday() < 5
    if cadence == "weekly":
        return weekday_name == (topic.get("day_of_week") or "monday").lower()
    return False


def refresh_due_topics(target_date: date, levels: set[str] | None = None) -> list[dict]:
    runtime = load_runtime()
    results = []

    for topic in configured_topics(runtime):
        if levels and topic["level"] not in levels:
            continue
        if not topic_is_due(topic, target_date):
            results.append({"topic": topic["name"], "status": "skipped", "reason": "not_due"})
            continue
        results.append(run_topic(runtime, topic["name"]))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local research and publishing pipeline.")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD form.")
    parser.add_argument("--levels", help="Comma-separated level filter, for example L1,L2.")
    parser.add_argument("--skip-sync", action="store_true", help="Do not sync config into the last30days watchlist.")
    parser.add_argument("--skip-refresh", action="store_true", help="Do not run any last30days topic refresh before building the report.")
    parser.add_argument("--prune", action="store_true", help="Remove watchlist topics missing from config during sync.")
    args = parser.parse_args()

    target_date = parse_iso_date(args.date)
    level_filter = set(part.strip() for part in args.levels.split(",")) if args.levels else None

    summary = {}
    if not args.skip_sync:
        summary["sync"] = sync_topics(prune=args.prune)
    if not args.skip_refresh:
        summary["refresh"] = refresh_due_topics(target_date, levels=level_filter)

    report = build_report(date_value=target_date.isoformat(), use_saved=False)
    summary["report"] = write_report(report)
    render_site()

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
