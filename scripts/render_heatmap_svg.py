#!/usr/bin/env python3
"""
Render data/contributions.json into an animated terminal-style GitHub contribution
heatmap SVG (assets/contrib-heatmap.svg).

Features:
- Terminal window header with macOS-style window controls
- Terminal title: ayushcmdx@github: ~/contributions --graph
- 53-week x 7-day contribution grid with rounded cells
- GitHub intensity green palette
- Month and weekday labels
- Diagonal sequential reveal animation (CSS keyframes with backwards fill)
- Interactive tooltip titles on cells
- Less -> More legend
- Real summary statistics footer
- Graceful degradation: Remains completely visible if animations are unsupported
"""
import datetime
import json
import os
import xml.sax.saxutils as saxutils

HERE = os.path.dirname(__file__)
IN_PATH = os.path.join(HERE, "..", "data", "contributions.json")
OUT_ASSETS = os.path.join(HERE, "..", "assets", "contrib-heatmap.svg")
OUT_ROOT = os.path.join(HERE, "..", "contrib-heatmap.svg")

# GitHub dark theme green palette: Level 0 (empty) to Level 5 (neon max)
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#56f085"]

# Dimensions & Layout
CELL = 12
GAP = 3
STEP = CELL + GAP
PAD = 20
LEFT_LABEL_W = 32
TOP_LABEL_H = 22
TITLEBAR_H = 32
STATS_FOOTER_H = 84

# Colors
BG_COLOR = "#0d1117"
BG_GRAD_TOP = "#161b22"
BORDER_COLOR = "#30363d"
MUTED = "#8b949e"
TEXT_PRIMARY = "#e6edf3"
ACCENT_CYAN = "#22d3ee"
ACCENT_GREEN = "#39d353"
ACCENT_GOLD = "#f2cc60"
DIVIDER_LINE = "#21262d"

# Animation timing
COL_T = 0.055   # delay per column (left-to-right sweep)
ROW_T = 0.030   # delay per row (top-to-bottom cascade)
POP_DUR = 0.50
FLASH_DUR = 0.65


def level_for(count):
    if count == 0:
        return 0
    if count <= 2:
        return 1
    if count <= 6:
        return 2
    if count <= 12:
        return 3
    if count <= 20:
        return 4
    return 5


def build_grid(days):
    """Organize calendar days into 7-row columns (Sunday=0 through Saturday=6)."""
    if not days:
        return []

    first = datetime.date.fromisoformat(days[0]["date"])
    lead_pad = (first.weekday() + 1) % 7  # 0=Sunday
    grid = []
    col = [None] * lead_pad

    for d in days:
        date = datetime.date.fromisoformat(d["date"])
        weekday = (date.weekday() + 1) % 7
        while len(col) < weekday:
            col.append(None)
        col.append((d["date"], d["count"], level_for(d["count"])))
        if len(col) == 7:
            grid.append(col)
            col = []

    if col:
        while len(col) < 7:
            col.append(None)
        grid.append(col)

    return grid


