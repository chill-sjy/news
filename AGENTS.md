# AGENTS

This repository is designed to be runnable both on a local machine and inside a Codex cloud task.

## Core idea

- `last30days` is the upstream research engine.
- This repo adds topic config, briefing assembly, static site generation, and RSS publishing.
- Cloud tasks must not rely on `~/.agents/skills/last30days`, because that path only exists on the local machine.

## Cloud bootstrap

Before running the pipeline in a fresh Codex environment:

```bash
./scripts/setup_cloud.sh
```

That script:

1. creates `.venv`
2. installs repo dependencies plus `yt-dlp`
3. clones `mvanhorn/last30days-skill` into `.vendor/last30days-skill`
4. checks out the pinned ref from `scripts/bootstrap_last30days.py`

## Cloud runner

After setup:

```bash
./scripts/run_pipeline_cloud.sh
```

Useful variants:

```bash
./scripts/run_pipeline_cloud.sh --skip-refresh
./scripts/run_pipeline_cloud.sh --levels L1,L2
./scripts/run_pipeline_cloud.sh --date 2026-03-29
```

## Data and outputs

- repo-local working state: `data/last30days/`
- markdown reports: `reports/`
- static site + RSS: `public/`

## Important limitation

Local secrets in `~/.config/last30days/.env` do not automatically exist inside a cloud task.

That means:

- local app runs can use your current X cookies
- cloud runs need equivalent env vars provided in the task environment if you want X there too
- without those env vars, the pipeline still runs, but source coverage is reduced
