#!/usr/bin/env python3
"""Build a NERV-themed Hermes skin from a supplied braille logo."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

from build_eva_skins import EvaSkinSpec, make_skin_yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "reference" / "nerv.png"
HERO_WIDTH = 50
BRAILLE_BLANK = "\u2800"
BRAILLE_BIT_GRID = (
    (0x01, 0x08),
    (0x02, 0x10),
    (0x04, 0x20),
    (0x40, 0x80),
)


RAW_HERO = """
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⣤⣤⣶⣶⣶⣿⣶⣾⣿⣶⣾⣶⣦⠄
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣤⣀⣀⡀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣤⣤
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢿⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡄
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣦⠀⠀⠀⠀⠀⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⡀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢷⣄⡀⠀⢀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠋
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠛⠁
⠀⠈⠙⣿⣿⣿⣦⡀⠀⠀⠉⢹⡟⠉⠁⠉⠹⣿⣿⡿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣌⣉⠉⠉
⠀⠀⠀⣿⠿⣿⣿⣷⣄⠀⠀⢸⡇⠀⠀⠀⠀⣿⣿⡇⠈⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣶⣄
⠀⠀⠀⣿⠀⠈⢿⣿⣿⣧⡀⢸⡇⠀⠀⠀⠀⣿⣿⣇⣀⣠⣿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦
⠀⠀⠀⣿⠀⠀⠀⠙⣿⣿⣿⣼⡇⠀⠀⠀⠀⣿⣿⡏⠉⠻⣿⠀⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄
⠀⠀⠀⣿⠀⠀⠀⠀⠈⠻⣿⣿⡇⠀⠀⠀⢀⣿⣿⡇⠀⠀⠹⠀⠀⣰⠙⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⠀⠀⠀⣿⡀⠀⠀⠀⠀⠀⠙⢿⡇⠀⠀⠀⢸⣿⣿⣧⡀⠀⢀⣀⣴⡇⠀⠀⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣆
⠀⠐⠛⠛⠛⠂⠀⠀⠀⠀⠀⠀⠃⠀⠀⠒⠛⠛⠛⠛⠛⠛⠛⠛⠛⠁⠀⠀⠀⠈⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠒⢶⣶⣶⡖⠒⠶⣶⣦⣄⠀⠐⠲⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡷
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⡇⠀⠀⠘⣿⣿⣧⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⡇⠀⠀⢠⣿⣿⠟⠀⠀⠀⢿⣿⣿⡝⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⡷⣶⣾⣿⡟⠁⠀⠀⠀⠀⠈⣿⣿⣷⡀⢹⣿⣿⣿⣿⣿⣿⣿⣿⣿⠆
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⡇⠈⢿⣿⣿⣆⠀⠀⠀⠀⠀⠘⣿⣿⣧⡞⠀⠙⢿⣿⣿⣿⣿⣿⣿
⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⡇⠀⠀⠻⣿⣿⣧⠀⠀⠀⠀⠀⠹⣿⡿⠁⠀⠀⠈⠻⣿⣿⣿⣿⡟
⠐⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠤⠾⠿⠿⠷⠤⠀⠀⠙⠿⠿⠷⠄⠀⠀⠀⠀⠻⠁⠀⠀⠀⠀⠀⠈⠻⣿⣿⣿⡀
⠀⠀⠅⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿
⠀⠀⠀⢁⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢄⠀⠘⠂
⠀⠀⠀⠀⠐⠀⠄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢔⢄⠔
⠀⠀⠀⠀⠀⠀⠪⠐⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⡐⠌⠂
⠀⠀⠀⠀⠀⠀⠀⠀⠐⠑⡕⠀⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠔⡄⠈⠉
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠐⢀⠃⢠⠀⢀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠄⠄⠂⢄⠈⠌⠈
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠐⠀⠨⠀⠐⠀⡠⢀⠄⢐⠈⠠⠈⠒⠐⠈⠈
""".strip("\n")


NERV_HERO_RED = "#b01010"


def foreground_mask(image: Image.Image) -> Image.Image:
    """Return a soft foreground mask for the red NERV mark on a white source."""
    rgba = image.convert("RGBA")
    mask = Image.new("L", rgba.size)
    output: list[int] = []
    for r, g, b, a in rgba.getdata():
        if a < 12:
            output.append(0)
            continue

        # The supplied logo is red-on-white.  Measuring distance from white keeps
        # anti-aliased red edges while dropping the white background.
        white_distance = max(255 - r, 255 - g, 255 - b)
        output.append(int(max(0, min(255, white_distance * (a / 255.0) * 1.35))))
    mask.putdata(output)
    return mask


def content_bbox(mask: Image.Image) -> tuple[int, int, int, int]:
    threshold = mask.point(lambda value: 255 if value > 12 else 0)
    bbox = threshold.getbbox()
    if bbox is None:
        return (0, 0, mask.width, mask.height)

    left, top, right, bottom = bbox
    pad = max(2, round(max(right - left, bottom - top) * 0.015))
    return (
        max(0, left - pad),
        max(0, top - pad),
        min(mask.width, right + pad),
        min(mask.height, bottom + pad),
    )


def image_to_braille_hero(path: Path, width: int) -> str:
    source = Image.open(path)
    mask = foreground_mask(source)
    cropped = mask.crop(content_bbox(mask))

    rows = max(1, round((cropped.height / cropped.width) * width * 0.5))
    target = cropped.resize((width * 2, rows * 4), Image.Resampling.LANCZOS)
    # Slight max filter keeps thin serifs/dots from disappearing at 50 columns.
    target = target.filter(ImageFilter.MaxFilter(3))
    pixels = target.load()

    lines: list[str] = []
    for row in range(rows):
        chars: list[str] = []
        for col in range(width):
            bits = 0
            for dy in range(4):
                for dx in range(2):
                    if pixels[col * 2 + dx, row * 4 + dy] >= 58:
                        bits |= BRAILLE_BIT_GRID[dy][dx]
            chars.append(chr(0x2800 + bits) if bits else BRAILLE_BLANK)
        lines.append("".join(chars))
    return "\n".join(lines)


def braille_density(char: str) -> int:
    code = ord(char)
    if 0x2800 <= code <= 0x28FF:
        return (code - 0x2800).bit_count()
    return 1 if not char.isspace() else 0


def hero_color(char: str) -> str | None:
    density = braille_density(char)
    if density <= 0:
        return None
    return NERV_HERO_RED


def tint_hero(hero: str) -> str:
    lines: list[str] = []
    for line in hero.splitlines():
        out: list[str] = []
        active_color: str | None = None
        buffer: list[str] = []

        def flush() -> None:
            nonlocal active_color, buffer
            if not buffer:
                return
            text = "".join(buffer)
            if active_color:
                out.append(f"[{active_color}]{text}[/]")
            else:
                out.append(text)
            buffer = []

        for char in line:
            color = hero_color(char)
            if color != active_color:
                flush()
                active_color = color
            buffer.append(char)
        flush()
        lines.append("".join(out))
    return "\n".join(lines)


def normalize_hero_width(hero: str, width: int) -> str:
    lines: list[str] = []
    for line in hero.splitlines():
        if len(line) > width:
            lines.append(line[:width])
        else:
            lines.append(line + (BRAILLE_BLANK * (width - len(line))))
    return "\n".join(lines)


NERV_SPEC = EvaSkinSpec(
    name="eva-nerv",
    image_name="",
    description="NERV command skin - red tinted Seele/NERV braille hero",
    colors={
        "banner_border": "#ffffff",
        "banner_title": "#ffdddd",
        "banner_accent": "#ff3030",
        "banner_dim": "#d84a3f",
        "banner_text": "#ffe8e8",
        "ui_accent": "#ff3030",
        "ui_label": "#ffb3a3",
        "ui_ok": "#ff3030",
        "ui_error": "#ff5a5a",
        "ui_warn": "#ff8a3d",
        "prompt": "#ffdddd",
        "input_rule": "#ff0033",
        "response_border": "#ff0033",
        "session_label": "#ffb3a3",
        "session_border": "#ff0033",
    },
    branding={
        "agent_name": "NERV // CENTRAL DOGMA",
        "welcome": '"God is in his heaven. All is right with the world."',
        "goodbye": "NERV command channel closed.",
        "response_label": " [NERV MAGI] ",
        "prompt_symbol": "NERV>",
        "help_header": "[NERV MAGI Command Menu]",
    },
    logo_color="#ffdddd",
    logo_accent="#ff0033",
    thinking_verbs=[
        "routing MAGI consensus",
        "raising red alert channel",
        "checking Central Dogma telemetry",
        "projecting operational boundary",
        "synchronizing NERV command link",
    ],
)


def main() -> None:
    out_dir = Path("skins")
    out_dir.mkdir(exist_ok=True)
    raw_hero = image_to_braille_hero(SOURCE_IMAGE, HERO_WIDTH)
    hero = tint_hero(normalize_hero_width(raw_hero, HERO_WIDTH))
    out_path = out_dir / "eva-nerv.yaml"
    out_path.write_text(make_skin_yaml(NERV_SPEC, hero), encoding="utf-8", newline="\n")
    print(out_path)


if __name__ == "__main__":
    main()
