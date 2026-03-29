#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path

from common import (
    CONFIG_DIR,
    PUBLIC_REPORTS_DIR,
    REPORTS_DIR,
    load_yaml,
    today_string,
    truncate,
    write_json,
    write_text,
)
from last30days_bridge import generate_briefing, load_runtime


def _highlight_title(item: dict) -> str:
    return (
        item.get("source_title")
        or item.get("title")
        or item.get("content")
        or "Untitled finding"
    )


def _compact_snippet(item: dict) -> str:
    return truncate(item.get("summary") or item.get("content") or "", 220)


def _sort_findings(findings: list[dict]) -> list[dict]:
    return sorted(
        findings,
        key=lambda item: (
            float(item.get("engagement_score", 0) or 0),
            float(item.get("relevance_score", 0) or 0),
        ),
        reverse=True,
    )


def load_briefing(date_value: str | None = None, use_saved: bool = False) -> dict:
    runtime = load_runtime()
    return generate_briefing(runtime, date_value=date_value, use_saved=use_saved)


def build_report(date_value: str | None = None, use_saved: bool = False) -> dict:
    topics_cfg = load_yaml(CONFIG_DIR / "topics.yaml")
    sources_cfg = load_yaml(CONFIG_DIR / "sources.yaml")
    briefing = load_briefing(date_value=date_value, use_saved=use_saved)
    report_date = briefing.get("date") or date_value or today_string()

    topic_map = {topic["name"]: topic for topic in briefing.get("topics", [])}
    highlights_per_topic = topics_cfg.get("briefing", {}).get("max_highlights_per_topic", 3)

    levels = []
    for level_key, level_meta in topics_cfg.get("levels", {}).items():
        level_topics = []
        total_new = 0
        for configured_topic in topics_cfg.get("topics", []):
            if configured_topic["level"] != level_key:
                continue
            tracked = topic_map.get(configured_topic["name"], {})
            findings = _sort_findings(tracked.get("findings", []))[:highlights_per_topic]
            highlights = []
            for finding in findings:
                highlights.append(
                    {
                        "title": _highlight_title(finding),
                        "url": finding.get("source_url") or finding.get("url") or "",
                        "source": finding.get("source", "web"),
                        "author": finding.get("author") or "unknown",
                        "engagement": finding.get("engagement_score", 0),
                        "summary": _compact_snippet(finding),
                    }
                )
            total_new += tracked.get("new_count", 0) or 0
            level_topics.append(
                {
                    "id": configured_topic["id"],
                    "name": configured_topic["name"],
                    "level": configured_topic["level"],
                    "cadence": configured_topic.get("cadence", "daily"),
                    "focus": configured_topic.get("focus", ""),
                    "why_it_matters": configured_topic.get("why_it_matters", ""),
                    "new_count": tracked.get("new_count", 0) or 0,
                    "stale": bool(tracked.get("stale")),
                    "last_run": tracked.get("last_run"),
                    "last_status": tracked.get("last_status", "unknown"),
                    "highlights": highlights,
                }
            )

        curated_sources = []
        for source_set in sources_cfg.get("source_sets", []):
            if source_set.get("level") == level_key:
                curated_sources.extend(source_set.get("sources", []))

        levels.append(
            {
                "key": level_key,
                "label": level_meta.get("label", level_key),
                "display_name": level_meta.get("display_name", level_key),
                "description": level_meta.get("description", ""),
                "total_new": total_new,
                "topics": level_topics,
                "curated_sources": curated_sources,
            }
        )

    top_finding = briefing.get("top_finding") or {}
    if top_finding.get("title"):
        summary = f"今日最强信号来自 {top_finding.get('topic', 'unknown topic')}：{top_finding['title']}"
    else:
        summary = "今天还没有累计到足够的新发现，适合先看一级主题与高信号来源清单。"

    configured_total_new = sum(level["total_new"] for level in levels)
    configured_total_topics = len(topics_cfg.get("topics", []))

    report = {
        "date": report_date,
        "title": f"{topics_cfg['site']['title']} | {report_date}",
        "site_title": topics_cfg["site"]["title"],
        "subtitle": topics_cfg["site"]["subtitle"],
        "summary": summary,
        "intro_note": topics_cfg.get("briefing", {}).get("intro_note", ""),
        "total_new": configured_total_new,
        "total_topics": configured_total_topics,
        "cost": briefing.get("cost", {}),
        "levels": levels,
    }
    return report


