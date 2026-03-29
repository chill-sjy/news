#!/usr/bin/env python3
"""Convert a saved last30days briefing JSON into repo content and HTML."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from html import escape
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
TOPICS_CONFIG = REPO_ROOT / "config" / "topics.yaml"
SOURCES_CONFIG = REPO_ROOT / "config" / "sources.yaml"
DEFAULT_BRIEFS_DIR = Path.home() / ".local" / "share" / "last30days" / "briefs"
CONTENT_DIR = REPO_ROOT / "content" / "reports"
PUBLIC_REPORTS_DIR = REPO_ROOT / "public" / "reports"


def load_yaml(path: Path) -> dict:
    with path.open() as handle:
        return yaml.safe_load(handle)


def load_briefing(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def build_topic_index(config: dict) -> dict[str, dict]:
    index = {}
    for tier in config.get("tiers", []):
        for topic in tier.get("topics", []):
            index[topic["name"]] = {
                "tier_id": tier["id"],
                "tier_name": tier["name"],
                "tier_description": tier.get("description", ""),
                "notes": topic.get("notes", ""),
                "slug": topic.get("slug", topic["name"].lower().replace(" ", "-")),
            }
    return index


def build_tier_sections(briefing: dict, topics_cfg: dict) -> list[dict]:
    topic_index = build_topic_index(topics_cfg)
    sections: list[dict] = []
    grouped: dict[str, list[dict]] = {}

    for topic in briefing.get("topics", []):
        meta = topic_index.get(
            topic["name"],
            {
                "tier_id": "unmapped",
                "tier_name": "未映射",
                "tier_description": "配置文件里还没定义这个主题。",
                "notes": "",
                "slug": topic["name"].lower().replace(" ", "-"),
            },
        )
        merged = {**meta, **topic}
        grouped.setdefault(meta["tier_id"], []).append(merged)

    for tier in topics_cfg.get("tiers", []):
        tier_topics = grouped.get(tier["id"], [])
        tier_topics.sort(key=lambda item: (item.get("new_count", 0), item.get("hours_ago") or 9999), reverse=True)
        sections.append(
            {
                "id": tier["id"],
                "name": tier["name"],
                "description": tier.get("description", ""),
                "topics": tier_topics,
            }
        )
    return sections


def load_source_sections() -> list[dict]:
    config = load_yaml(SOURCES_CONFIG)
    return config.get("tiers", [])


def compute_summary(briefing: dict) -> str:
    top = briefing.get("top_finding")
    if not top:
        return "今天还没有足够强的信号，建议先刷新 watchlist 再生成日报。"
    return f"今日最高信号落在 {top.get('topic', '未分类主题')}：{top.get('title', '暂无标题')}。"


def topic_freshness(topic: dict) -> str:
    if topic.get("stale"):
        return f"数据偏旧，上次运行约 {topic.get('hours_ago', '?')} 小时前。"
    if topic.get("hours_ago") is None:
        return "还没有成功运行记录。"
    return f"数据新鲜，上次运行约 {topic['hours_ago']} 小时前。"


def render_markdown(report: dict) -> str:
    lines = [
        "---",
        f"title: {report['title']}",
        f"date: {report['date']}",
        f"summary: {report['summary']}",
        f"slug: {report['slug']}",
        "---",
        "",
        f"# {report['title']}",
        "",
        report["summary"],
        "",
        "## TL;DR",
        "",
        report["summary"],
        "",
    ]

    for section in report["sections"]:
        lines.extend([f"## {section['name']}", "", section["description"], ""])
        if not section["topics"]:
            lines.extend(["- 今天没有拿到这一级别的新结果。", ""])
            continue
        for topic in section["topics"]:
            lines.extend([f"### {topic['name']}", ""])
            lines.append(f"- 新发现：{topic.get('new_count', 0)}")
            lines.append(f"- 新鲜度：{topic_freshness(topic)}")
            if topic.get("top_finding"):
                top = topic["top_finding"]
                lines.append(f"- Top signal：{top.get('title', '暂无标题')} ({top.get('source', 'unknown')})")
                if top.get("content"):
                    lines.append(f"- 线索摘要：{top['content']}")
            if topic.get("notes"):
                lines.append(f"- 跟踪意图：{topic['notes']}")
            lines.append("")

    lines.extend(["## Source backlog", ""])
    for source_tier in report["source_sections"]:
        lines.append(f"### {source_tier['name']}")
        lines.append("")
        for source in source_tier.get("sources", []):
            lines.append(f"- [{source['name']}]({source['url']}) | {source['kind']} | {source['notes']}")
        lines.append("")

    lines.extend(
        [
            "## Stats",
            "",
            f"- topics：{report['stats']['total_topics']}",
            f"- new findings：{report['stats']['total_new']}",
            f"- daily cost：${report['stats']['cost_daily']:.2f} / ${report['stats']['cost_budget']:.2f}",
            "",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_html(report: dict) -> str:
    tier_cards = []
    accent = {"l1": "#0f766e", "l2": "#1d4ed8", "l3": "#b45309"}
    for section in report["sections"]:
        items = []
        if not section["topics"]:
            items.append('<li class="empty">今天没有拿到这一级别的新结果。</li>')
        for topic in section["topics"]:
            bullets = [
                f"<li><strong>新发现：</strong>{topic.get('new_count', 0)}</li>",
                f"<li><strong>新鲜度：</strong>{escape(topic_freshness(topic))}</li>",
            ]
            if topic.get("top_finding"):
                top = topic["top_finding"]
                bullets.append(
                    "<li><strong>Top signal：</strong>"
                    f"{escape(top.get('title', '暂无标题'))} "
                    f"<span class=\"source-pill\">{escape(top.get('source', 'unknown'))}</span></li>"
                )
                if top.get("content"):
                    bullets.append(f"<li><strong>线索摘要：</strong>{escape(top['content'])}</li>")
            if topic.get("notes"):
                bullets.append(f"<li><strong>跟踪意图：</strong>{escape(topic['notes'])}</li>")
            items.append(
                f"""
                <article class="topic-card">
                  <h3>{escape(topic['name'])}</h3>
                  <ul>{''.join(bullets)}</ul>
                </article>
                """
            )

        tier_cards.append(
            f"""
            <section class="tier-card" style="--tier-accent:{accent.get(section['id'], '#475569')}">
              <div class="tier-header">
                <p class="tier-label">{escape(section['id'].upper())}</p>
                <h2>{escape(section['name'])}</h2>
                <p>{escape(section['description'])}</p>
              </div>
              <div class="topic-grid">
                {''.join(items)}
              </div>
            </section>
            """
        )

    source_blocks = []
    for source_tier in report["source_sections"]:
        source_items = []
        for source in source_tier.get("sources", []):
            source_items.append(
                f"""
                <li>
                  <a href="{escape(source['url'])}">{escape(source['name'])}</a>
                  <span>{escape(source['kind'])}</span>
                  <p>{escape(source['notes'])}</p>
                </li>
                """
            )
        source_blocks.append(
            f"""
            <section class="source-card">
              <h2>{escape(source_tier['name'])}</h2>
              <ul>{''.join(source_items)}</ul>
            </section>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(report['title'])}</title>
  <meta name="description" content="{escape(report['summary'])}" />
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f2e8;
      --panel: rgba(255, 255, 255, 0.78);
      --text: #0f172a;
      --muted: #475569;
      --border: rgba(15, 23, 42, 0.08);
      --shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
      font-family: "IBM Plex Sans", "Avenir Next", "PingFang SC", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(13, 148, 136, 0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(29, 78, 216, 0.16), transparent 30%),
        linear-gradient(180deg, #f8f5ef 0%, var(--bg) 100%);
    }}
    a {{ color: inherit; }}
    .shell {{
      width: min(1100px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 32px 0 64px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.72));
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }}
    .eyebrow {{
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #0f766e;
      font-weight: 700;
      font-size: 12px;
      margin: 0 0 12px;
    }}
    h1 {{
      font-family: Charter, "Iowan Old Style", "Songti SC", serif;
      font-size: clamp(32px, 5vw, 56px);
      line-height: 1.02;
      margin: 0 0 12px;
    }}
    .summary {{
      font-size: 18px;
      color: var(--muted);
      margin: 0;
      max-width: 780px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 20px;
    }}
    .stat {{
      border-radius: 20px;
      background: rgba(255,255,255,0.82);
      border: 1px solid var(--border);
      padding: 14px 16px;
    }}
    .stat strong {{
      display: block;
      font-size: 24px;
      margin-bottom: 4px;
    }}
    .grid {{
      display: grid;
      gap: 18px;
      margin-top: 22px;
    }}
    .tier-card, .source-card {{
      border: 1px solid var(--border);
      border-radius: 26px;
      background: var(--panel);
      box-shadow: var(--shadow);
      padding: 22px;
      backdrop-filter: blur(14px);
    }}
    .tier-header {{
      border-left: 6px solid var(--tier-accent);
      padding-left: 14px;
      margin-bottom: 18px;
    }}
    .tier-label {{
      color: var(--tier-accent);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.12em;
      margin: 0 0 8px;
    }}
    .tier-header h2, .source-card h2 {{
      margin: 0 0 6px;
      font-size: 26px;
    }}
    .tier-header p, .source-card p {{
      margin: 0;
      color: var(--muted);
    }}
    .topic-grid {{
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    }}
    .topic-card {{
      background: rgba(255,255,255,0.92);
      border-radius: 20px;
      border: 1px solid var(--border);
      padding: 16px;
    }}
    .topic-card h3 {{
      margin: 0 0 10px;
      font-size: 20px;
    }}
    .topic-card ul, .source-card ul {{
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
    }}
    .topic-card li, .source-card li {{
      margin-bottom: 8px;
      line-height: 1.5;
    }}
    .source-pill {{
      display: inline-block;
      margin-left: 6px;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.08);
      font-size: 12px;
      color: var(--muted);
    }}
    .empty {{
      color: var(--muted);
      list-style: none;
      padding-left: 0;
    }}
    @media (max-width: 720px) {{
      .shell {{ width: min(100vw - 20px, 1100px); padding-top: 20px; }}
      .hero, .tier-card, .source-card {{ border-radius: 22px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">AI Signal Daily</p>
      <h1>{escape(report['title'])}</h1>
      <p class="summary">{escape(report['summary'])}</p>
      <div class="stats">
        <div class="stat"><strong>{report['stats']['total_topics']}</strong><span>topics tracked</span></div>
        <div class="stat"><strong>{report['stats']['total_new']}</strong><span>new findings</span></div>
        <div class="stat"><strong>${report['stats']['cost_daily']:.2f}</strong><span>daily cost</span></div>
      </div>
    </section>
    <section class="grid">
      {''.join(tier_cards)}
      {''.join(source_blocks)}
    </section>
  </main>
</body>
</html>
"""


def write_outputs(report: dict) -> tuple[Path, Path, Path]:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    md_path = CONTENT_DIR / f"{report['slug']}.md"
    json_path = CONTENT_DIR / f"{report['slug']}.json"
    html_path = PUBLIC_REPORTS_DIR / f"{report['slug']}.html"

    md_path.write_text(render_markdown(report))
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    html_path.write_text(render_html(report))
    return md_path, json_path, html_path


def resolve_input_path(args: argparse.Namespace) -> Path:
    if args.input:
        return args.input
    if args.date:
        return DEFAULT_BRIEFS_DIR / f"{args.date}.json"
    today = datetime.now().strftime("%Y-%m-%d")
    return DEFAULT_BRIEFS_DIR / f"{today}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a saved last30days briefing into repo files")
    parser.add_argument("--input", type=Path, help="Path to a briefing JSON file")
    parser.add_argument("--date", help="Date of briefing to load from ~/.local/share/last30days/briefs")
    parser.add_argument("--title", help="Optional custom report title")
    args = parser.parse_args()

    input_path = resolve_input_path(args)
    if not input_path.exists():
        raise SystemExit(f"Briefing file not found: {input_path}")

    topics_cfg = load_yaml(TOPICS_CONFIG)
    briefing = load_briefing(input_path)
    report_date = briefing.get("date") or args.date or datetime.now().strftime("%Y-%m-%d")
    title = args.title or f"{report_date} AI Signal Daily"

    report = {
        "title": title,
        "date": report_date,
        "slug": report_date,
        "summary": compute_summary(briefing),
        "sections": build_tier_sections(briefing, topics_cfg),
        "source_sections": load_source_sections(),
        "stats": {
            "total_topics": briefing.get("total_topics", 0),
            "total_new": briefing.get("total_new", 0),
            "cost_daily": float(briefing.get("cost", {}).get("daily", 0.0)),
            "cost_budget": float(briefing.get("cost", {}).get("budget", 0.0)),
        },
        "raw_briefing_path": str(input_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    md_path, json_path, html_path = write_outputs(report)
    print(f"Markdown: {md_path}")
    print(f"Metadata: {json_path}")
    print(f"HTML: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

