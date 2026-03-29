#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
REPORTS_DIR = ROOT_DIR / "reports"
PUBLIC_DIR = ROOT_DIR / "public"
PUBLIC_REPORTS_DIR = PUBLIC_DIR / "reports"


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit(
            "PyYAML is required. Install it with `python3 -m pip install -r requirements.txt`."
        ) from exc

    if not path.exists():
        raise SystemExit(f"Missing config file: {path}")

    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def truncate(text: str, limit: int = 180) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def run_command(args: Iterable[str], timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Command returned empty output.")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end < 0:
            raise
        return json.loads(cleaned[start : end + 1])


def run_json(args: Iterable[str], timeout: int = 300) -> dict[str, Any]:
    result = run_command(args, timeout=timeout)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or f"Command failed: {' '.join(args)}")
    try:
        return _extract_json_payload(result.stdout)
    except Exception as exc:
        raise SystemExit(
            "Failed to parse JSON output from command:\n"
            f"{' '.join(args)}\n\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        ) from exc


def find_skill_root() -> Path:
    candidates = [
        Path((__import__("os").environ.get("LAST30DAYS_ROOT") or "")).expanduser() if __import__("os").environ.get("LAST30DAYS_ROOT") else None,
        Path.cwd(),
        ROOT_DIR / ".vendor" / "last30days-skill",
        Path.home() / ".agents" / "skills" / "last30days",
        Path.home() / ".codex" / "skills" / "last30days",
        Path.home() / ".claude" / "skills" / "last30days",
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        if (candidate / "scripts" / "last30days.py").exists():
            return candidate
    raise SystemExit("Could not find the local last30days skill installation.")


def today_string() -> str:
    return date.today().isoformat()


def parse_iso_date(value: str | None) -> date:
    return datetime.strptime(value or today_string(), "%Y-%m-%d").date()
