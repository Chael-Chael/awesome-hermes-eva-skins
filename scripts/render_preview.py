from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

from image_to_rich_braille import (
    detect_background_rgb,
    preprocess_pixel_art_layer,
    render_pixel_art_braille,
)


ROOT = Path(__file__).resolve().parents[1]
ITEMS = [
    ("eva-00", Path(r"C:\Users\27923\Downloads\evafinalpixeljointprevia_heads\01_unit-00_blue_white_bg.png")),
    ("eva-01", Path(r"C:\Users\27923\Downloads\evafinalpixeljointprevia_heads\02_unit-01_purple_white_bg.png")),
    ("eva-02", Path(r"C:\Users\27923\Downloads\evafinalpixeljointprevia_heads\03_unit-02_red_white_bg.png")),
]
TAG_RE = re.compile(r"\[#([0-9a-fA-F]{6})\](.*?)\[/\]")


def render_item(name: str, path: Path) -> Image.Image:
    source = Image.open(path).convert("RGBA")
    background = detect_background_rgb(source)
    processed = preprocess_pixel_art_layer(
        source,
        width=50,
        background_rgb=background,
        background_tolerance=28,
        alpha_threshold=12,
        autocrop=True,
        palette_size=32,
    )
    rich = render_pixel_art_braille(
        processed,
        background_rgb=background,
        background_tolerance=28,
        alpha_threshold=12,
        min_cell_coverage=0.05,
        outline_radius=0,
        ink_color=(42, 48, 56),
        neutral_color=(143, 152, 168),
        fallback_color=(255, 255, 255),
        bold=False,
    )

    rows = rich.splitlines()
    char_w = 8
    char_h = 16
    image = Image.new("RGB", (max(len(row) for row in rows) * char_w + 32, len(rows) * char_h + 56), (12, 16, 23))
    draw = ImageDraw.Draw(image)
    draw.text((16, 12), name, fill=(160, 185, 255))
    y = 40
    for row in rows:
        x = 16
        pos = 0
        while pos < len(row):
            match = TAG_RE.match(row, pos)
            if match:
                color = tuple(int(match.group(1)[i : i + 2], 16) for i in (0, 2, 4))
                for char in match.group(2):
                    if char != "\u2800":
                        draw.ellipse((x + 2, y + 5, x + 5, y + 8), fill=color)
                    x += char_w
                pos = match.end()
            else:
                x += char_w
                pos += 1
        y += char_h
    return image


def main() -> None:
    panels = [render_item(name, path) for name, path in ITEMS]
    output = Image.new(
        "RGB",
        (max(panel.width for panel in panels), sum(panel.height for panel in panels) + 16 * (len(panels) - 1)),
        (9, 12, 18),
    )
    y = 0
    for panel in panels:
        output.paste(panel, (0, y))
        y += panel.height + 16
    output_path = ROOT / "screenshots" / "white-bg-vivid-preview.png"
    output.save(output_path)
    print(output_path)


if __name__ == "__main__":
    main()
