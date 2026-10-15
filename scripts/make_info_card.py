#!/usr/bin/env python3
"""
Generate a Neofetch-inspired GitHub statistics dashboard SVG (assets/info-card.svg)
derived from data/contributions.json.

Features:
- Terminal window title bar matching profile theme
- Contribution metrics: Current Streak, Longest Streak, Total Contributions, Active Days,
  Average per Active Day, and Best Contribution Day
- Monthly contribution bar chart with GitHub-green bars
- Compact Account Activity section with 6 cards (2 rows of 3):
  1. Commits (365d)
  2. Public Repositories
  3. Stars Earned
  4. Pull Requests (including Merged PR status)
  5. Code Reviews
  6. Issues
- Subtle entrance fade-in animations with backwards fill (degrades to static cleanly)
- Self-contained SVG, valid XML, zero external runtime dependencies
"""
import datetime
import json
import os
import xml.sax.saxutils as saxutils

HERE = os.path.dirname(__file__)
IN_PATH = os.path.join(HERE, "..", "data", "contributions.json")
OUT_PATH = os.path.join(HERE, "..", "assets", "info-card.svg")

# Dimensions
CARD_WIDTH = 440
CARD_HEIGHT = 420
TITLEBAR_H = 32
PAD = 16

# Theme Colors
BG_COLOR = "#0d1117"
BG_GRAD_TOP = "#161b22"
BORDER_COLOR = "#30363d"
PANEL_BG = "#161b22"
PANEL_BORDER = "#21262d"
MUTED = "#8b949e"
TEXT_PRIMARY = "#f0f6fc"
TEXT_SECONDARY = "#c9d1d9"
ACCENT_GREEN = "#39d353"
ACCENT_CYAN = "#22d3ee"
ACCENT_GOLD = "#f2cc60"
ACCENT_PURPLE = "#bc8cff"
ACCENT_AMBER = "#f0883e"
BAR_EMPTY = "#21262d"


