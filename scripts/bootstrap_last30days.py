#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from common import ROOT_DIR, find_skill_root


DEFAULT_REPO = "https://github.com/mvanhorn/last30days-skill.git"
DEFAULT_REF = "4d6224f"
VENDOR_ROOT = ROOT_DIR / ".vendor" / "last30days-skill"


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def _resolve_existing() -> Path | None:
    try:
        return find_skill_root()
    except SystemExit:
        return None


def ensure_skill_root(force_refresh: bool = False) -> Path:
    existing = _resolve_existing()
    if existing and not force_refresh:
        return existing

    repo_url = os.environ.get("LAST30DAYS_REPO", DEFAULT_REPO)
    ref = os.environ.get("LAST30DAYS_REF", DEFAULT_REF)

    if shutil.which("git") is None:
        raise SystemExit("git is required to bootstrap last30days-skill.")

    VENDOR_ROOT.parent.mkdir(parents=True, exist_ok=True)

    if VENDOR_ROOT.exists() and force_refresh:
        shutil.rmtree(VENDOR_ROOT)

    if not VENDOR_ROOT.exists():
        _run(["git", "clone", "--filter=blob:none", repo_url, str(VENDOR_ROOT)])

    if ref:
        _run(["git", "-C", str(VENDOR_ROOT), "fetch", "--all", "--tags"])
        _run(["git", "-C", str(VENDOR_ROOT), "checkout", ref])

    if not (VENDOR_ROOT / "scripts" / "last30days.py").exists():
        raise SystemExit(f"Bootstrapped skill is missing scripts/last30days.py: {VENDOR_ROOT}")

    return VENDOR_ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure a repo-local copy of last30days-skill exists.")
    parser.add_argument("--force-refresh", action="store_true", help="Re-clone the vendored copy.")
    parser.add_argument("--path-only", action="store_true", help="Print only the resolved skill root.")
    args = parser.parse_args()

    root = ensure_skill_root(force_refresh=args.force_refresh)
    if args.path_only:
        print(root)
    else:
        print(f"last30days root: {root}")


if __name__ == "__main__":
    main()
