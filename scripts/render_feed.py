#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from common import CONFIG_DIR, PUBLIC_DIR, REPORTS_DIR, load_yaml, write_text


def load_report_metadata() -> list[dict]:
    reports = []
    for path in sorted(REPORTS_DIR.glob("*.report.json"), reverse=True):
        with path.open("r", encoding="utf-8") as handle:
            reports.append(json.load(handle))
    return sorted(reports, key=lambda item: item["date"], reverse=True)


def render_feed(reports: list[dict], site_cfg: dict, max_items: int) -> str:
    base_url = site_cfg["site"]["base_url"].rstrip("/")
    title = site_cfg["site"]["title"]
    subtitle = site_cfg["site"]["subtitle"]
    generated_at = format_datetime(datetime.now(timezone.utc))

    items = []
    for report in reports[:max_items]:
        link = f"{base_url}/{report['html_path']}"
        pub_date = format_datetime(
            datetime.strptime(report["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        )
        items.append(
            f"""
    <item>
      <title>{xml_escape(report['title'])}</title>
      <link>{xml_escape(link)}</link>
      <guid>{xml_escape(link)}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{xml_escape(report['summary'])}</description>
    </item>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{xml_escape(title)}</title>
    <link>{xml_escape(base_url + '/')}</link>
    <description>{xml_escape(subtitle)}</description>
    <language>{xml_escape(site_cfg['site']['language'])}</language>
    <lastBuildDate>{generated_at}</lastBuildDate>
    {''.join(items)}
  </channel>
</rss>
"""


def render_index(reports: list[dict], site_cfg: dict) -> str:
    cards = []
    for report in reports:
        cards.append(
            f"""
            <article class="card">
              <p class="date">{escape(report['date'])}</p>
              <h2><a href="{escape(report['html_path'])}">{escape(report['title'])}</a></h2>
              <p>{escape(report['summary'])}</p>
              <div class="meta">
                <span>{report['total_new']} new findings</span>
                <span>{report['total_topics']} tracked topics</span>
              </div>
            </article>
            """
        )

    empty_state = (
        """
        <article class="card empty">
          <p class="date">No reports yet</p>
          <h2>Run the pipeline to publish the first briefing</h2>
          <p>Use `python3 scripts/run_pipeline.py --skip-refresh` to build the initial site shell, or run the full pipeline once your sources are ready.</p>
        </article>
        """
        if not cards
        else ""
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(site_cfg['site']['title'])}</title>
  <style>
    :root {{
      --bg: #efe9dc;
      --panel: rgba(255, 250, 243, 0.92);
      --ink: #1f2933;
      --muted: #5c6b73;
      --line: rgba(31, 41, 51, 0.12);
      --accent: #0f766e;
      --accent-soft: rgba(15, 118, 110, 0.12);
      --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      --sans: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.16), transparent 26rem),
        linear-gradient(180deg, #f6f0e7 0%, #efe7dc 100%);
      color: var(--ink);
      font-family: var(--sans);
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
      padding: 40px 18px 88px;
    }}
    .hero {{
      padding: 26px;
      border-radius: 28px;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: 0 18px 42px rgba(31, 41, 51, 0.12);
    }}
    .hero h1 {{
      margin: 10px 0;
      font-family: var(--serif);
      font-size: clamp(2rem, 6vw, 4rem);
      line-height: 1;
      letter-spacing: -0.04em;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      max-width: 60ch;
    }}
    .feed-link {{
      display: inline-flex;
      margin-top: 16px;
      padding: 10px 14px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      text-decoration: none;
      font-weight: 700;
    }}
    .cards {{
      display: grid;
      gap: 18px;
      margin-top: 24px;
    }}
    .card {{
      padding: 22px;
      border-radius: 22px;
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid var(--line);
      box-shadow: 0 14px 30px rgba(31, 41, 51, 0.08);
    }}
    .card h2 {{
      margin: 8px 0;
      font-size: 1.3rem;
    }}
    .card h2 a {{
      color: inherit;
      text-decoration: none;
      border-bottom: 1px solid rgba(15, 118, 110, 0.3);
    }}
    .card p {{
      margin: 0;
      color: var(--muted);
    }}
    .date {{
      color: var(--accent);
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 0.82rem;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    @media (max-width: 640px) {{
      main {{
        padding: 24px 14px 64px;
      }}
      .hero,
      .card {{
        padding: 18px;
        border-radius: 20px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <p>{escape(site_cfg['site']['subtitle'])}</p>
      <h1>{escape(site_cfg['site']['title'])}</h1>
      <p>Published from GitHub Pages friendly static files. Subscribe with Folo or Inoreader using the feed URL below.</p>
      <a class="feed-link" href="feed.xml">Open RSS feed</a>
    </section>
    <section class="cards">
      {empty_state}
      {''.join(cards)}
    </section>
  </main>
</body>
</html>
"""


def render_site() -> None:
    site_cfg = load_yaml(CONFIG_DIR / "topics.yaml")
    max_items = site_cfg.get("briefing", {}).get("max_reports_in_feed", 20)
    reports = load_report_metadata()

    write_text(PUBLIC_DIR / "feed.xml", render_feed(reports, site_cfg, max_items=max_items))
    write_text(PUBLIC_DIR / "index.html", render_index(reports, site_cfg))
    write_text(PUBLIC_DIR / ".nojekyll", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render public/index.html and public/feed.xml from report metadata.")
    parser.parse_args()
    render_site()


if __name__ == "__main__":
    main()