def render_markdown(report: dict) -> str:
    lines = [
        f"# {report['site_title']}",
        "",
        f"Date: {report['date']}",
        "",
        report["summary"],
        "",
        report["intro_note"],
        "",
        f"Tracked topics: {report['total_topics']}",
        f"New findings in window: {report['total_new']}",
        f"Budget used: ${report['cost'].get('daily', 0):.2f} / ${report['cost'].get('budget', 0):.2f}",
        "",
    ]

    for level in report["levels"]:
        lines.extend(
            [
                f"## {level['display_name']}",
                "",
                level["description"],
                "",
                f"New findings: {level['total_new']}",
                "",
            ]
        )
        for topic in level["topics"]:
            lines.extend(
                [
                    f"### {topic['name']}",
                    "",
                    f"Why track it: {topic['why_it_matters']}",
                    f"Focus: {topic['focus']}",
                    f"Cadence: {topic['cadence']}",
                    f"New findings: {topic['new_count']}",
                    "",
                ]
            )
            if topic["highlights"]:
                for item in topic["highlights"]:
                    link = f"[{item['title']}]({item['url']})" if item["url"] else item["title"]
                    lines.extend(
                        [
                            f"- {link} | source: {item['source']} | author: {item['author']} | engagement: {item['engagement']}",
                            f"  {item['summary']}",
                        ]
                    )
            else:
                lines.append("- No new findings in the current window.")
            lines.append("")

        if level["curated_sources"]:
            lines.extend(
                [
                    "Curated sources for this level:",
                    "",
                ]
            )
            for source in level["curated_sources"]:
                lines.append(f"- [{source['name']}]({source['url']}) | {source['notes']}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def render_html(report: dict) -> str:
    sections = []
    for level in report["levels"]:
        topic_cards = []
        for topic in level["topics"]:
            if topic["highlights"]:
                highlight_items = []
                for item in topic["highlights"]:
                    title = escape(item["title"])
                    summary = escape(item["summary"])
                    meta = f"{escape(str(item['source']))} / {escape(str(item['author']))} / score {item['engagement']}"
                    if item["url"]:
                        heading = f'<a href="{escape(item["url"])}" target="_blank" rel="noreferrer">{title}</a>'
                    else:
                        heading = title
                    highlight_items.append(
                        f"""
                        <li class="finding">
                          <div class="finding-title">{heading}</div>
                          <div class="finding-meta">{meta}</div>
                          <p>{summary}</p>
                        </li>
                        """
                    )
                findings_html = "<ul class=\"finding-list\">" + "".join(highlight_items) + "</ul>"
            else:
                findings_html = "<p class=\"empty-state\">No new findings in the current window.</p>"

            topic_cards.append(
                f"""
                <article class="topic-card">
                  <div class="topic-head">
                    <h3>{escape(topic['name'])}</h3>
                    <span class="pill">{escape(topic['cadence'])}</span>
                  </div>
                  <p class="topic-why">{escape(topic['why_it_matters'])}</p>
                  <p class="topic-focus"><strong>Focus:</strong> {escape(topic['focus'])}</p>
                  <p class="topic-stats">New findings: {topic['new_count']}</p>
                  {findings_html}
                </article>
                """
            )

        curated = ""
        if level["curated_sources"]:
            curated_items = []
            for source in level["curated_sources"]:
                curated_items.append(
                    f"""
                    <li>
                      <a href="{escape(source['url'])}" target="_blank" rel="noreferrer">{escape(source['name'])}</a>
                      <span>{escape(source['notes'])}</span>
                    </li>
                    """
                )
            curated = (
                "<div class=\"source-box\"><h4>Curated sources</h4><ul class=\"source-list\">"
                + "".join(curated_items)
                + "</ul></div>"
            )

        sections.append(
            f"""
            <section class="level-section">
              <div class="level-head">
                <div>
                  <p class="eyebrow">{escape(level['label'])}</p>
                  <h2>{escape(level['display_name'])}</h2>
                </div>
                <div class="level-metric">{level['total_new']} new</div>
              </div>
              <p class="level-description">{escape(level['description'])}</p>
              <div class="topic-grid">
                {''.join(topic_cards)}
              </div>
              {curated}
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(report['title'])}</title>
  <style>
    :root {{
      --bg: #f4efe6;
      --paper: rgba(255, 251, 245, 0.92);
      --ink: #1f2933;
      --muted: #5c6b73;
      --line: rgba(31, 41, 51, 0.12);
      --accent: #0f766e;
      --accent-soft: rgba(15, 118, 110, 0.12);
      --warm: #8a5a44;
      --shadow: 0 18px 40px rgba(31, 41, 51, 0.12);
      --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      --sans: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 28rem),
        radial-gradient(circle at top right, rgba(138, 90, 68, 0.18), transparent 24rem),
        linear-gradient(180deg, #f8f2e8 0%, #f1ebe2 100%);
      font-family: var(--sans);
      line-height: 1.65;
    }}
    .shell {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 40px 20px 96px;
    }}
    .hero {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .hero h1 {{
      margin: 8px 0 12px;
      font-family: var(--serif);
      font-size: clamp(2rem, 5vw, 3.8rem);
      line-height: 1.05;
      letter-spacing: -0.04em;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      max-width: 72ch;
    }}
    .hero-grid {{
      display: grid;
      gap: 16px;
      margin-top: 24px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }}
    .hero-stat {{
      padding: 16px 18px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.75), rgba(255,255,255,0.45));
      border: 1px solid var(--line);
    }}
    .hero-stat strong {{
      display: block;
      font-size: 1.5rem;
      color: var(--accent);
    }}
    .eyebrow {{
      margin: 0;
      color: var(--warm);
      font-size: 0.8rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    .level-section {{
      margin-top: 28px;
      padding: 26px;
      border-radius: 26px;
      background: rgba(255, 251, 245, 0.82);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}
    .level-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: end;
    }}
    .level-head h2 {{
      margin: 6px 0 0;
      font-family: var(--serif);
      font-size: clamp(1.4rem, 3vw, 2.2rem);
    }}
    .level-description {{
      color: var(--muted);
      margin-top: 10px;
    }}
    .level-metric {{
      min-width: 92px;
      text-align: center;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 700;
      padding: 10px 14px;
    }}
    .topic-grid {{
      display: grid;
      gap: 18px;
      margin-top: 18px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }}
    .topic-card {{
      background: rgba(255,255,255,0.62);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
    }}
    .topic-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }}
    .topic-head h3 {{
      margin: 0;
      font-size: 1.1rem;
    }}
    .pill {{
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(31, 41, 51, 0.06);
      color: var(--muted);
      font-size: 0.82rem;
      white-space: nowrap;
    }}
    .topic-why,
    .topic-focus,
    .topic-stats {{
      margin: 12px 0 0;
      color: var(--muted);
    }}
    .finding-list,
    .source-list {{
      list-style: none;
      padding: 0;
      margin: 16px 0 0;
    }}
    .finding {{
      border-top: 1px solid var(--line);
      padding-top: 14px;
      margin-top: 14px;
    }}
    .finding:first-child {{
      border-top: 0;
      padding-top: 0;
      margin-top: 0;
    }}
    .finding-title a,
    .source-list a {{
      color: var(--ink);
      text-decoration: none;
      border-bottom: 1px solid rgba(15, 118, 110, 0.35);
    }}
    .finding-title a:hover,
    .source-list a:hover {{
      color: var(--accent);
    }}
    .finding-meta {{
      font-size: 0.84rem;
      color: var(--warm);
      margin-top: 4px;
    }}
    .empty-state {{
      color: var(--muted);
      font-style: italic;
      margin-top: 16px;
    }}
    .source-box {{
      margin-top: 20px;
      padding: 18px;
      border-radius: 20px;
      background: rgba(255,255,255,0.7);
      border: 1px solid var(--line);
    }}
    .source-box h4 {{
      margin: 0 0 12px;
    }}
    .source-list li {{
      display: grid;
      gap: 6px;
      padding: 10px 0;
      border-top: 1px solid var(--line);
    }}
    .source-list li:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    @media (max-width: 720px) {{
      .shell {{
        padding: 24px 14px 72px;
      }}
      .hero,
      .level-section {{
        padding: 20px;
        border-radius: 22px;
      }}
      .level-head {{
        flex-direction: column;
        align-items: start;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">{escape(report['site_title'])}</p>
      <h1>{escape(report['date'])} Briefing</h1>
      <p>{escape(report['summary'])}</p>
      <div class="hero-grid">
        <div class="hero-stat"><strong>{report['total_new']}</strong><span>new findings</span></div>
        <div class="hero-stat"><strong>{report['total_topics']}</strong><span>tracked topics</span></div>
        <div class="hero-stat"><strong>${report['cost'].get('daily', 0):.2f}</strong><span>budget used</span></div>
      </div>
    </section>
    {''.join(sections)}
  </main>
</body>
</html>
"""


def write_report(report: dict) -> dict:
    report_date = report["date"]
    markdown_path = REPORTS_DIR / f"{report_date}.md"
    html_path = PUBLIC_REPORTS_DIR / f"{report_date}.html"
    meta_path = REPORTS_DIR / f"{report_date}.report.json"

    markdown = render_markdown(report)
    html = render_html(report)

    metadata = {
        "date": report_date,
        "title": report["title"],
        "summary": report["summary"],
        "markdown_path": str(markdown_path.relative_to(REPORTS_DIR.parent)),
        "html_path": f"reports/{report_date}.html",
        "total_new": report["total_new"],
        "total_topics": report["total_topics"],
    }

    write_text(markdown_path, markdown)
    write_text(html_path, html)
    write_json(meta_path, metadata)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a repo-local briefing from last30days data.")
    parser.add_argument("--date", help="Use a saved briefing date in YYYY-MM-DD form.")
    parser.add_argument("--use-saved", action="store_true", help="Load a saved briefing instead of generating a fresh one.")
    args = parser.parse_args()

    report = build_report(date_value=args.date, use_saved=args.use_saved)
    metadata = write_report(report)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
