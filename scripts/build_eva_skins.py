#!/usr/bin/env python3
"""Build the three EVA Hermes skins from extracted head images."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image

from image_to_rich_braille import (
    detect_background_rgb,
    preprocess_pixel_art_layer,
    render_pixel_art_braille,
)


@dataclass(frozen=True)
class EvaSkinSpec:
    name: str
    image_name: str
    description: str
    colors: dict[str, str]
    branding: dict[str, str]
    logo_color: str
    logo_accent: str
    thinking_verbs: list[str]


EVA_SPECS = (
    EvaSkinSpec(
        name="eva-00",
        image_name="01_unit-00_blue_white_bg.png",
        description="EVA-00 Prototype - Rei blue/white colored braille hero",
        colors={
            "banner_border": "#4da3ff",
            "banner_title": "#e8f5ff",
            "banner_accent": "#4da3ff",
            "banner_dim": "#24527f",
            "banner_text": "#d8ecff",
            "ui_accent": "#64b5f6",
            "ui_label": "#9ad8ff",
            "ui_ok": "#66bb6a",
            "ui_error": "#ef5350",
            "ui_warn": "#ffb74d",
            "prompt": "#e8f5ff",
            "input_rule": "#4da3ff",
            "response_border": "#2f6bb7",
            "session_label": "#9ad8ff",
            "session_border": "#2f6bb7",
        },
        branding={
            "agent_name": "NERV // EVA-00",
            "welcome": '"It must not run away."',
            "goodbye": "EVA-00 shutdown complete.",
            "response_label": " [EVA-00 Rei] ",
            "prompt_symbol": "00>",
            "help_header": "[EVA-00 MAGI Command Menu]",
        },
        logo_color="#e8f5ff",
        logo_accent="#4da3ff",
        thinking_verbs=[
            "cooling prototype armor",
            "aligning Rei sync pattern",
            "charging positron rifle",
            "holding AT Field",
            "reading blue status telemetry",
        ],
    ),
    EvaSkinSpec(
        name="eva-01",
        image_name="02_unit-01_purple_white_bg.png",
        description="EVA-01 Test Type - purple/green/orange colored braille hero",
        colors={
            "banner_border": "#8a5cff",
            "banner_title": "#d8ccff",
            "banner_accent": "#75ff57",
            "banner_dim": "#6b3fb3",
            "banner_text": "#f2ecff",
            "ui_accent": "#75ff57",
            "ui_label": "#ff9f2d",
            "ui_ok": "#75ff57",
            "ui_error": "#ff4d5f",
            "ui_warn": "#ff9f2d",
            "prompt": "#ffffff",
            "input_rule": "#75ff57",
            "response_border": "#8a5cff",
            "session_label": "#75ff57",
            "session_border": "#6b3fb3",
        },
        branding={
            "agent_name": "NERV // EVA-01",
            "welcome": "Sync ratio unstable. Entry plug ready.",
            "goodbye": "EVA-01 restraint locks engaged.",
            "response_label": " [EVA-01 Shinji] ",
            "prompt_symbol": "01>",
            "help_header": "[EVA-01 MAGI Command Menu]",
        },
        logo_color="#d8ccff",
        logo_accent="#75ff57",
        thinking_verbs=[
            "raising sync ratio",
            "stabilizing berserk signal",
            "opening progressive knife bay",
            "projecting AT Field",
            "checking purple armor telemetry",
        ],
    ),
    EvaSkinSpec(
        name="eva-02",
        image_name="03_unit-02_red_white_bg.png",
        description="EVA-02 Production Model - Asuka red/orange colored braille hero",
        colors={
            "banner_border": "#ff0015",
            "banner_title": "#ffffff",
            "banner_accent": "#ff3b1f",
            "banner_dim": "#a51212",
            "banner_text": "#fff2ed",
            "ui_accent": "#ff8800",
            "ui_label": "#ffb347",
            "ui_ok": "#4caf50",
            "ui_error": "#ef5350",
            "ui_warn": "#ffa726",
            "prompt": "#ffffff",
            "input_rule": "#ff8800",
            "response_border": "#ff0015",
            "session_label": "#ff8800",
            "session_border": "#ff0015",
        },
        branding={
            "agent_name": "NERV // EVA-02",
            "welcome": '"God\'s in His heaven, all\'s right with the world."',
            "goodbye": "EVA-02 deployment complete.",
            "response_label": " [EVA-02 Asuka] ",
            "prompt_symbol": "02>",
            "help_header": "[EVA-02 MAGI Command Menu]",
        },
        logo_color="#ffffff",
        logo_accent="#ff0015",
        thinking_verbs=[
            "boosting Asuka sync ratio",
            "priming progressive knife",
            "locking red armor telemetry",
            "breaching Angel pattern",
            "projecting AT Field",
        ],
    ),
)


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_block(key: str, value: str, indent: int = 2) -> str:
    pad = " " * indent
    return f"{key}: |-\n" + "\n".join(f"{pad}{line}" for line in value.splitlines())


def make_logo(spec: EvaSkinSpec) -> str:
    label = spec.name.upper().replace("-", "-")
    return "\n".join(
        [
            f"[bold {spec.logo_accent}]============================================================[/]",
            f"[bold {spec.logo_color}]  NERV SYSTEM // {label} // HERMES AGENT[/]",
            f"[bold {spec.logo_accent}]============================================================[/]",
        ]
    )


def make_hero(image_path: Path, width: int) -> str:
    source = Image.open(image_path).convert("RGBA")
    background_rgb = detect_background_rgb(source)
    processed = preprocess_pixel_art_layer(
        source,
        width=width,
        background_rgb=background_rgb,
        background_tolerance=28.0,
        alpha_threshold=12,
        autocrop=True,
        palette_size=32,
    )
    return render_pixel_art_braille(
        processed,
        background_rgb=background_rgb,
        background_tolerance=28.0,
        alpha_threshold=12,
        min_cell_coverage=0.05,
        fallback_color=(255, 255, 255),
        bold=False,
    )


def make_skin_yaml(spec: EvaSkinSpec, hero: str) -> str:
    lines: list[str] = [
        f"name: {spec.name}",
        f"description: {quote(spec.description)}",
        "colors:",
    ]
    lines.extend(f"  {key}: {quote(value)}" for key, value in spec.colors.items())
    lines.extend(
        [
            "spinner:",
            "  waiting_faces:",
            "    - \"[00]\"",
            "    - \"[01]\"",
            "    - \"[02]\"",
            "    - \"[AT]\"",
            "    - \"[MAGI]\"",
            "  thinking_faces:",
            "    - \"[00]\"",
            "    - \"[01]\"",
            "    - \"[02]\"",
            "    - \"[AT]\"",
            "    - \"[MAGI]\"",
            "  thinking_verbs:",
        ]
    )
    lines.extend(f"    - {quote(verb)}" for verb in spec.thinking_verbs)
    lines.extend(
        [
            "  wings:",
            "    - - \"<AT\"",
            "      - \"FIELD>\"",
            "branding:",
        ]
    )
    lines.extend(f"  {key}: {quote(value)}" for key, value in spec.branding.items())
    lines.extend(
        [
            "tool_prefix: \"|\"",
            "tool_emojis:",
            "  terminal: \"[TERM]\"",
            "  web_search: \"[WEB]\"",
            "  browser_navigate: \"[BROWSER]\"",
            "  file: \"[FILE]\"",
            "  todo: \"[TODO]\"",
            yaml_block("banner_logo", make_logo(spec)),
            yaml_block("banner_hero", hero),
        ]
    )
    return "\n".join(lines) + "\n"


def build_skins(source_dir: Path, skins_dir: Path, fragments_dir: Path, width: int) -> list[Path]:
    skins_dir.mkdir(parents=True, exist_ok=True)
    fragments_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for spec in EVA_SPECS:
        image_path = source_dir / spec.image_name
        if not image_path.exists():
            raise FileNotFoundError(f"Missing source image: {image_path}")

        hero = make_hero(image_path, width)
        skin_yaml = make_skin_yaml(spec, hero)
        skin_path = skins_dir / f"{spec.name}.yaml"
        skin_path.write_text(skin_yaml, encoding="utf-8", newline="\n")
        written.append(skin_path)

        fragment_path = fragments_dir / f"{spec.name}-rich-braille.yaml"
        fragment_path.write_text(yaml_block("banner_hero", hero) + "\n", encoding="utf-8", newline="\n")
        written.append(fragment_path)
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build EVA-00/01/02 Hermes skin YAML files.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path.home() / "Downloads" / "evafinalpixeljointprevia_heads",
        help="Directory containing extracted EVA head PNG files.",
    )
    parser.add_argument("--skins-dir", type=Path, default=Path("skins"), help="Output skin directory.")
    parser.add_argument(
        "--fragments-dir",
        type=Path,
        default=Path("screenshots"),
        help="Directory for generated banner_hero fragment YAML files.",
    )
    parser.add_argument("--width", type=int, default=50, help="Braille width in terminal cells.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    written = build_skins(args.source_dir, args.skins_dir, args.fragments_dir, args.width)
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
