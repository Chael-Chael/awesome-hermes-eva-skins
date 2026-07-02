#!/usr/bin/env python3
"""Convert an image into Hermes/Rich colored braille hero art.

This follows the same core idea used by cocktailpeanut/hermes-mod: each
terminal character encodes a 2x4 pixel block using Unicode braille dots.  The
change here is that every emitted braille cell is wrapped in Rich foreground
markup based on the source image color for that cell.
"""

from __future__ import annotations

import argparse
import colorsys
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


BRAILLE_BLANK = "\u2800"
BRAILLE_BIT_GRID = (
    (0x01, 0x08),
    (0x02, 0x10),
    (0x04, 0x20),
    (0x40, 0x80),
)
QUADRANT_CHARS = {
    0b0000: " ",
    0b0001: "▘",
    0b0010: "▝",
    0b0011: "▀",
    0b0100: "▖",
    0b0101: "▌",
    0b0110: "▞",
    0b0111: "▛",
    0b1000: "▗",
    0b1001: "▚",
    0b1010: "▐",
    0b1011: "▜",
    0b1100: "▄",
    0b1101: "▙",
    0b1110: "▟",
    0b1111: "█",
}
QUADRANT_BRAILLE_CHARS = {
    0b0000: BRAILLE_BLANK,
    0b0001: chr(0x2800 + 0x01),
    0b0010: chr(0x2800 + 0x08),
    0b0011: chr(0x2800 + 0x01 + 0x08),
    0b0100: chr(0x2800 + 0x40),
    0b0101: chr(0x2800 + 0x01 + 0x40),
    0b0110: chr(0x2800 + 0x08 + 0x40),
    0b0111: chr(0x2800 + 0x01 + 0x08 + 0x40),
    0b1000: chr(0x2800 + 0x80),
    0b1001: chr(0x2800 + 0x01 + 0x80),
    0b1010: chr(0x2800 + 0x08 + 0x80),
    0b1011: chr(0x2800 + 0x01 + 0x08 + 0x80),
    0b1100: chr(0x2800 + 0x40 + 0x80),
    0b1101: chr(0x2800 + 0x01 + 0x40 + 0x80),
    0b1110: chr(0x2800 + 0x08 + 0x40 + 0x80),
    0b1111: chr(0x2800 + 0x01 + 0x08 + 0x40 + 0x80),
}
QUADRANT_TEXTURE_CHARS = {
    0b0000: BRAILLE_BLANK,
    0b0001: "⠂",
    0b0010: "⠂",
    0b0011: "⠆",
    0b0100: "⠂",
    0b0101: "⠆",
    0b0110: "⠆",
    0b0111: "⠇",
    0b1000: "⠂",
    0b1001: "⠆",
    0b1010: "⠆",
    0b1011: "⠇",
    0b1100: "⠆",
    0b1101: "⠇",
    0b1110: "⠇",
    0b1111: "⣿",
}
HERMESMOD_SHARPEN_KERNEL = ImageFilter.Kernel(
    (3, 3),
    (0, -1, 0, -1, 5, -1, 0, -1, 0),
    scale=1,
)


