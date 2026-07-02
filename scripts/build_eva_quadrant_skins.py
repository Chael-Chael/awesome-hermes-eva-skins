"""Build the main Hermes skins using the quadrant-block renderer."""

from __future__ import annotations

from pathlib import Path

from build_eva_block_fragments import ITEMS, SOURCE_DIR, make_fragment
from build_eva_skins import EVA_SPECS, make_skin_yaml


def main() -> None:
    out_dir = Path("skins")
    out_dir.mkdir(exist_ok=True)
    fragments = {
        name: make_fragment(SOURCE_DIR / image_name, white_tint=white_tint, neutral_shadow=neutral_shadow)
        for name, image_name, white_tint, neutral_shadow in ITEMS
    }
    for spec in EVA_SPECS:
        path = out_dir / f"{spec.name}.yaml"
        path.write_text(make_skin_yaml(spec, fragments[spec.name]), encoding="utf-8", newline="\n")
        print(path)


if __name__ == "__main__":
    main()
