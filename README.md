# AI Signal Briefing

This repository is a publishing layer around the locally installed `last30days` skill.

It keeps three things under version control:

- what we want to track
- how we turn raw findings into a readable report
- the static site and RSS feed that can be published with GitHub Pages

## Content model

The briefing is split into three levels:

- `L1`: your highest-signal topics, centered on agent systems and AI engineering
- `L2`: adjacent AI technical sources and implementation trends
- `L3`: broader AI industry and product news

`last30days` is used as the research engine for the tracked topics.
This repo adds the missing pieces: config, orchestration, rendering, and publishing.

## Repository layout

- [`config/topics.yaml`](/Users/sunjiyuan/project/research/news/config/topics.yaml): topic definitions, level mapping, cadence, and site settings
- [`config/sources.yaml`](/Users/sunjiyuan/project/research/news/config/sources.yaml): curated source inventory for future direct ingestion and manual review
- [`AGENTS.md`](/Users/sunjiyuan/project/research/news/AGENTS.md): Codex-oriented instructions for local and cloud tasks
- [`scripts/sync_watchlist.py`](/Users/sunjiyuan/project/research/news/scripts/sync_watchlist.py): sync repo config into a repo-local `last30days` watchlist
- [`scripts/run_pipeline.py`](/Users/sunjiyuan/project/research/news/scripts/run_pipeline.py): refresh due topics, build the daily report, and regenerate the site
- [`scripts/build_digest.py`](/Users/sunjiyuan/project/research/news/scripts/build_digest.py): turn `last30days` briefing data into Markdown, HTML, and report metadata
- [`scripts/render_feed.py`](/Users/sunjiyuan/project/research/news/scripts/render_feed.py): regenerate `public/index.html` and `public/feed.xml`
- [`scripts/last30days_bridge.py`](/Users/sunjiyuan/project/research/news/scripts/last30days_bridge.py): isolate upstream `last30days` state into `data/last30days/`
- [`scripts/bootstrap_last30days.py`](/Users/sunjiyuan/project/research/news/scripts/bootstrap_last30days.py): clone a repo-local copy of `last30days-skill` when the machine does not already have it
- [`scripts/setup_cloud.sh`](/Users/sunjiyuan/project/research/news/scripts/setup_cloud.sh): one-shot setup for a fresh Codex cloud environment
- [`scripts/run_pipeline_cloud.sh`](/Users/sunjiyuan/project/research/news/scripts/run_pipeline_cloud.sh): convenience wrapper for cloud/local automation runners
- [`public/`](/Users/sunjiyuan/project/research/news/public): static site output for GitHub Pages

## Assumptions

- The `last30days` skill is installed at `~/.agents/skills/last30days`
- This repo stores its own working state under `data/last30days/`, so it does not mix with any other `last30days` experiments you have run elsewhere
- We do not modify the upstream skill
- Scheduling logic lives in this repo, because upstream `watchlist.py run-all` ignores the stored cadence metadata and runs every enabled topic

## Setup

```bash
cd /Users/sunjiyuan/project/research/news
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

If you prefer not to use a virtual environment:

```bash
python3 -m pip install --user -r requirements.txt
```

## Current remote

This repo now points at:

`git@github.com:chill-sjy/news.git`

## First run

1. Sync the configured topics into the repo-local `last30days` dataset:

```bash
python3 scripts/sync_watchlist.py
```

2. Run the pipeline once without refreshing sources, just to build the site shell:

```bash
python3 scripts/run_pipeline.py --skip-refresh
```

3. Run a real refresh for the due topics:

```bash
python3 scripts/run_pipeline.py
```

## Publishing

The repo includes a GitHub Pages workflow at
[`deploy-pages.yml`](/Users/sunjiyuan/project/research/news/.github/workflows/deploy-pages.yml).

Once this repository is pushed to GitHub and Pages is enabled:

- `public/index.html` becomes the reading homepage
- `public/feed.xml` becomes the RSS feed you can subscribe to in Folo or Inoreader

Before that, update `site.base_url` in [`config/topics.yaml`](/Users/sunjiyuan/project/research/news/config/topics.yaml) from the placeholder value to your real Pages URL.

## Codex Automation / Cloud

If you want a Codex cloud task or automation to run this repo, there are two special needs:

1. cloud tasks do not have your local `~/.agents/skills/last30days`
2. cloud tasks do not automatically inherit your local `~/.config/last30days/.env`

To handle the first problem, this repo can now self-bootstrap a vendored upstream copy:

```bash
./scripts/setup_cloud.sh
```

Then run the pipeline with:

```bash
./scripts/run_pipeline_cloud.sh
```

This works well with Codex environments that let you define setup steps and internet access.

Recommended cloud setup step:

```bash
./scripts/setup_cloud.sh
```

Recommended automation runner command:

```bash
./scripts/run_pipeline_cloud.sh
```

For X-enabled cloud runs, you will still need equivalent `AUTH_TOKEN` / `CT0` env vars available in that environment. Local desktop runs can continue using your existing `~/.config/last30days/.env`.

## Notes on `last30days`

- The skill is best used here as a topic research engine, not as the final reader
- The repo-local watchlist database is persistent, so findings accumulate over time without polluting or being polluted by your other experiments
- The generated report in this repo is intentionally opinionated and grouped by your three levels
- `config/sources.yaml` is the source registry for future direct source ingestion; the first version of the pipeline uses it as context and curation, not as an automated crawler yet
- Upstream `watchlist.py` only converts a subset of source types into stored findings. In practice, missing X / YouTube auth or broad queries can lead to an empty briefing even if `last30days` found signals elsewhere. That is a real limitation we observed during this setup.
- The repo now supports a vendored `.vendor/last30days-skill` fallback, so cloud tasks can bootstrap the upstream skill instead of depending on your local home directory.
