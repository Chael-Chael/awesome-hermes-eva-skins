"""Build experimental quadrant-block EVA banner fragments."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

from image_to_rich_braille import (
    detect_background_rgb,
    preprocess_pixel_art_block_layer,
    render_pixel_art_quadrant_blocks,
    set_pixel_art_tints,
    yaml_block,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path.home() / "Downloads" / "evafinalpixeljointprevia_heads"
OUT_DIR = ROOT / "screenshots"
WIDTH = 50
ITEMS = [
    ("eva-00", "01_unit-00_blue.png", (154, 216, 255), (128, 210, 255)),
    ("eva-01", "02_unit-01_purple.png", (128, 184, 255), (106, 155, 232)),
    ("eva-02", "03_unit-02_red.png", (255, 192, 160), (255, 159, 184)),
]
TAG_RE = re.compile(r"\[([^\]]+)\](.*?)\[/\]")


def make_fragment(
    image_path: Path,
    *,
    white_tint: tuple[int, int, int],
    neutral_shadow: tuple[int, int, int],
) -> str:
    set_pixel_art_tints(white_tint=white_tint, neutral_shadow=neutral_shadow)
    source = Image.open(image_path).convert("RGBA")
    background = detect_background_rgb(source)
    processed = preprocess_pixel_art_block_layer(
        source,
        width=WIDTH,
        background_rgb=background,
        background_tolerance=37.0,
        alpha_threshold=12,
        autocrop=True,
        palette_size=None,
    )
    return render_pixel_art_quadrant_blocks(
        processed,
        background_rgb=background,
        background_tolerance=37.0,
        alpha_threshold=12,
        min_cell_coverage=0.0,
        ink_color=(0, 16, 6),
        neutral_color=(154, 166, 184),
        fallback_color=(255, 255, 255),
        blank_white=False,
        bold=False,
    )


def parse_style(style: str) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
    style = style.strip()
    fg: tuple[int, int, int] | None = None
    bg: tuple[int, int, int] | None = None
    if " on " in style:
        left, right = style.split(" on ", 1)
        fg = parse_hex(left.strip().split()[-1])
        bg = parse_hex(right.strip().split()[-1])
    else:
        fg = parse_hex(style.split()[-1])
    return fg, bg


def parse_hex(value: str) -> tuple[int, int, int] | None:
    if not value.startswith("#") or len(value) != 7:
        return None
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def draw_block(draw: ImageDraw.ImageDraw, x: int, y: int, char: str, fg, bg, scale: int) -> None:
    if bg:
        draw.rectangle((x, y, x + scale * 2 - 1, y + scale * 2 - 1), fill=bg)
    if not fg:
        return
    if char == "█":
        draw.rectangle((x, y, x + scale * 2 - 1, y + scale * 2 - 1), fill=fg)
        return
    quadrants = {
        "▘": (1, 0, 0, 0),
        "▝": (0, 1, 0, 0),
        "▀": (1, 1, 0, 0),
        "▖": (0, 0, 1, 0),
        "▌": (1, 0, 1, 0),
        "▞": (0, 1, 1, 0),
        "▛": (1, 1, 1, 0),
        "▗": (0, 0, 0, 1),
        "▚": (1, 0, 0, 1),
        "▐": (0, 1, 0, 1),
        "▜": (1, 1, 0, 1),
        "▄": (0, 0, 1, 1),
        "▙": (1, 0, 1, 1),
        "▟": (0, 1, 1, 1),
        "█": (1, 1, 1, 1),
    }.get(char, (0, 0, 0, 0))
    boxes = (
        (x, y, x + scale - 1, y + scale - 1),
        (x + scale, y, x + scale * 2 - 1, y + scale - 1),
        (x, y + scale, x + scale - 1, y + scale * 2 - 1),
        (x + scale, y + scale, x + scale * 2 - 1, y + scale * 2 - 1),
    )
    for active, box in zip(quadrants, boxes):
        if active:
            draw.rectangle(box, fill=fg)


def render_preview(fragments: list[tuple[str, str]]) -> Path:
    scale = 5
    panels = []
    for name, rich in fragments:
        rows = rich.splitlines()
        plain_width = max(len(re.sub(r"\[[^\]]+\]|\[/\]", "", row)) for row in rows)
        image = Image.new("RGB", (plain_width * scale * 2 + 32, len(rows) * scale * 2 + 48), (12, 16, 23))
        draw = ImageDraw.Draw(image)
        draw.text((12, 10), f"{name} quadrant", fill=(160, 185, 255))
        y = 34
        for row in rows:
            x = 16
            pos = 0
            while pos < len(row):
                match = TAG_RE.match(row, pos)
                if match:
                    fg, bg = parse_style(match.group(1))
                    for char in match.group(2):
                        draw_block(draw, x, y, char, fg, bg, scale)
                        x += scale * 2
                    pos = match.end()
                else:
                    draw_block(draw, x, y, row[pos], None, None, scale)
                    x += scale * 2
                    pos += 1
            y += scale * 2
        panels.append(image)

    output = Image.new(
        "RGB",
        (max(panel.width for panel in panels), sum(panel.height for panel in panels) + 16 * (len(panels) - 1)),
        (8, 11, 16),
    )
    y = 0
    for panel in panels:
        output.paste(panel, (0, y))
        y += panel.height + 16
    out_path = OUT_DIR / "eva-quadrant-block-preview.png"
    output.save(out_path)
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fragments: list[tuple[str, str]] = []
    for name, image_name, white_tint, neutral_shadow in ITEMS:
        rich = make_fragment(SOURCE_DIR / image_name, white_tint=white_tint, neutral_shadow=neutral_shadow)
        fragments.append((name, rich))
        path = OUT_DIR / f"{name}-quadrant-block.yaml"
        path.write_text(yaml_block("banner_hero", rich) + "\n", encoding="utf-8", newline="\n")
        print(path)
    print(render_preview(fragments))


if __name__ == "__main__":
    main()
