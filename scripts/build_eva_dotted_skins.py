"""Build experimental 2x2-shaped braille-dot EVA skins."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw

from build_eva_block_fragments import ITEMS, SOURCE_DIR
from build_eva_skins import EVA_SPECS, make_skin_yaml
from image_to_rich_braille import (
    BRAILLE_BLANK,
    detect_background_rgb,
    preprocess_pixel_art_block_layer,
    render_pixel_art_dotted_quadrants,
    yaml_block,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "screenshots"
SKINS_DIR = ROOT / "skins"
WIDTH = 50
TAG_RE = re.compile(r"\[#([0-9a-fA-F]{6})\](.*?)\[/\]")


def make_fragment(image_path: Path) -> str:
    source = Image.open(image_path).convert("RGBA")
    background = detect_background_rgb(source)
    processed = preprocess_pixel_art_block_layer(
        source,
        width=WIDTH,
        background_rgb=background,
        background_tolerance=28.0,
        alpha_threshold=12,
        autocrop=True,
        palette_size=32,
    )
    return render_pixel_art_dotted_quadrants(
        processed,
        background_rgb=background,
        background_tolerance=28.0,
        alpha_threshold=12,
        min_cell_coverage=0.05,
        ink_color=(42, 48, 56),
        neutral_color=(143, 152, 168),
        fallback_color=(255, 255, 255),
        bold=False,
    )


def render_preview(fragments: list[tuple[str, str]]) -> Path:
    char_w = 8
    char_h = 16
    panels = []
    for name, rich in fragments:
        rows = rich.splitlines()
        plain_width = max(len(re.sub(r"\[[^\]]+\]|\[/\]", "", row)) for row in rows)
        image = Image.new("RGB", (plain_width * char_w + 32, len(rows) * char_h + 48), (12, 16, 23))
        draw = ImageDraw.Draw(image)
        draw.text((12, 10), f"{name} dotted", fill=(160, 185, 255))
        y = 34
        for row in rows:
            x = 16
            pos = 0
            while pos < len(row):
                match = TAG_RE.match(row, pos)
                if match:
                    color = tuple(int(match.group(1)[index : index + 2], 16) for index in (0, 2, 4))
                    for char in match.group(2):
                        if char != BRAILLE_BLANK:
                            draw.text((x, y), char, fill=color)
                        x += char_w
                    pos = match.end()
                else:
                    x += char_w
                    pos += 1
            y += char_h
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
    out_path = OUT_DIR / "eva-dotted-quadrant-preview.png"
    output.save(out_path)
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SKINS_DIR.mkdir(parents=True, exist_ok=True)
    fragments: list[tuple[str, str]] = []
    fragment_by_name: dict[str, str] = {}
    for name, image_name in ITEMS:
        rich = make_fragment(SOURCE_DIR / image_name)
        fragments.append((name, rich))
        fragment_by_name[name] = rich
        fragment_path = OUT_DIR / f"{name}-dotted-quadrant.yaml"
        fragment_path.write_text(yaml_block("banner_hero", rich) + "\n", encoding="utf-8", newline="\n")
        print(fragment_path)

    for spec in EVA_SPECS:
        dotted_name = f"{spec.name}-dotted"
        dotted_spec = replace(
            spec,
            name=dotted_name,
            description=spec.description.replace("colored braille hero", "colored dotted quadrant hero"),
        )
        skin_path = SKINS_DIR / f"{dotted_name}.yaml"
        skin_path.write_text(make_skin_yaml(dotted_spec, fragment_by_name[spec.name]), encoding="utf-8", newline="\n")
        print(skin_path)

    print(render_preview(fragments))


if __name__ == "__main__":
    main()
