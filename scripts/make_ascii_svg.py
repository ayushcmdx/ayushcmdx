#!/usr/bin/env python3
"""
Convert Ayush's photograph (img/Ayush_Raj_Face.png) into a high-contrast,
monochrome ASCII art portrait and render it as an animated SVG (assets/ayush-ascii.svg).

Features:
- Terminal-styled window container matching the profile aesthetic
- Crisp monospace ASCII rendering with precise aspect-ratio compensation
- Cascade reveal animation (line by line typing / printing effect)
- Graceful degradation: Fully visible if CSS/SVG animation is unsupported
"""
import os
import sys
import xml.sax.saxutils as saxutils
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

HERE = os.path.dirname(__file__)
IMG_PATH = os.path.join(HERE, "..", "img", "Ayush_Raj_Face.png")
OUT_PATH = os.path.join(HERE, "..", "assets", "ayush-ascii.svg")

# Monospace character ramp: dark to light
RAMP = " .':;!+*eE#%@"

# Card Dimensions
CARD_WIDTH = 400
CARD_HEIGHT = 420
TITLEBAR_H = 32
PADDING_X = 20
PADDING_Y = 16

# Terminal Theme Colors
BG_COLOR = "#0d1117"
BG_GRAD_TOP = "#161b22"
BORDER_COLOR = "#30363d"
TITLE_TEXT_COLOR = "#8b949e"
ASCII_TEXT_COLOR = "#c9d1d9"
ACCENT_GREEN = "#39d353"


def image_to_ascii(image_path, cols=62, rows=38):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at: {image_path}")

    img = Image.open(image_path).convert("RGBA")

    # Composite onto dark background
    bg = Image.new("RGB", img.size, (13, 17, 23))
    bg.paste(img, mask=img.split()[-1])

    # Convert to grayscale
    gray = bg.convert("L")

    # Crop slightly to center on face if needed, or maintain portrait proportions
    # The image is 1024x1024. Let's center-crop to 1024x1024 or tighten slightly
    w, h = gray.size
    # Center crop with slight margin
    crop_box = (int(w * 0.05), int(h * 0.02), int(w * 0.95), int(h * 0.98))
    gray = gray.crop(crop_box)

    # Enhance contrast and sharpness for crisp ASCII output
    gray = ImageOps.autocontrast(gray, cutoff=(1, 1))
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(1.5)
    sharpener = ImageEnhance.Sharpness(gray)
    gray = sharpener.enhance(1.4)

    # Resize with high quality resampling
    small = gray.resize((cols, rows), Image.Resampling.LANCZOS)

    lines = []
    ramp_len = len(RAMP)
    for y in range(rows):
        line_chars = []
        for x in range(cols):
            pixel = small.getpixel((x, y))
            idx = int((pixel / 255.0) * (ramp_len - 1))
            line_chars.append(RAMP[idx])
        lines.append("".join(line_chars))

    return lines


def generate_ascii_svg(lines, out_path=OUT_PATH):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    rows = len(lines)
    # Character sizing inside the SVG
    font_size = 8.5
    line_height = 9.2
    char_width = 5.2

    # Animation timings
    row_delay_step = 0.035
    anim_duration = 0.45

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" '
        f'viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, \'Courier New\', monospace">',
        "<style>",
        "  .window-bg { fill: #0d1117; }",
        "  .window-border { fill: none; stroke: #30363d; stroke-width: 1; }",
        "  .title-line { stroke: #21262d; stroke-width: 1; }",
        "  .title-text { fill: #8b949e; font-size: 11px; font-weight: 500; }",
        "  .ascii-line { fill: #c9d1d9; font-size: 8.5px; opacity: 1; transform-origin: left center; }",
        "  .anim-line { animation: typeIn 0.35s ease-out backwards; }",
        "  @keyframes typeIn {",
        "    0% { opacity: 0; transform: translateY(2px); }",
        "    100% { opacity: 1; transform: translateY(0); }",
        "  }",
        "  @media (prefers-reduced-motion: reduce) {",
        "    .anim-line { animation: none !important; opacity: 1 !important; }",
        "  }",
        "</style>",
        "<defs>",
        f'  <linearGradient id="cardGrad" x1="0" y1="0" x2="0" y2="1">',
        f'    <stop offset="0%" stop-color="{BG_GRAD_TOP}"/>',
        f'    <stop offset="100%" stop-color="{BG_COLOR}"/>',
        "  </linearGradient>",
        "</defs>",
        f'<rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="10" fill="url(#cardGrad)"/>',
        f'<rect x="0.5" y="0.5" width="{CARD_WIDTH-1}" height="{CARD_HEIGHT-1}" rx="10" class="window-border"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{CARD_WIDTH}" y2="{TITLEBAR_H}" class="title-line"/>',
    ]

    # Terminal buttons
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        svg_parts.append(f'<circle cx="{PADDING_X + i * 14}" cy="{TITLEBAR_H // 2}" r="4.5" fill="{color}"/>')

    # Title text
    svg_parts.append(
        f'<text x="{CARD_WIDTH // 2}" y="{TITLEBAR_H // 2 + 4}" class="title-text" text-anchor="middle">'
        f'ayushcmdx@github: ~/whoami --portrait'
        f'</text>'
    )

    # ASCII text container
    start_y = TITLEBAR_H + PADDING_Y + 4
    start_x = PADDING_X + 4

    for idx, line in enumerate(lines):
        y_pos = start_y + idx * line_height
        delay = idx * row_delay_step
        escaped_line = saxutils.escape(line).replace(" ", "&#160;")
        svg_parts.append(
            f'<text class="ascii-line anim-line" x="{start_x}" y="{y_pos:.1f}" '
            f'style="animation-delay: {delay:.3f}s;">{escaped_line}</text>'
        )

    svg_parts.append("</svg>")

    svg_content = "\n".join(svg_parts)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated ASCII SVG at: {out_path} ({len(svg_content)} bytes)")


if __name__ == "__main__":
    lines = image_to_ascii(IMG_PATH, cols=62, rows=38)
    generate_ascii_svg(lines, OUT_PATH)
