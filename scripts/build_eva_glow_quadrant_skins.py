"""Build glow-compensated EVA test skins using the quadrant-block renderer."""

from __future__ import annotations

import colorsys
from dataclasses import replace
from pathlib import Path
from typing import Sequence

import image_to_rich_braille as rich
from build_eva_block_fragments import ITEMS, SOURCE_DIR, make_fragment
from build_eva_skins import EVA_SPECS, make_skin_yaml


SATURATION_GAIN = 2.15
SATURATION_FLOOR = 0.72
VALUE_MIN = 0.51
VALUE_MAX = 0.92
VALUE_GAMMA = 1.38
SOURCE_CONTRAST = 1.51
SOURCE_EXPOSURE = -0.65
SHADOW_CRUSH = 0.20
HUE_SHIFT_DEGREES = -5.0
ACTIVE_VALUE_MAX = VALUE_MAX
UNIT_VALUE_MAX = {
    "eva-02": 0.72,
}
UNIT_TINTS = {
    "eva-02": {
        "white_tint": (184, 117, 98),
        "neutral_shadow": (184, 100, 116),
    },
}


def glow_compensated_pixel_art_visible_color(rgb: Sequence[int]) -> tuple[int, int, int]:
    """Map colored pixel art for readable HLSL with GLOW_STRENGTH=0.40."""
    if rich.is_pixel_art_blank_white(rgb):
        return rich.PIXEL_ART_WHITE_TINT
    if rich.is_pixel_art_neutral(rgb):
        return rich.pixel_art_neutral_color(rgb)

    r, g, b = (channel / 255.0 for channel in rgb[:3])
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + HUE_SHIFT_DEGREES / 360.0) % 1.0
    s = rich.clamp(max(s, SATURATION_FLOOR) * SATURATION_GAIN, 0.0, 1.0)
    v = rich.clamp((v - 0.5) * (1.0 + SOURCE_CONTRAST) + 0.5 + SOURCE_EXPOSURE, 0.0, 1.0)
    v = v**VALUE_GAMMA
    v = VALUE_MIN + v * (ACTIVE_VALUE_MAX - VALUE_MIN)
    if v < 0.52:
        v *= 1.0 - SHADOW_CRUSH * (1.0 - v / 0.52)
    v = rich.clamp(v, 0.0, 1.0)

    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return (round(rr * 255), round(gg * 255), round(bb * 255))


def main() -> None:
    global ACTIVE_VALUE_MAX
    rich.pixel_art_visible_color = glow_compensated_pixel_art_visible_color

    out_dir = Path("skins")
    out_dir.mkdir(exist_ok=True)
    fragments = {}
    for name, image_name, white_tint, neutral_shadow in ITEMS:
        ACTIVE_VALUE_MAX = UNIT_VALUE_MAX.get(name, VALUE_MAX)
        tints = UNIT_TINTS.get(name, {})
        fragments[name] = make_fragment(
            SOURCE_DIR / image_name,
            white_tint=tints.get("white_tint", white_tint),
            neutral_shadow=tints.get("neutral_shadow", neutral_shadow),
        )
    for spec in EVA_SPECS:
        glow_spec = replace(
            spec,
            name=f"{spec.name}-glow",
            description=f"{spec.description} - readable glow 0.40 quadrant compensation test",
        )
        path = out_dir / f"{glow_spec.name}.yaml"
        path.write_text(make_skin_yaml(glow_spec, fragments[spec.name]), encoding="utf-8", newline="\n")
        print(path)


if __name__ == "__main__":
    main()
