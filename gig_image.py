"""
gig_image.py
Generates Fiverr-style gig images (550x370) entirely with Pillow —
no external image assets or internet access required at runtime.
"""

import os
import random
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(BASE_DIR, "fonts", "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(BASE_DIR, "fonts", "DejaVuSans.ttf")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 550, 370

# Category -> (accent color, badge letter/short tag)
CATEGORY_STYLES = {
    "design":       {"accent": "#6C5CE7", "tag": "DESIGN"},
    "writing":      {"accent": "#00B894", "tag": "WRITING"},
    "marketing":    {"accent": "#E17055", "tag": "MARKETING"},
    "video":        {"accent": "#0984E3", "tag": "VIDEO"},
    "programming":  {"accent": "#2D3436", "tag": "DEV"},
    "music":        {"accent": "#D63031", "tag": "AUDIO"},
    "business":     {"accent": "#FDCB6E", "tag": "BUSINESS"},
}

STYLE_LAYOUTS = ["minimal", "bold", "professional", "creative"]


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _lighten(rgb, factor=0.35):
    return tuple(int(c + (255 - c) * factor) for c in rgb)


def _darken(rgb, factor=0.35):
    return tuple(int(c * (1 - factor)) for c in rgb)


def _gradient_background(color_hex, direction="diagonal"):
    """Creates a smooth two-tone gradient background."""
    base = _hex_to_rgb(color_hex)
    top = _lighten(base, 0.15)
    bottom = _darken(base, 0.25)

    img = Image.new("RGB", (WIDTH, HEIGHT), top)
    draw = ImageDraw.Draw(img)

    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
        g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
        b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    return img


def _fit_font(draw, text, max_width, start_size, font_path, min_size=20):
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(font_path, min_size)


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_badge(draw, x, y, text, accent_rgb):
    font = ImageFont.truetype(FONT_BOLD, 16)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 14, 8
    draw.rounded_rectangle(
        [x, y, x + tw + pad_x * 2, y + th + pad_y * 2],
        radius=18,
        fill=(255, 255, 255, 230),
    )
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=accent_rgb)


def _decorative_shapes(draw, style, accent_rgb):
    light = _lighten(accent_rgb, 0.25)
    if style == "minimal":
        draw.ellipse([WIDTH - 160, -60, WIDTH + 60, 140], fill=(*light, 60) if len(light) == 3 else light)
    elif style == "bold":
        draw.polygon(
            [(WIDTH, 0), (WIDTH - 180, 0), (WIDTH, 180)],
            fill=_darken(accent_rgb, 0.15),
        )
        draw.polygon(
            [(0, HEIGHT), (140, HEIGHT), (0, HEIGHT - 140)],
            fill=_darken(accent_rgb, 0.15),
        )
    elif style == "professional":
        draw.rectangle([0, HEIGHT - 12, WIDTH, HEIGHT], fill=_darken(accent_rgb, 0.35))
        draw.rectangle([0, 0, 12, HEIGHT], fill=_darken(accent_rgb, 0.35))
    elif style == "creative":
        for i in range(6):
            r = random.randint(10, 40)
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            draw.ellipse([x, y, x + r, y + r], fill=_lighten(accent_rgb, 0.4))


def generate_gig_image(title, category, style, color_hex=None, filename=None):
    """
    Generates one Fiverr gig image (550x370) and saves it to /output.

    title: gig title text, e.g. "I will design a modern minimalist logo"
    category: one of CATEGORY_STYLES keys
    style: one of STYLE_LAYOUTS
    color_hex: optional override accent color, e.g. "#FF5733"
    filename: optional output filename
    Returns the full file path.
    """
    category = category.lower()
    style = style.lower()
    if category not in CATEGORY_STYLES:
        category = "design"
    if style not in STYLE_LAYOUTS:
        style = "minimal"

    cat_data = CATEGORY_STYLES[category]
    accent_hex = color_hex if color_hex else cat_data["accent"]
    accent_rgb = _hex_to_rgb(accent_hex)

    img = _gradient_background(accent_hex)
    draw = ImageDraw.Draw(img, "RGBA")

    _decorative_shapes(draw, style, accent_rgb)

    # Category badge (top-left)
    _draw_badge(draw, 30, 30, cat_data["tag"], accent_rgb)

    # "I WILL" kicker text
    kicker_font = ImageFont.truetype(FONT_BOLD, 18)
    draw.text((32, 90), "I WILL", font=kicker_font, fill=(255, 255, 255))

    # Main title, auto-wrapped and auto-fit
    title_text = title.upper() if style == "bold" else title
    max_text_width = WIDTH - 64
    title_font = _fit_font(draw, title_text, max_text_width, 40, FONT_BOLD, min_size=22)
    lines = _wrap_text(draw, title_text, title_font, max_text_width)[:4]

    y = 125
    for line in lines:
        draw.text((32, y), line, font=title_font, fill=(255, 255, 255))
        bbox = draw.textbbox((0, 0), line, font=title_font)
        y += (bbox[3] - bbox[1]) + 10

    # Footer strip
    footer_font = ImageFont.truetype(FONT_REGULAR, 14)
    draw.text((32, HEIGHT - 34), "Professional Fiverr Gig", font=footer_font, fill=(255, 255, 255, 200))

    # Slight blur on decorative background elements only would need layering;
    # keeping single-layer for simplicity and speed.

    if not filename:
        safe_title = "".join(c for c in title[:20] if c.isalnum() or c == " ").strip().replace(" ", "_")
        filename = f"{safe_title or 'gig'}_{category}_{style}.png"

    path = os.path.join(OUTPUT_DIR, filename)
    img.save(path, "PNG")
    return path


def generate_variations(title, category, color_hex=None, count=3):
    """Generates `count` different style variations for the same gig title."""
    styles = random.sample(STYLE_LAYOUTS, min(count, len(STYLE_LAYOUTS)))
    paths = []
    for i, style in enumerate(styles):
        fname = f"variation_{i}_{category}_{style}.png"
        path = generate_gig_image(title, category, style, color_hex, filename=fname)
        paths.append(path)
    return paths