def render_info_card(data, out_path=OUT_PATH):
    username = data.get("username", "ayushcmdx")
    total_contribs = data.get("total_contributions", 0)
    active_days = data.get("active_days", 0)
    avg_day = data.get("avg_per_active_day", 0.0)

    cur_streak = data.get("current_streak", {})
    cur_len = cur_streak.get("length", 0)
    cur_range = f"{cur_streak.get('start', '')} → {cur_streak.get('end', '')}" if cur_len else "No active streak"

    long_streak = data.get("longest_streak", {})
    long_len = long_streak.get("length", 0)
    long_range = f"{long_streak.get('start', '')} → {long_streak.get('end', '')}" if long_len else "N/A"

    best_day = data.get("best_day", {})
    best_count = best_day.get("count", 0)
    best_date = best_day.get("date", "N/A")

    monthly = data.get("monthly", [])
    recent_months = monthly[-12:] if len(monthly) >= 12 else monthly

    # GitHub account metrics
    gh_stats = data.get("github_stats", {})
    commits_val = gh_stats.get("commits_365d")
    repos_val = gh_stats.get("public_repos")
    stars_val = gh_stats.get("total_stars")
    prs_val = gh_stats.get("total_prs")
    merged_val = gh_stats.get("merged_prs")
    reviews_val = gh_stats.get("code_reviews")
    issues_val = gh_stats.get("total_issues")

    # Format PR subtext
    if prs_val is not None and merged_val is not None:
        pr_sub = f"{merged_val} Merged" if merged_val == prs_val else f"{merged_val}/{prs_val} Merged"
    elif merged_val is not None:
        pr_sub = f"{merged_val} Merged"
    else:
        pr_sub = "Authored PRs"

    css = """
  .fade-in { animation: fadeIn 0.5s ease-out backwards; }
  .bar-grow { animation: barGrow 0.6s ease-out backwards; transform-origin: bottom; }
  @keyframes fadeIn {
    0% { opacity: 0; transform: translateY(4px); }
    100% { opacity: 1; transform: translateY(0); }
  }
  @keyframes barGrow {
    0% { transform: scaleY(0.1); opacity: 0.3; }
    100% { transform: scaleY(1); opacity: 1; }
  }
  @media (prefers-reduced-motion: reduce) {
    .fade-in, .bar-grow { animation: none !important; opacity: 1 !important; transform: none !important; }
  }
""".strip()

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
        f'viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, \'Liberation Mono\', monospace">',
        f'<style>{css}</style>',
        '<defs>',
        f'  <linearGradient id="cardGrad" x1="0" y1="0" x2="0" y2="1">',
        f'    <stop offset="0%" stop-color="{BG_GRAD_TOP}"/>',
        f'    <stop offset="100%" stop-color="{BG_COLOR}"/>',
        '  </linearGradient>',
        f'  <linearGradient id="barGrad" x1="0" y1="1" x2="0" y2="0">',
        f'    <stop offset="0%" stop-color="#26a641"/>',
        f'    <stop offset="100%" stop-color="#39d353"/>',
        '  </linearGradient>',
        '</defs>',
        f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="10" fill="url(#cardGrad)"/>',
        f'<rect x="0.5" y="0.5" width="{CARD_WIDTH-1}" height="{CARD_HEIGHT-1}" rx="10" '
        f'fill="none" stroke="{BORDER_COLOR}" stroke-width="1"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{CARD_WIDTH}" y2="{TITLEBAR_H}" stroke="{PANEL_BORDER}" stroke-width="1"/>',
    ]

    # Terminal buttons
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*14}" cy="{TITLEBAR_H/2}" r="4.5" fill="{color}"/>')

    # Window title
    parts.append(
        f'<text x="{CARD_WIDTH/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="11" font-weight="500" '
        f'text-anchor="middle">{username}@github: ~/neofetch --stats</text>'
    )

    # 4 Metric Cards in 2x2 Grid (Top Section)
    grid_y = TITLEBAR_H + 8
    col_w = (CARD_WIDTH - (PAD * 2) - 8) / 2
    row_h = 48

    top_metrics = [
        {
            "label": "CURRENT STREAK",
            "val": f"{cur_len} DAYS",
            "sub": cur_range,
            "val_color": ACCENT_CYAN,
            "delay": 0.05,
        },
        {
            "label": "LONGEST STREAK",
            "val": f"{long_len} DAYS",
            "sub": long_range,
            "val_color": ACCENT_PURPLE,
            "delay": 0.09,
        },
        {
            "label": "TOTAL CONTRIBUTIONS",
            "val": f"{total_contribs:,}",
            "sub": "Last 365 Days",
            "val_color": ACCENT_GREEN,
            "delay": 0.13,
        },
        {
            "label": "ACTIVE CONTRIBUTION DAYS",
            "val": f"{active_days} DAYS",
            "sub": f"Avg {avg_day} / active day",
            "val_color": ACCENT_GOLD,
            "delay": 0.17,
        },
    ]

    for idx, m in enumerate(top_metrics):
        r = idx // 2
        c = idx % 2
        mx = PAD + c * (col_w + 8)
        my = grid_y + r * (row_h + 6)

        parts.append(
            f'<g class="fade-in" style="animation-delay: {m["delay"]}s;">'
            f'<rect x="{mx}" y="{my}" width="{col_w}" height="{row_h}" rx="5" '
            f'fill="{PANEL_BG}" stroke="{PANEL_BORDER}" stroke-width="1"/>'
            f'<text x="{mx + 8}" y="{my + 13}" fill="{MUTED}" font-size="8" font-weight="600" letter-spacing="0.5">{m["label"]}</text>'
            f'<text x="{mx + 8}" y="{my + 30}" fill="{m["val_color"]}" font-size="13.5" font-weight="700">{m["val"]}</text>'
            f'<text x="{mx + 8}" y="{my + 42}" fill="{MUTED}" font-size="7.5">{m["sub"]}</text>'
            f'</g>'
        )

    # Best Contribution Day Bar
    best_y = grid_y + 2 * (row_h + 6)
    best_w = CARD_WIDTH - (PAD * 2)
    parts.append(
        f'<g class="fade-in" style="animation-delay: 0.21s;">'
        f'<rect x="{PAD}" y="{best_y}" width="{best_w}" height="24" rx="5" '
        f'fill="{PANEL_BG}" stroke="{PANEL_BORDER}" stroke-width="1"/>'
        f'<text x="{PAD + 8}" y="{best_y + 16}" fill="{MUTED}" font-size="8.5" font-weight="600">'
        f'BEST DAY: <tspan fill="{ACCENT_GOLD}" font-weight="700">{best_count} contributions</tspan>'
        f'<tspan fill="{MUTED}"> on {best_date}</tspan>'
        f'</text>'
        f'</g>'
    )

    # Monthly Contribution Chart Section
    chart_y = best_y + 32
    chart_w = CARD_WIDTH - (PAD * 2)

    parts.append(
        f'<g class="fade-in" style="animation-delay: 0.25s;">'
        f'<text x="{PAD}" y="{chart_y}" fill="{MUTED}" font-size="8" font-weight="600" letter-spacing="0.5">'
        f'MONTHLY CONTRIBUTION ACTIVITY'
        f'</text>'
        f'<line x1="{PAD}" y1="{chart_y + 4}" x2="{CARD_WIDTH - PAD}" y2="{chart_y + 4}" stroke="{PANEL_BORDER}" stroke-width="1"/>'
        f'</g>'
    )

    # Chart bars
    max_month_val = max([m["total"] for m in recent_months] + [1])
    bar_area_y = chart_y + 7
    max_bar_h = 36
    n_bars = len(recent_months)
    slot_w = chart_w / n_bars
    bar_w = max(slot_w - 6, 8)

    for i, m in enumerate(recent_months):
        bx = PAD + i * slot_w + (slot_w - bar_w) / 2
        ratio = m["total"] / max_month_val
        bh = max(int(ratio * max_bar_h), 4) if m["total"] > 0 else 3
        by = bar_area_y + max_bar_h - bh
        bar_fill = "url(#barGrad)" if m["total"] > 0 else BAR_EMPTY
        delay = 0.28 + i * 0.02

        parts.append(
            f'<g class="fade-in" style="animation-delay: {delay:.3f}s;">'
            f'<rect class="bar-grow" x="{bx}" y="{by}" width="{bar_w}" height="{bh}" rx="2" fill="{bar_fill}">'
            f'<title>{m["label"]} {m.get("year", "")}: {m["total"]} contributions</title>'
            f'</rect>'
        )

        if m["total"] > 0:
            parts.append(
                f'<text x="{bx + bar_w/2}" y="{by - 3}" fill="{MUTED}" font-size="7" text-anchor="middle">{m["total"]}</text>'
            )

        parts.append(
            f'<text x="{bx + bar_w/2}" y="{bar_area_y + max_bar_h + 11}" fill="{MUTED}" font-size="7.5" text-anchor="middle">'
            f'{m["label"][:3]}'
            f'</text>'
            f'</g>'
        )

    # -------------------------------------------------------------
    # GITHUB ACTIVITY (PUBLIC) SECTION — 6 CARDS IN 2 ROWS OF 3
    # -------------------------------------------------------------
    stats_y = bar_area_y + max_bar_h + 22
    parts.append(
        f'<g class="fade-in" style="animation-delay: 0.52s;">'
        f'<text x="{PAD}" y="{stats_y}" fill="{MUTED}" font-size="8" font-weight="600" letter-spacing="0.5">'
        f'GITHUB ACTIVITY (PUBLIC)'
        f'</text>'
        f'<line x1="{PAD}" y1="{stats_y + 4}" x2="{CARD_WIDTH - PAD}" y2="{stats_y + 4}" stroke="{PANEL_BORDER}" stroke-width="1"/>'
        f'</g>'
    )

    card_gap = 7
    card_w = (CARD_WIDTH - (PAD * 2) - (card_gap * 2)) / 3
    card_h = 40
    row1_y = stats_y + 9
    row2_y = row1_y + card_h + 5

    activity_cards = [
        # Row 1
        {
            "row": 0, "col": 0,
            "label": "COMMITS (365D)",
            "val": str(commits_val) if commits_val is not None else "—",
            "sub": "Trailing 365 Days",
            "color": ACCENT_GREEN,
            "delay": 0.54,
        },
        {
            "row": 0, "col": 1,
            "label": "REPOSITORIES",
            "val": str(repos_val) if repos_val is not None else "—",
            "sub": "Public Repos",
            "color": ACCENT_CYAN,
            "delay": 0.57,
        },
        {
            "row": 0, "col": 2,
            "label": "STARS EARNED",
            "val": str(stars_val) if stars_val is not None else "—",
            "sub": "Across Repos",
            "color": ACCENT_AMBER,
            "delay": 0.60,
        },
        # Row 2
        {
            "row": 1, "col": 0,
            "label": "PULL REQUESTS",
            "val": str(prs_val) if prs_val is not None else "—",
            "sub": pr_sub,
            "color": ACCENT_PURPLE,
            "delay": 0.63,
        },
        {
            "row": 1, "col": 1,
            "label": "CODE REVIEWS",
            "val": str(reviews_val) if reviews_val is not None else "0",
            "sub": "Public PR Reviews",
            "color": MUTED,
            "delay": 0.66,
        },
        {
            "row": 1, "col": 2,
            "label": "ISSUES",
            "val": str(issues_val) if issues_val is not None else "—",
            "sub": "Created Issues",
            "color": ACCENT_GOLD,
            "delay": 0.69,
        },
    ]

    for item in activity_cards:
        mx = PAD + item["col"] * (card_w + card_gap)
        my = row1_y if item["row"] == 0 else row2_y

        parts.append(
            f'<g class="fade-in" style="animation-delay: {item["delay"]}s;">'
            f'<rect x="{mx}" y="{my}" width="{card_w}" height="{card_h}" rx="5" '
            f'fill="{PANEL_BG}" stroke="{PANEL_BORDER}" stroke-width="1"/>'
            f'<text x="{mx + card_w/2}" y="{my + 12}" fill="{MUTED}" font-size="7.5" font-weight="600" text-anchor="middle" letter-spacing="0.4">{item["label"]}</text>'
            f'<text x="{mx + card_w/2}" y="{my + 26}" fill="{item["color"]}" font-size="12.5" font-weight="700" text-anchor="middle">{item["val"]}</text>'
            f'<text x="{mx + card_w/2}" y="{my + 36}" fill="{MUTED}" font-size="6.8" text-anchor="middle">{item["sub"]}</text>'
            f'</g>'
        )

    # Subtle footer note
    footer_y = row2_y + card_h + 14
    parts.append(
        f'<text x="{CARD_WIDTH/2}" y="{footer_y}" fill="{MUTED}" font-size="7" opacity="0.7" text-anchor="middle">'
        f'Public account activity • Commits: trailing 365-day search'
        f'</text>'
    )

    parts.append("</svg>")
    svg_content = "\n".join(parts)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated Info Card SVG at: {out_path} ({len(svg_content)} bytes)")


def main():
    if not os.path.exists(IN_PATH):
        raise FileNotFoundError(f"Input file not found at {IN_PATH}")

    with open(IN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    render_info_card(data, OUT_PATH)


if __name__ == "__main__":
    main()