def render(data):
    days = data.get("days", [])
    if not days:
        raise ValueError("Missing 'days' in contribution data.")

    username = data.get("username", "ayushcmdx")
    grid = build_grid(days)
    n_cols = len(grid)

    art_w = n_cols * STEP
    art_h = 7 * STEP

    month_labels = []
    seen_months = set()
    for ci, column in enumerate(grid):
        for cell in column:
            if cell is None:
                continue
            date = datetime.date.fromisoformat(cell[0])
            key = (date.year, date.month)
            if key not in seen_months and date.day <= 7:
                seen_months.add(key)
                month_labels.append((ci, date.strftime("%b")))
            break

    canvas_w = PAD + LEFT_LABEL_W + art_w + PAD
    canvas_h = TITLEBAR_H + TOP_LABEL_H + art_h + STATS_FOOTER_H + PAD

    css = f"""
  .cell {{ transform-box: fill-box; transform-origin: center; opacity: 1; }}
  .anim-cell {{ animation: popIn {POP_DUR}s ease-out backwards; }}
  .anim-flash {{ animation: popIn {POP_DUR}s ease-out backwards, flash {FLASH_DUR}s ease-out backwards; }}
  @keyframes popIn {{
    0% {{ opacity: 0; transform: scale(0.2); }}
    70% {{ opacity: 1; transform: scale(1.08); }}
    100% {{ opacity: 1; transform: scale(1); }}
  }}
  @keyframes flash {{
    0% {{ filter: brightness(2.4); }}
    50% {{ filter: brightness(2.0); }}
    100% {{ filter: brightness(1); }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    .cell, .anim-cell, .anim-flash {{ opacity: 1 !important; animation: none !important; }}
  }}
""".strip()

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, \'Liberation Mono\', monospace">',
        f'<style>{css}</style>',
        '<defs>',
        f'  <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1">',
        f'    <stop offset="0%" stop-color="{BG_GRAD_TOP}"/>',
        f'    <stop offset="100%" stop-color="{BG_COLOR}"/>',
        '  </linearGradient>',
        '</defs>',
        f'<rect width="{canvas_w}" height="{canvas_h}" rx="10" fill="url(#bgGrad)"/>',
        f'<rect x="0.5" y="0.5" width="{canvas_w-1}" height="{canvas_h-1}" rx="10" '
        f'fill="none" stroke="{BORDER_COLOR}" stroke-width="1"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{canvas_w}" y2="{TITLEBAR_H}" stroke="{DIVIDER_LINE}" stroke-width="1"/>',
    ]

    # Terminal buttons
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*14}" cy="{TITLEBAR_H/2}" r="4.5" fill="{color}"/>')

    # Window title
    parts.append(
        f'<text x="{canvas_w/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="11" font-weight="500" '
        f'text-anchor="middle">{username}@github: ~/contributions --graph</text>'
    )

    grid_top = TITLEBAR_H + TOP_LABEL_H
    grid_left = PAD + LEFT_LABEL_W

    # Month labels
    for ci, label in month_labels:
        x = grid_left + ci * STEP
        parts.append(f'<text x="{x}" y="{TITLEBAR_H + 15}" fill="{MUTED}" font-size="10">{label}</text>')

    # Weekday labels
    for wi, wname in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = grid_top + wi * STEP + CELL * 0.78
        parts.append(f'<text x="{PAD}" y="{y:.1f}" fill="{MUTED}" font-size="9">{wname}</text>')

    # Contribution grid cells
    for ci, column in enumerate(grid):
        gx = grid_left + ci * STEP
        for ri, cell in enumerate(column):
            if cell is None:
                continue
            date_s, count, lvl = cell
            gy = grid_top + ri * STEP
            delay = ci * COL_T + ri * ROW_T
            plural = "s" if count != 1 else ""

            cls = "cell anim-flash" if lvl > 0 else "cell anim-cell"
            parts.append(
                f'<rect class="{cls}" x="{gx}" y="{gy}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{PALETTE[lvl]}" style="animation-delay:{delay:.3f}s;">'
                f'<title>{date_s}: {count} contribution{plural}</title></rect>'
            )

    # Legend: Less [][][][][][] More
    leg_y = grid_top + art_h + 8
    leg_x = canvas_w - PAD - (len(PALETTE) * (CELL - 1) + 68)
    parts.append(f'<text x="{leg_x}" y="{leg_y + CELL*0.8:.1f}" fill="{MUTED}" font-size="10" text-anchor="end">Less</text>')
    lx = leg_x + 6
    for color in PALETTE:
        parts.append(f'<rect x="{lx}" y="{leg_y}" width="{CELL-1}" height="{CELL-1}" rx="2" fill="{color}"/>')
        lx += CELL
    parts.append(f'<text x="{lx + 4}" y="{leg_y + CELL*0.8:.1f}" fill="{MUTED}" font-size="10">More</text>')

    # Divider before statistics footer
    sep_y = leg_y + CELL + 14
    parts.append(f'<line x1="0" y1="{sep_y}" x2="{canvas_w}" y2="{sep_y}" stroke="{DIVIDER_LINE}" stroke-width="1"/>')

    # Footer metrics
    cs = data.get("current_streak", {}).get("length", 0)
    ls = data.get("longest_streak", {}).get("length", 0)
    total = data.get("total_contributions", 0)
    best = data.get("best_day", {"count": 0, "date": "N/A"})
    rng = data.get("range", {"start": "", "end": ""})

    ly = sep_y + 22
    # Row 1: Total contributions & Date range
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="12" fill="{ACCENT_GREEN}">'
                 f'<tspan font-weight="700">{total:,}</tspan>'
                 f'<tspan fill="{MUTED}"> contributions in the last year</tspan></text>')
    parts.append(f'<text x="{canvas_w - PAD}" y="{ly}" font-size="11" fill="{MUTED}" text-anchor="end">'
                 f'{rng["start"]} &#8594; {rng["end"]}</text>')

    ly += 22
    # Row 2: Streaks & Best Day
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="12" fill="{MUTED}">current streak '
                 f'<tspan fill="{ACCENT_CYAN}" font-weight="700">{cs} days</tspan>'
                 f'<tspan fill="{MUTED}">   &#183;   longest </tspan>'
                 f'<tspan fill="{ACCENT_CYAN}" font-weight="700">{ls} days</tspan></text>')
    parts.append(f'<text x="{canvas_w - PAD}" y="{ly}" font-size="11" fill="{MUTED}" text-anchor="end">'
                 f'best day <tspan fill="{ACCENT_GOLD}" font-weight="700">{best["count"]}</tspan> on {best["date"]}</text>')

    parts.append("</svg>")
    return "".join(parts)


def main():
    if not os.path.exists(IN_PATH):
        raise FileNotFoundError(f"Input file not found at {IN_PATH}")

    with open(IN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    svg_content = render(data)

    os.makedirs(os.path.dirname(OUT_ASSETS), exist_ok=True)
    with open(OUT_ASSETS, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Wrote {OUT_ASSETS} ({len(svg_content)} bytes)")

    # Also write root copy for backwards compatibility
    with open(OUT_ROOT, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Wrote {OUT_ROOT} ({len(svg_content)} bytes)")


if __name__ == "__main__":
    main()
