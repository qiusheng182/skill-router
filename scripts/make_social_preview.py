#!/usr/bin/env python3
"""Generate the GitHub social preview image for skill-router."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 640
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "social-preview.png"

BACKGROUND = "#0B1220"
PANEL = "#111C31"
INK = "#F7FAFC"
MUTED = "#A7B4C8"
TEAL = "#38D39F"
BLUE = "#5CA8FF"
AMBER = "#F4C95D"
CORAL = "#FF6B6B"
LINE = "#23324D"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = Path("C:/Windows/Fonts") / name
    return ImageFont.truetype(str(path), size=size)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: str) -> None:
    draw.rounded_rectangle(box, radius=18, fill=color)


def chip(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fill: str,
    text_fill: str = INK,
) -> None:
    x, y = xy
    fnt = font("segoeui.ttf", 22)
    width = int(draw.textlength(text, font=fnt)) + 34
    draw.rounded_rectangle((x, y, x + width, y + 44), radius=12, fill=fill)
    draw.text((x + 17, y + 9), text, fill=text_fill, font=fnt)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line((start, end), fill=LINE, width=4)
    x, y = end
    if end[0] >= start[0]:
        draw.polygon([(x, y), (x - 12, y - 7), (x - 12, y + 7)], fill=LINE)
    else:
        draw.polygon([(x, y), (x + 12, y - 7), (x + 12, y + 7)], fill=LINE)


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    for x in range(0, WIDTH, 40):
        draw.line((x, 0, x, HEIGHT), fill="#0F192B", width=1)
    for y in range(0, HEIGHT, 40):
        draw.line((0, y, WIDTH, y), fill="#0F192B", width=1)

    rounded(draw, (64, 56, 1216, 584), PANEL)
    draw.rectangle((64, 56, 72, 584), fill=TEAL)

    draw.text((112, 98), "Skill Router", fill=INK, font=font("seguisb.ttf", 76))
    draw.text(
        (116, 190),
        "Keep agent skills out of every prompt.",
        fill=MUTED,
        font=font("segoeui.ttf", 34),
    )

    chip(draw, (116, 258), "clarify first", TEAL, BACKGROUND)
    chip(draw, (282, 258), "focused scan", BLUE, BACKGROUND)
    chip(draw, (456, 258), "context on demand", AMBER, BACKGROUND)
    chip(draw, (691, 258), "tested evolution", CORAL, BACKGROUND)

    left = (116, 362, 594, 500)
    right = (686, 338, 1164, 520)
    rounded(draw, left, "#0D1729")
    rounded(draw, right, "#0D1729")

    draw.text((146, 388), "Before", fill=MUTED, font=font("seguisb.ttf", 24))
    for idx, text in enumerate(("skills 001-046", "skills 047-092", "skills 093-138")):
        chip(draw, (146 + idx * 4, 430 + idx * 12), text, "#1E2C45", MUTED)

    draw.text((716, 366), "After", fill=MUTED, font=font("seguisb.ttf", 24))
    chip(draw, (716, 405), "one router", TEAL, BACKGROUND)
    arrow(draw, (856, 427), (918, 427))
    chip(draw, (930, 405), "context pack", BLUE, BACKGROUND)
    draw.text(
        (716, 466),
        "task-scoped docs + experience + validation",
        fill=INK,
        font=font("segoeui.ttf", 20),
    )

    draw.text(
        (116, 536),
        "github.com/qiusheng182/skill-router",
        fill=MUTED,
        font=font("consola.ttf", 24),
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, quality=95)
    print(OUTPUT)


if __name__ == "__main__":
    main()