@dataclass(frozen=True)
class PixelSample:
    rgb: tuple[int, int, int]
    alpha: int
    darkness: float
    foreground: float


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def parse_hex_color(value: str) -> tuple[int, int, int]:
    text = value.strip()
    if text.lower() == "auto":
        raise ValueError("'auto' is not a concrete color")
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})", text)
    if not match:
        raise argparse.ArgumentTypeError(f"Expected #RRGGBB, got {value!r}")
    raw = match.group(1)
    return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def to_hex(rgb: Sequence[int]) -> str:
    r, g, b = (int(clamp(channel, 0, 255)) for channel in rgb[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def color_distance(a: Sequence[int], b: Sequence[int]) -> float:
    dr = int(a[0]) - int(b[0])
    dg = int(a[1]) - int(b[1])
    db = int(a[2]) - int(b[2])
    return (dr * dr + dg * dg + db * db) ** 0.5


def luminance(rgb: Sequence[int]) -> float:
    r, g, b = rgb[:3]
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def pixel_darkness(rgba: Sequence[int]) -> float:
    alpha = rgba[3] / 255.0
    return clamp((1.0 - luminance(rgba[:3])) * alpha, 0.0, 1.0)


def saturation(rgb: Sequence[int]) -> float:
    r, g, b = (channel / 255.0 for channel in rgb[:3])
    _, s, _ = colorsys.rgb_to_hsv(r, g, b)
    return s


def chroma(rgb: Sequence[int]) -> float:
    values = [int(channel) for channel in rgb[:3]]
    return (max(values) - min(values)) / 255.0


def has_transparency(image: Image.Image, alpha_threshold: int) -> bool:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    alpha = image.getchannel("A")
    min_alpha, max_alpha = alpha.getextrema()
    return min_alpha < min(alpha_threshold, max_alpha)


def detect_background_rgb(image: Image.Image) -> tuple[int, int, int]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    border: list[tuple[int, int, int]] = []

    for x in range(width):
        for y in (0, height - 1):
            r, g, b, a = pixels[x, y]
            if a:
                border.append((r, g, b))
    for y in range(height):
        for x in (0, width - 1):
            r, g, b, a = pixels[x, y]
            if a:
                border.append((r, g, b))

    if not border:
        return (0, 0, 0)
    return Counter(border).most_common(1)[0][0]


def flatten_background_to_white(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
) -> Image.Image:
    rgba = image.convert("RGBA")
    data: list[tuple[int, int, int, int]] = []

    for r, g, b, a in rgba.getdata():
        if a < alpha_threshold:
            data.append((255, 255, 255, 255))
            continue
        if background_rgb is not None and color_distance((r, g, b), background_rgb) <= background_tolerance:
            data.append((255, 255, 255, 255))
            continue
        data.append((r, g, b, a))

    output = Image.new("RGBA", rgba.size)
    output.putdata(data)
    return output


def find_content_bbox(
    image: Image.Image,
    *,
    mask_mode: str,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    luma_threshold: float,
) -> tuple[int, int, int, int] | None:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    xs: list[int] = []
    ys: list[int] = []

    for y in range(height):
        for x in range(width):
            sample = sample_pixel(
                pixels[x, y],
                mask_mode=mask_mode,
                background_rgb=background_rgb,
                background_tolerance=background_tolerance,
                alpha_threshold=alpha_threshold,
                luma_threshold=luma_threshold,
            )
            if sample.foreground > 0.0:
                xs.append(x)
                ys.append(y)

    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def sample_pixel(
    rgba: Sequence[int],
    *,
    mask_mode: str,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    luma_threshold: float,
) -> PixelSample:
    r, g, b, a = (int(value) for value in rgba)
    alpha_strength = clamp(a / 255.0, 0.0, 1.0)
    darkness = pixel_darkness((r, g, b, a))

    if a < alpha_threshold:
        foreground = 0.0
    elif mask_mode == "alpha":
        foreground = alpha_strength
    elif mask_mode == "luma":
        foreground = 1.0 if darkness >= luma_threshold else 0.0
    elif mask_mode == "background":
        if background_rgb is None:
            foreground = alpha_strength
        else:
            distance = color_distance((r, g, b), background_rgb)
            foreground = clamp(distance / max(1.0, background_tolerance), 0.0, 1.0)
    else:
        raise ValueError(f"Unsupported mask mode: {mask_mode}")

    return PixelSample(rgb=(r, g, b), alpha=a, darkness=darkness, foreground=foreground)


def adaptive_braille_threshold(cell_average_darkness: float) -> float:
    if cell_average_darkness >= 0.72:
        return 0.34
    if cell_average_darkness >= 0.48:
        return 0.42
    return 0.5


def preprocess_image(
    source: Image.Image,
    *,
    width: int,
    mask_mode: str,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    luma_threshold: float,
    autocrop: bool,
    sharpen: bool,
    contrast: float,
    palette_size: int | None,
) -> Image.Image:
    image = source.convert("RGBA")

    if autocrop:
        bbox = find_content_bbox(
            image,
            mask_mode=mask_mode,
            background_rgb=background_rgb,
            background_tolerance=background_tolerance,
            alpha_threshold=alpha_threshold,
            luma_threshold=luma_threshold,
        )
        if bbox:
            left, top, right, bottom = bbox
            left = max(0, left - 1)
            top = max(0, top - 1)
            right = min(image.width, right + 1)
            bottom = min(image.height, bottom + 1)
            image = image.crop((left, top, right, bottom))

    output_height = max(1, round((image.height / max(1, image.width)) * width * 0.5))
    pixel_width = max(1, width * 2)
    pixel_height = max(1, output_height * 4)
    image = image.resize((pixel_width, pixel_height), Image.Resampling.LANCZOS)

    if contrast:
        image = ImageEnhance.Contrast(image).enhance(max(0.0, 1.0 + contrast))

    if sharpen:
        image = image.filter(ImageFilter.SHARPEN)

    if palette_size and palette_size > 0:
        alpha = image.getchannel("A")
        quantized = image.convert("RGB").quantize(
            colors=max(2, palette_size),
            method=Image.Quantize.MEDIANCUT,
        )
        image = quantized.convert("RGBA")
        image.putalpha(alpha)

    return image


def resize_for_braille(
    image: Image.Image,
    width: int,
    *,
    resample: Image.Resampling = Image.Resampling.LANCZOS,
) -> Image.Image:
    output_height = max(1, round((image.height / max(1, image.width)) * width * 0.5))
    pixel_width = max(1, width * 2)
    pixel_height = max(1, output_height * 4)
    return image.resize((pixel_width, pixel_height), resample)


def resize_for_quadrant_blocks(
    image: Image.Image,
    width: int,
    *,
    resample: Image.Resampling = Image.Resampling.NEAREST,
) -> Image.Image:
    output_height = max(1, round((image.height / max(1, image.width)) * width * 0.5))
    pixel_width = max(1, width * 2)
    pixel_height = max(1, output_height * 2)
    return image.resize((pixel_width, pixel_height), resample)


def crop_to_background_content(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    padding: int = 1,
) -> Image.Image:
    if background_rgb is None:
        return image
    bbox = find_content_bbox(
        image,
        mask_mode="background",
        background_rgb=background_rgb,
        background_tolerance=background_tolerance,
        alpha_threshold=alpha_threshold,
        luma_threshold=0.5,
    )
    if not bbox:
        return image
    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)
    return image.crop((left, top, right, bottom))


def preprocess_hermesmod_layers(
    source: Image.Image,
    *,
    width: int,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    autocrop: bool,
    sharpen: bool,
    contrast: float,
    palette_size: int | None,
) -> tuple[Image.Image, Image.Image]:
    """Build separate layers: hermes-mod grayscale dots plus original colors."""
    color_image = source.convert("RGBA")

    if autocrop:
        bbox = find_content_bbox(
            color_image,
            mask_mode="background",
            background_rgb=background_rgb,
            background_tolerance=background_tolerance,
            alpha_threshold=alpha_threshold,
            luma_threshold=0.5,
        )
        if bbox:
            left, top, right, bottom = bbox
            left = max(0, left - 1)
            top = max(0, top - 1)
            right = min(color_image.width, right + 1)
            bottom = min(color_image.height, bottom + 1)
            color_image = color_image.crop((left, top, right, bottom))

    color_image = flatten_background_to_white(
        color_image,
        background_rgb=background_rgb,
        background_tolerance=background_tolerance,
        alpha_threshold=alpha_threshold,
    )
    color_image = resize_for_braille(color_image, width)

    dot_image = ImageOps.grayscale(color_image)
    dot_image = ImageOps.autocontrast(dot_image)

    if contrast:
        dot_image = ImageEnhance.Contrast(dot_image).enhance(max(0.0, 1.0 + contrast))

    if sharpen:
        dot_image = dot_image.filter(HERMESMOD_SHARPEN_KERNEL)

    dot_image = Image.merge("RGBA", (dot_image, dot_image, dot_image, color_image.getchannel("A")))

    if palette_size and palette_size > 0:
        alpha = color_image.getchannel("A")
        quantized = color_image.convert("RGB").quantize(
            colors=max(2, palette_size),
            method=Image.Quantize.MEDIANCUT,
        )
        color_image = quantized.convert("RGBA")
        color_image.putalpha(alpha)

    return dot_image, color_image


def preprocess_pixel_art_layer(
    source: Image.Image,
    *,
    width: int,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    autocrop: bool,
    palette_size: int | None,
) -> Image.Image:
    image = source.convert("RGBA")
    if autocrop:
        image = crop_to_background_content(
            image,
            background_rgb=background_rgb,
            background_tolerance=background_tolerance,
            alpha_threshold=alpha_threshold,
            padding=1,
        )

    image = resize_for_braille(image, width, resample=Image.Resampling.NEAREST)

    if palette_size and palette_size > 0:
        alpha = image.getchannel("A")
        quantized = image.convert("RGB").quantize(
            colors=max(2, palette_size),
            method=Image.Quantize.MEDIANCUT,
        )
        image = quantized.convert("RGBA")
        image.putalpha(alpha)

    return image


def preprocess_pixel_art_block_layer(
    source: Image.Image,
    *,
    width: int,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    autocrop: bool,
    palette_size: int | None,
) -> Image.Image:
    image = source.convert("RGBA")
    if autocrop:
        image = crop_to_background_content(
            image,
            background_rgb=background_rgb,
            background_tolerance=background_tolerance,
            alpha_threshold=alpha_threshold,
            padding=1,
        )

    image = resize_for_quadrant_blocks(image, width, resample=Image.Resampling.NEAREST)

    if palette_size and palette_size > 0:
        alpha = image.getchannel("A")
        quantized = image.convert("RGB").quantize(
            colors=max(2, palette_size),
            method=Image.Quantize.MEDIANCUT,
        )
        image = quantized.convert("RGBA")
        image.putalpha(alpha)

    return image


def average_color(samples: Iterable[PixelSample], fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    weighted = []
    for sample in samples:
        weight = max(sample.foreground, sample.darkness, sample.alpha / 255.0)
        if weight > 0:
            weighted.append((sample.rgb, weight))

    if not weighted:
        return fallback

    total = sum(weight for _, weight in weighted)
    channels = []
    for channel in range(3):
        value = sum(rgb[channel] * weight for rgb, weight in weighted) / total
        channels.append(round(value))
    return tuple(channels)  # type: ignore[return-value]


def dominant_color(samples: Iterable[PixelSample], fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    colors = [sample.rgb for sample in samples if sample.foreground > 0.0 or sample.darkness > 0.0]
    if not colors:
        return fallback
    return Counter(colors).most_common(1)[0][0]


def terminal_visible_color(rgb: Sequence[int]) -> tuple[int, int, int]:
    r, g, b = (channel / 255.0 for channel in rgb[:3])
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = clamp(max(s, 0.62) * 1.08, 0.0, 1.0)
    v = clamp(max(v, 0.78), 0.0, 1.0)
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    visible = (round(rr * 255), round(gg * 255), round(bb * 255))
    lum = luminance(visible)
    min_luminance = 0.54
    if lum >= min_luminance:
        return visible

    blend = clamp((min_luminance - lum) / max(0.001, 1.0 - lum), 0.0, 1.0)
    return tuple(round(channel + (255 - channel) * blend) for channel in visible)  # type: ignore[return-value]


def pixel_art_visible_color(rgb: Sequence[int]) -> tuple[int, int, int]:
    """Map colored pixel art with the current EVA terminal-lab source settings."""
    if is_pixel_art_blank_white(rgb):
        return (255, 255, 255)
    r, g, b = (channel / 255.0 for channel in rgb[:3])
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if is_pixel_art_neutral(rgb):
        return pixel_art_neutral_color(rgb)

    # Mirrors tools/eva-terminal-lab.html with:
    # satGain=2.15, satFloor=.72, valueMin=.51, valueMax=1,
    # valueGamma=1.24, sourceContrast=1.51, sourceExposure=-.13,
    # shadowCrush=.14, hueShift=1.
    h = (h + 1.0 / 360.0) % 1.0
    s = clamp(max(s, 0.72) * 2.15, 0.0, 1.0)
    v = clamp((v - 0.5) * 2.51 + 0.5 - 0.13, 0.0, 1.0)
    v = v**1.24
    v = 0.51 + v * (1.0 - 0.51)
    if v < 0.52:
        v *= 1.0 - 0.14 * (1.0 - v / 0.52)
    v = clamp(v, 0.0, 1.0)
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return (round(rr * 255), round(gg * 255), round(bb * 255))


def pixel_art_neutral_color(rgb: Sequence[int]) -> tuple[int, int, int]:
    """Keep white armor and gray shading distinct instead of collapsing them."""
    tint = (154, 166, 184)
    lum = luminance(rgb)
    level = clamp((0.14 + lum * 0.72) * 1.4, 0.0, 1.0)
    return tuple(round(channel * level) for channel in tint)  # type: ignore[return-value]


def is_pixel_art_neutral(rgb: Sequence[int]) -> bool:
    if is_pixel_art_blank_white(rgb):
        return False
    sat = saturation(rgb)
    lum = luminance(rgb)
    chr_value = chroma(rgb)
    r, g, b = (channel / 255.0 for channel in rgb[:3])
    hue, _, _ = colorsys.rgb_to_hsv(r, g, b)
    if sat <= 0.18:
        return True
    if chr_value <= 0.16 and lum >= 0.16:
        return True
    return chr_value <= 0.20 and sat <= 0.42 and 0.50 <= hue <= 0.76 and lum >= 0.18


def theme_aligned_pixel_color(rgb: Sequence[int]) -> tuple[int, int, int]:
    return tuple(int(channel) for channel in rgb[:3])  # type: ignore[return-value]


def is_uncolored_white_or_gray(rgb: Sequence[int]) -> bool:
    lum = luminance(rgb)
    sat = saturation(rgb)
    return sat < 0.16 or (lum > 0.86 and sat < 0.28)


def is_pixel_art_blank_white(rgb: Sequence[int]) -> bool:
    return luminance(rgb) > 0.80 and saturation(rgb) < 0.22


def is_pixel_art_ink(rgb: Sequence[int]) -> bool:
    if is_pixel_art_blank_white(rgb):
        return False
    lum = luminance(rgb)
    sat = saturation(rgb)
    max_channel = max(int(channel) for channel in rgb[:3]) / 255.0
    return max_channel < 0.16 or (lum <= 0.32 and sat <= 0.31)


def has_pixel_art_fill(rgb: Sequence[int]) -> bool:
    return not is_pixel_art_blank_white(rgb) and not is_pixel_art_ink(rgb) and not is_pixel_art_neutral(rgb)


def should_force_ink_color(outline_samples: int, active_pixels: int, active_samples: Sequence[PixelSample]) -> bool:
    if outline_samples <= 0:
        return False

    colored_samples = sum(1 for sample in active_samples if has_pixel_art_fill(sample.rgb))
    if colored_samples == 0:
        return True

    outline_ratio = outline_samples / max(1, active_pixels)
    return outline_samples >= 3 or (outline_samples >= 2 and outline_ratio >= 0.6)


def bright_local_color(
    color_pixels,
    *,
    width: int,
    height: int,
    x: int,
    y: int,
    alpha_threshold: int,
    fallback_color: tuple[int, int, int],
) -> tuple[int, int, int] | None:
    radius_x = 3
    radius_y = 5
    weighted: list[tuple[tuple[int, int, int], float]] = []

    left = max(0, x - radius_x)
    top = max(0, y - radius_y)
    right = min(width, x + 2 + radius_x)
    bottom = min(height, y + 4 + radius_y)

    for sample_y in range(top, bottom):
        for sample_x in range(left, right):
            r, g, b, a = (int(value) for value in color_pixels[sample_x, sample_y])
            if a < alpha_threshold:
                continue
            rgb = (r, g, b)
            lum = luminance(rgb)
            sat = saturation(rgb)
            if is_uncolored_white_or_gray(rgb):
                continue
            if lum < 0.05:
                continue
            distance = abs(sample_x - (x + 0.5)) + abs(sample_y - (y + 1.5))
            weight = (sat ** 1.4) * (0.4 + lum) / (1.0 + distance * 0.18)
            if weight > 0:
                weighted.append((rgb, weight))

    if not weighted:
        return None

    total = sum(weight for _, weight in weighted)
    channels = []
    for channel in range(3):
        value = sum(rgb[channel] * weight for rgb, weight in weighted) / total
        channels.append(round(value))

    rgb = tuple(channels)  # type: ignore[assignment]
    if is_uncolored_white_or_gray(rgb):
        return None
    return terminal_visible_color(rgb or fallback_color)


def pixel_art_cell_color(
    active_samples: Sequence[PixelSample],
    fallback_color: tuple[int, int, int],
    ink_color: tuple[int, int, int],
    neutral_color: tuple[int, int, int],
) -> tuple[int, int, int] | None:
    colored: list[tuple[tuple[int, int, int], float]] = []
    neutral: list[tuple[tuple[int, int, int], float]] = []
    has_ink = False

    for sample in active_samples:
        rgb = sample.rgb
        lum = luminance(rgb)
        sat = saturation(rgb)
        if is_pixel_art_blank_white(rgb):
            continue
        if is_pixel_art_ink(rgb):
            has_ink = True
            continue
        if is_pixel_art_neutral(rgb):
            if lum < 0.78:
                neutral.append((rgb, 0.35 + (1.0 - abs(lum - 0.45))))
            continue
        weight = (sat ** 1.25) * (0.35 + lum)
        if weight > 0:
            colored.append((rgb, weight))

    if not colored:
        if has_ink:
            return ink_color
        if neutral:
            return neutral_color
        return None

    total = sum(weight for _, weight in colored)
    channels = []
    for channel in range(3):
        value = sum(rgb[channel] * weight for rgb, weight in colored) / total
        channels.append(round(value))

    rgb = tuple(channels)  # type: ignore[assignment]
    if is_uncolored_white_or_gray(rgb):
        if has_ink:
            return ink_color
        if neutral:
            return neutral_color
        return None
    return pixel_art_visible_color(rgb or fallback_color)


def build_pixel_art_masks(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    outline_radius: int,
) -> tuple[list[list[bool]], list[list[bool]]]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    foreground = [[False for _ in range(width)] for _ in range(height)]
    outline_seed = [[False for _ in range(width)] for _ in range(height)]

    for y in range(height):
        for x in range(width):
            sample = sample_pixel(
                pixels[x, y],
                mask_mode="background",
                background_rgb=background_rgb,
                background_tolerance=background_tolerance,
                alpha_threshold=alpha_threshold,
                luma_threshold=0.5,
            )
            active = sample.foreground >= 0.5 and not is_pixel_art_blank_white(sample.rgb)
            foreground[y][x] = active
            if active and is_pixel_art_ink(sample.rgb):
                outline_seed[y][x] = True

    outline = [[False for _ in range(width)] for _ in range(height)]
    radius = max(0, outline_radius)
    if radius == 0:
        return foreground, outline_seed

    for y in range(height):
        for x in range(width):
            if not outline_seed[y][x]:
                continue
            for oy in range(-radius, radius + 1):
                for ox in range(-radius, radius + 1):
                    if abs(ox) + abs(oy) > radius:
                        continue
                    tx = x + ox
                    ty = y + oy
                    if 0 <= tx < width and 0 <= ty < height:
                        outline[ty][tx] = True

    return foreground, outline


def render_pixel_art_braille(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    min_cell_coverage: float,
    outline_radius: int,
    ink_color: tuple[int, int, int],
    neutral_color: tuple[int, int, int],
    fallback_color: tuple[int, int, int],
    bold: bool,
) -> str:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    foreground_mask, outline_mask = build_pixel_art_masks(
        rgba,
        background_rgb=background_rgb,
        background_tolerance=background_tolerance,
        alpha_threshold=alpha_threshold,
        outline_radius=outline_radius,
    )
    lines: list[str] = []

    for y in range(0, rgba.height, 4):
        cells: list[tuple[str, str | None]] = []
        for x in range(0, rgba.width, 2):
            bits = 0
            samples = 0
            active_pixels = 0
            active_samples: list[PixelSample] = []
            outline_samples = 0

            for dy in range(4):
                for dx in range(2):
                    sample_x = x + dx
                    sample_y = y + dy
                    if sample_x >= rgba.width or sample_y >= rgba.height:
                        continue
                    samples += 1
                    is_foreground = foreground_mask[sample_y][sample_x]
                    is_outline = outline_mask[sample_y][sample_x]
                    if is_foreground or is_outline:
                        active_pixels += 1
                        bits |= BRAILLE_BIT_GRID[dy][dx]
                        if is_outline:
                            outline_samples += 1
                        if is_foreground:
                            sample = sample_pixel(
                                pixels[sample_x, sample_y],
                                mask_mode="background",
                                background_rgb=background_rgb,
                                background_tolerance=background_tolerance,
                                alpha_threshold=alpha_threshold,
                                luma_threshold=0.5,
                            )
                            active_samples.append(sample)

            if not bits or active_pixels / max(1, samples) < min_cell_coverage:
                cells.append((BRAILLE_BLANK, None))
                continue

            if should_force_ink_color(outline_samples, active_pixels, active_samples):
                rgb = ink_color
            else:
                rgb = pixel_art_cell_color(active_samples, fallback_color, ink_color, neutral_color)
            if rgb is None:
                color = None
            else:
                color = to_hex(rgb)
            cells.append((chr(0x2800 + bits), color))

        while cells and cells[-1] == (BRAILLE_BLANK, None):
            cells.pop()
        lines.append(markup_cells(cells, bold=bold))

    return trim_blank_lines("\n".join(lines))


def render_pixel_art_quadrant_blocks(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    min_cell_coverage: float,
    ink_color: tuple[int, int, int],
    neutral_color: tuple[int, int, int],
    fallback_color: tuple[int, int, int],
    blank_white: bool = True,
    bold: bool,
) -> str:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    lines: list[str] = []

    for y in range(0, rgba.height, 2):
        cells: list[tuple[str, str | None, str | None]] = []
        for x in range(0, rgba.width, 2):
            samples: list[PixelSample | None] = []
            bits = 0

            for index, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
                sample_x = x + dx
                sample_y = y + dy
                if sample_x >= rgba.width or sample_y >= rgba.height:
                    samples.append(None)
                    continue
                sample = sample_pixel(
                    pixels[sample_x, sample_y],
                    mask_mode="background",
                    background_rgb=background_rgb,
                    background_tolerance=background_tolerance,
                    alpha_threshold=alpha_threshold,
                    luma_threshold=0.5,
                )
                active = sample.foreground >= 0.5 and not (blank_white and is_pixel_art_blank_white(sample.rgb))
                if active:
                    bits |= 1 << index
                    samples.append(sample)
                else:
                    samples.append(None)

            active_samples = [sample for sample in samples if sample is not None]
            if not bits or len(active_samples) / 4 < min_cell_coverage:
                cells.append((" ", None, None))
                continue

            colors: list[tuple[int, int, int] | None] = []
            for sample in samples:
                if sample is None:
                    colors.append(None)
                elif is_pixel_art_ink(sample.rgb):
                    colors.append(ink_color)
                elif is_pixel_art_neutral(sample.rgb):
                    colors.append(pixel_art_neutral_color(sample.rgb))
                else:
                    colors.append(pixel_art_visible_color(sample.rgb or fallback_color))

            active_colors = [color for color in colors if color is not None]
            if not active_colors:
                cells.append((" ", None, None))
                continue

            top = [colors[0], colors[1]]
            bottom = [colors[2], colors[3]]
            left = [colors[0], colors[2]]
            right = [colors[1], colors[3]]

            def mean_color(values: Sequence[tuple[int, int, int] | None]) -> tuple[int, int, int] | None:
                present = [value for value in values if value is not None]
                if not present:
                    return None
                return tuple(round(sum(value[channel] for value in present) / len(present)) for channel in range(3))

            fg: tuple[int, int, int] | None
            bg: tuple[int, int, int] | None = None
            char = QUADRANT_CHARS[bits]

            if bits == 0b1111:
                top_color = mean_color(top)
                bottom_color = mean_color(bottom)
                left_color = mean_color(left)
                right_color = mean_color(right)
                top_bottom_distance = color_distance(top_color, bottom_color) if top_color and bottom_color else 0
                left_right_distance = color_distance(left_color, right_color) if left_color and right_color else 0
                if top_color and bottom_color and top_bottom_distance >= max(24, left_right_distance):
                    char = "▀"
                    fg = theme_aligned_pixel_color(top_color)
                    bg = theme_aligned_pixel_color(bottom_color)
                elif left_color and right_color and left_right_distance >= 24:
                    char = "▌"
                    fg = theme_aligned_pixel_color(left_color)
                    bg = theme_aligned_pixel_color(right_color)
                else:
                    mixed = mean_color(active_colors)
                    fg = theme_aligned_pixel_color(mixed) if mixed else None
            else:
                mixed = mean_color(active_colors)
                fg = theme_aligned_pixel_color(mixed) if mixed else None

            cells.append((char, to_hex(fg) if fg else None, to_hex(bg) if bg else None))

        while cells and cells[-1] == (" ", None, None):
            cells.pop()
        lines.append(markup_block_cells(cells, bold=bold))

    return trim_blank_lines("\n".join(lines))


def render_pixel_art_full_blocks(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    min_cell_coverage: float,
    ink_color: tuple[int, int, int],
    neutral_color: tuple[int, int, int],
    fallback_color: tuple[int, int, int],
    blank_white: bool = True,
    bold: bool,
) -> str:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    lines: list[str] = []

    for y in range(rgba.height):
        cells: list[tuple[str, str | None]] = []
        for x in range(rgba.width):
            sample = sample_pixel(
                pixels[x, y],
                mask_mode="background",
                background_rgb=background_rgb,
                background_tolerance=background_tolerance,
                alpha_threshold=alpha_threshold,
                luma_threshold=0.5,
            )
            active = sample.foreground >= 0.5 and not (blank_white and is_pixel_art_blank_white(sample.rgb))
            if not active or min_cell_coverage > 1.0:
                cells.append((" ", None))
                continue

            if is_pixel_art_ink(sample.rgb):
                rgb = ink_color
            elif is_pixel_art_neutral(sample.rgb):
                rgb = pixel_art_neutral_color(sample.rgb)
            else:
                rgb = pixel_art_visible_color(sample.rgb or fallback_color)
            cells.append(("█", to_hex(rgb)))

        while cells and cells[-1] == (" ", None):
            cells.pop()
        lines.append(markup_cells(cells, bold=bold))

    return trim_blank_lines("\n".join(lines))


def render_pixel_art_dotted_quadrants(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    min_cell_coverage: float,
    ink_color: tuple[int, int, int],
    neutral_color: tuple[int, int, int],
    fallback_color: tuple[int, int, int],
    bold: bool,
) -> str:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    lines: list[str] = []

    for y in range(0, rgba.height, 2):
        cells: list[tuple[str, str | None]] = []
        for x in range(0, rgba.width, 2):
            samples: list[PixelSample] = []
            bits = 0
            outline_samples = 0

            for index, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
                sample_x = x + dx
                sample_y = y + dy
                if sample_x >= rgba.width or sample_y >= rgba.height:
                    continue
                sample = sample_pixel(
                    pixels[sample_x, sample_y],
                    mask_mode="background",
                    background_rgb=background_rgb,
                    background_tolerance=background_tolerance,
                    alpha_threshold=alpha_threshold,
                    luma_threshold=0.5,
                )
                active = sample.foreground >= 0.5 and not is_pixel_art_blank_white(sample.rgb)
                if not active:
                    continue
                bits |= 1 << index
                samples.append(sample)
                if is_pixel_art_ink(sample.rgb):
                    outline_samples += 1

            if not bits or len(samples) / 4 < min_cell_coverage:
                cells.append((BRAILLE_BLANK, None))
                continue

            if should_force_ink_color(outline_samples, len(samples), samples):
                rgb = ink_color
            else:
                rgb = pixel_art_cell_color(samples, fallback_color, ink_color, neutral_color)
            cells.append((QUADRANT_BRAILLE_CHARS[bits], to_hex(rgb) if rgb else None))

        while cells and cells[-1] == (BRAILLE_BLANK, None):
            cells.pop()
        lines.append(markup_cells(cells, bold=bold))

    return trim_blank_lines("\n".join(lines))


def render_pixel_art_textured_quadrants(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    min_cell_coverage: float,
    ink_color: tuple[int, int, int],
    neutral_color: tuple[int, int, int],
    fallback_color: tuple[int, int, int],
    bold: bool,
) -> str:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    lines: list[str] = []

    for y in range(0, rgba.height, 2):
        cells: list[tuple[str, str | None]] = []
        for x in range(0, rgba.width, 2):
            samples: list[PixelSample] = []
            bits = 0
            outline_samples = 0

            for index, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
                sample_x = x + dx
                sample_y = y + dy
                if sample_x >= rgba.width or sample_y >= rgba.height:
                    continue
                sample = sample_pixel(
                    pixels[sample_x, sample_y],
                    mask_mode="background",
                    background_rgb=background_rgb,
                    background_tolerance=background_tolerance,
                    alpha_threshold=alpha_threshold,
                    luma_threshold=0.5,
                )
                active = sample.foreground >= 0.5 and not is_pixel_art_blank_white(sample.rgb)
                if not active:
                    continue
                bits |= 1 << index
                samples.append(sample)
                if is_pixel_art_ink(sample.rgb):
                    outline_samples += 1

            if not bits or len(samples) / 4 < min_cell_coverage:
                cells.append((BRAILLE_BLANK, None))
                continue

            if should_force_ink_color(outline_samples, len(samples), samples):
                rgb = ink_color
            else:
                rgb = pixel_art_cell_color(samples, fallback_color, ink_color, neutral_color)
            cells.append((QUADRANT_TEXTURE_CHARS[bits], to_hex(rgb) if rgb else None))

        while cells and cells[-1] == (BRAILLE_BLANK, None):
            cells.pop()
        lines.append(markup_cells(cells, bold=bold))

    return trim_blank_lines("\n".join(lines))


def render_hermesmod_colored_braille(
    dot_image: Image.Image,
    color_image: Image.Image,
    *,
    alpha_threshold: int,
    min_cell_coverage: float,
    color_strategy: str,
    fallback_color: tuple[int, int, int],
    bold: bool,
) -> str:
    dots = dot_image.convert("RGBA")
    colors = color_image.convert("RGBA")
    if dots.size != colors.size:
        colors = colors.resize(dots.size, Image.Resampling.LANCZOS)

    dot_pixels = dots.load()
    color_pixels = colors.load()
    lines: list[str] = []

    for y in range(0, dots.height, 4):
        cells: list[tuple[str, str | None]] = []
        for x in range(0, dots.width, 2):
            bits = 0
            samples: list[PixelSample] = []
            active_color_samples: list[PixelSample] = []
            darkness_total = 0.0

            for dy in range(4):
                for dx in range(2):
                    sample_x = x + dx
                    sample_y = y + dy
                    if sample_x >= dots.width or sample_y >= dots.height:
                        continue
                    dot_sample = sample_pixel(
                        dot_pixels[sample_x, sample_y],
                        mask_mode="luma",
                        background_rgb=None,
                        background_tolerance=1.0,
                        alpha_threshold=alpha_threshold,
                        luma_threshold=0.5,
                    )
                    color_sample = sample_pixel(
                        color_pixels[sample_x, sample_y],
                        mask_mode="alpha",
                        background_rgb=None,
                        background_tolerance=1.0,
                        alpha_threshold=alpha_threshold,
                        luma_threshold=0.5,
                    )
                    samples.append(color_sample)
                    darkness_total += dot_sample.darkness

            if not samples:
                cells.append((BRAILLE_BLANK, None))
                continue

            cell_average_darkness = darkness_total / len(samples)
            if cell_average_darkness < 0.04:
                cells.append((BRAILLE_BLANK, None))
                continue

            threshold = adaptive_braille_threshold(cell_average_darkness)

            for dy in range(4):
                for dx in range(2):
                    sample_x = x + dx
                    sample_y = y + dy
                    if sample_x >= dots.width or sample_y >= dots.height:
                        continue
                    dot_sample = sample_pixel(
                        dot_pixels[sample_x, sample_y],
                        mask_mode="luma",
                        background_rgb=None,
                        background_tolerance=1.0,
                        alpha_threshold=alpha_threshold,
                        luma_threshold=0.5,
                    )
                    if dot_sample.darkness >= threshold:
                        bits |= BRAILLE_BIT_GRID[dy][dx]
                        color_sample = sample_pixel(
                            color_pixels[sample_x, sample_y],
                            mask_mode="alpha",
                            background_rgb=None,
                            background_tolerance=1.0,
                            alpha_threshold=alpha_threshold,
                            luma_threshold=0.5,
                        )
                        active_color_samples.append(color_sample)

            if not bits or len(active_color_samples) / max(1, len(samples)) < min_cell_coverage:
                cells.append((BRAILLE_BLANK, None))
                continue

            if color_strategy == "dominant":
                rgb = dominant_color(active_color_samples, fallback_color)
                color = to_hex(terminal_visible_color(rgb)) if not is_uncolored_white_or_gray(rgb) else None
            elif color_strategy == "bright-local":
                rgb = bright_local_color(
                    color_pixels,
                    width=colors.width,
                    height=colors.height,
                    x=x,
                    y=y,
                    alpha_threshold=alpha_threshold,
                    fallback_color=fallback_color,
                )
                color = to_hex(rgb) if rgb is not None else None
            else:
                rgb = average_color(active_color_samples, fallback_color)
                color = to_hex(terminal_visible_color(rgb)) if not is_uncolored_white_or_gray(rgb) else None
            cells.append((chr(0x2800 + bits), color))

        while cells and cells[-1] == (BRAILLE_BLANK, None):
            cells.pop()
        lines.append(markup_cells(cells, bold=bold))

    return trim_blank_lines("\n".join(lines))


def render_colored_braille(
    image: Image.Image,
    *,
    mask_mode: str,
    background_rgb: tuple[int, int, int] | None,
    background_tolerance: float,
    alpha_threshold: int,
    luma_threshold: float,
    min_cell_coverage: float,
    color_strategy: str,
    fallback_color: tuple[int, int, int],
    bold: bool,
) -> str:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    lines: list[str] = []

    for y in range(0, rgba.height, 4):
        cells: list[tuple[str, str | None]] = []
        for x in range(0, rgba.width, 2):
            bits = 0
            samples: list[PixelSample] = []
            active_samples: list[PixelSample] = []
            darkness_total = 0.0

            for dy in range(4):
                for dx in range(2):
                    sample_x = x + dx
                    sample_y = y + dy
                    if sample_x >= rgba.width or sample_y >= rgba.height:
                        continue
                    sample = sample_pixel(
                        pixels[sample_x, sample_y],
                        mask_mode=mask_mode,
                        background_rgb=background_rgb,
                        background_tolerance=background_tolerance,
                        alpha_threshold=alpha_threshold,
                        luma_threshold=luma_threshold,
                    )
                    samples.append(sample)
                    darkness_total += sample.darkness

            if not samples:
                cells.append((BRAILLE_BLANK, None))
                continue

            if mask_mode == "luma":
                cell_average_darkness = darkness_total / len(samples)
                if cell_average_darkness < 0.04:
                    cells.append((BRAILLE_BLANK, None))
                    continue
                threshold = adaptive_braille_threshold(cell_average_darkness)
            else:
                threshold = 0.5

            for dy in range(4):
                for dx in range(2):
                    sample_x = x + dx
                    sample_y = y + dy
                    if sample_x >= rgba.width or sample_y >= rgba.height:
                        continue
                    sample = sample_pixel(
                        pixels[sample_x, sample_y],
                        mask_mode=mask_mode,
                        background_rgb=background_rgb,
                        background_tolerance=background_tolerance,
                        alpha_threshold=alpha_threshold,
                        luma_threshold=luma_threshold,
                    )
                    is_active = sample.darkness >= threshold if mask_mode == "luma" else sample.foreground >= threshold
                    if is_active:
                        bits |= BRAILLE_BIT_GRID[dy][dx]
                        active_samples.append(sample)

            if not bits or len(active_samples) / max(1, len(samples)) < min_cell_coverage:
                cells.append((BRAILLE_BLANK, None))
                continue

            if color_strategy == "dominant":
                rgb = dominant_color(active_samples, fallback_color)
            else:
                rgb = average_color(active_samples, fallback_color)
            cells.append((chr(0x2800 + bits), to_hex(rgb)))

        while cells and cells[-1] == (BRAILLE_BLANK, None):
            cells.pop()
        lines.append(markup_cells(cells, bold=bold))

    return trim_blank_lines("\n".join(lines))


def markup_cells(cells: Sequence[tuple[str, str | None]], *, bold: bool) -> str:
    parts: list[str] = []
    active_color: str | None = None
    active_text: list[str] = []

    def flush() -> None:
        nonlocal active_color, active_text
        if not active_text:
            return
        text = "".join(active_text)
        if active_color:
            style = f"bold {active_color}" if bold else active_color
            parts.append(f"[{style}]{text}[/]")
        else:
            parts.append(text)
        active_color = None
        active_text = []

    for char, color in cells:
        if color != active_color:
            flush()
            active_color = color
        active_text.append(char)
    flush()
    return "".join(parts)


def markup_block_cells(cells: Sequence[tuple[str, str | None, str | None]], *, bold: bool) -> str:
    parts: list[str] = []
    active_fg: str | None = None
    active_bg: str | None = None
    active_text: list[str] = []

    def flush() -> None:
        nonlocal active_fg, active_bg, active_text
        if not active_text:
            return
        text = "".join(active_text)
        if active_fg or active_bg:
            prefix = "bold " if bold else ""
            if active_fg and active_bg:
                style = f"{prefix}{active_fg} on {active_bg}"
            elif active_fg:
                style = f"{prefix}{active_fg}"
            else:
                style = f"{prefix}on {active_bg}"
            parts.append(f"[{style}]{text}[/]")
        else:
            parts.append(text)
        active_fg = None
        active_bg = None
        active_text = []

    for char, fg, bg in cells:
        if fg != active_fg or bg != active_bg:
            flush()
            active_fg = fg
            active_bg = bg
        active_text.append(char)
    flush()
    return "".join(parts)


def trim_blank_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not strip_markup(lines[0]).strip(BRAILLE_BLANK + " "):
        lines.pop(0)
    while lines and not strip_markup(lines[-1]).strip(BRAILLE_BLANK + " "):
        lines.pop()
    return "\n".join(lines)


def strip_markup(text: str) -> str:
    return re.sub(r"\[[^\]]*\]", "", text).replace("[/]", "")


def yaml_block(key: str, value: str, indent: int = 2) -> str:
    pad = " " * indent
    if not value:
        return f"{key}: \"\""
    lines = value.splitlines()
    return f"{key}: |{indent}-\n" + "\n".join(f"{pad}{line}" for line in lines)


def choose_frame(image: Image.Image, frame: int) -> Image.Image:
    try:
        image.seek(frame)
    except EOFError as exc:
        raise SystemExit(f"Frame {frame} does not exist in {image.filename!r}") from exc
    return image.copy()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an image into colored Rich-markup braille art for Hermes banner_hero.",
    )
    parser.add_argument("image", type=Path, help="Input PNG, JPG, GIF, or WEBP image")
    parser.add_argument("-o", "--output", type=Path, help="Output text file. Defaults to stdout.")
    parser.add_argument("--width", type=int, default=40, help="Output width in braille characters")
    parser.add_argument("--frame", type=int, default=0, help="GIF frame index to render")
    parser.add_argument(
        "--format",
        choices=("raw", "yaml"),
        default="yaml",
        help="Output raw Rich markup or a YAML block.",
    )
    parser.add_argument("--yaml-key", default="banner_hero", help="YAML key used with --format yaml")
    parser.add_argument(
        "--dot-mode",
        choices=("hermesmod", "pixel-art", "mask"),
        default="hermesmod",
        help="Use hermes-mod grayscale dots, pixel-art foreground dots, or the older mask-based colored dots.",
    )
    parser.add_argument(
        "--mask-mode",
        choices=("auto", "alpha", "background", "luma"),
        default="auto",
        help="How foreground dots are detected.",
    )
    parser.add_argument(
        "--bg-color",
        default="auto",
        help="Background color for background mask mode. Use auto or #RRGGBB.",
    )
    parser.add_argument("--bg-tolerance", type=float, default=30.0, help="Foreground distance from background color")
    parser.add_argument("--alpha-threshold", type=int, default=12, help="Pixels below this alpha are transparent")
    parser.add_argument("--luma-threshold", type=float, default=0.5, help="Darkness threshold for luma mask mode")
    parser.add_argument("--min-cell-coverage", type=float, default=0.05, help="Drop very sparse braille cells")
    parser.add_argument(
        "--outline-radius",
        type=int,
        default=0,
        help="Pixel-art mode only: dilate detected outlines by this many source pixels.",
    )
    parser.add_argument(
        "--ink-color",
        type=parse_hex_color,
        default=parse_hex_color("#2a3038"),
        help="Pixel-art mode only: visible color used for dark ink/outline cells.",
    )
    parser.add_argument(
        "--neutral-color",
        type=parse_hex_color,
        default=parse_hex_color("#8f98a8"),
        help="Pixel-art mode only: visible color used for gray non-color detail cells.",
    )
    parser.add_argument("--no-autocrop", action="store_true", help="Disable automatic crop to foreground")
    parser.add_argument("--no-sharpen", action="store_true", help="Disable sharpening")
    parser.add_argument("--contrast", type=float, default=0.18, help="Contrast boost; 0 disables it")
    parser.add_argument(
        "--palette-size",
        type=int,
        default=32,
        help="Quantize colors to this many colors. Use 0 for exact resized colors.",
    )
    parser.add_argument(
        "--color-strategy",
        choices=("average", "dominant", "bright-local"),
        default="bright-local",
        help="How to choose one color for each 2x4 braille cell.",
    )
    parser.add_argument(
        "--fallback-color",
        type=parse_hex_color,
        default=parse_hex_color("#ffffff"),
        help="Fallback #RRGGBB",
    )
    parser.add_argument("--bold", action="store_true", help="Wrap colored runs in bold Rich style")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.width < 1:
        raise SystemExit("--width must be positive")
    if args.palette_size < 0:
        raise SystemExit("--palette-size must be 0 or positive")
    if args.outline_radius < 0:
        raise SystemExit("--outline-radius must be 0 or positive")

    source = Image.open(args.image)
    source = choose_frame(source, args.frame)

    background_rgb: tuple[int, int, int] | None
    if args.bg_color == "auto":
        background_rgb = detect_background_rgb(source)
    else:
        background_rgb = parse_hex_color(args.bg_color)

    if args.mask_mode == "auto":
        mask_mode = "alpha" if has_transparency(source, args.alpha_threshold) else "background"
    else:
        mask_mode = args.mask_mode

    if args.dot_mode == "hermesmod":
        dot_image, color_image = preprocess_hermesmod_layers(
            source,
            width=args.width,
            background_rgb=background_rgb,
            background_tolerance=args.bg_tolerance,
            alpha_threshold=args.alpha_threshold,
            autocrop=not args.no_autocrop,
            sharpen=not args.no_sharpen,
            contrast=args.contrast,
            palette_size=args.palette_size or None,
        )
        rich_text = render_hermesmod_colored_braille(
            dot_image,
            color_image,
            alpha_threshold=args.alpha_threshold,
            min_cell_coverage=args.min_cell_coverage,
            color_strategy=args.color_strategy,
            fallback_color=args.fallback_color,
            bold=args.bold,
        )
    elif args.dot_mode == "pixel-art":
        processed = preprocess_pixel_art_layer(
            source,
            width=args.width,
            background_rgb=background_rgb,
            background_tolerance=args.bg_tolerance,
            alpha_threshold=args.alpha_threshold,
            autocrop=not args.no_autocrop,
            palette_size=args.palette_size or None,
        )
        rich_text = render_pixel_art_braille(
            processed,
            background_rgb=background_rgb,
            background_tolerance=args.bg_tolerance,
            alpha_threshold=args.alpha_threshold,
            min_cell_coverage=args.min_cell_coverage,
            outline_radius=args.outline_radius,
            ink_color=args.ink_color,
            neutral_color=args.neutral_color,
            fallback_color=args.fallback_color,
            bold=args.bold,
        )
    else:
        processed = preprocess_image(
            source,
            width=args.width,
            mask_mode=mask_mode,
            background_rgb=background_rgb,
            background_tolerance=args.bg_tolerance,
            alpha_threshold=args.alpha_threshold,
            luma_threshold=args.luma_threshold,
            autocrop=not args.no_autocrop,
            sharpen=not args.no_sharpen,
            contrast=args.contrast,
            palette_size=args.palette_size or None,
        )
        rich_text = render_colored_braille(
            processed,
            mask_mode=mask_mode,
            background_rgb=background_rgb,
            background_tolerance=args.bg_tolerance,
            alpha_threshold=args.alpha_threshold,
            luma_threshold=args.luma_threshold,
            min_cell_coverage=args.min_cell_coverage,
            color_strategy=args.color_strategy,
            fallback_color=args.fallback_color,
            bold=args.bold,
        )

    result = yaml_block(args.yaml_key, rich_text) if args.format == "yaml" else rich_text
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(result + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
