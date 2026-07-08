"""Build all derived brand assets from SVG masters at /home/kevin/Logo/.

Master SVG file naming (per user spec 2026-07-08):
  master logo icon white.svg
  master logo icon yellow.svg
  Master logo primary white.svg
  Master logo primary yellow.svg
  master logo secondary white.svg
  master logo secondary yellow.svg

Output: frontend/public/brand/master/*.png + frontend/public/brand/derived/*
  1024x512  primary-yellow.png / primary-white.png
  1024x256  secondary-yellow.png / secondary-white.png
  1024x1024 icon-yellow.png / icon-white.png

Then build favicon / PWA icons / OG from icon-yellow.

Brand colour (Optimism Yellow): #f5a700
Wordmark: "Teman UMKM Kita"
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

MASTER_DIR = Path("/home/kevin/Logo")
OUT_MASTER = Path("/home/kevin/kantorteman/frontend/public/brand/master")
OUT_DERIVED = Path("/home/kevin/kantorteman/frontend/public/brand/derived")

CANVAS_SIZES = {
    "primary":   (1024, 512),
    "secondary": (1024, 256),
    "icon":      (1024, 1024),
}

YELLOW_HEX = "#f5a700"
WHITE_HEX = "#fcfaf7"  # Snow

def write_master(svg_path: Path, png_path: Path, w: int, h: int) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(png_path),
        output_width=w,
        output_height=h,
        background_color=None,  # transparent
    )
    print(f"  master -> {png_path.relative_to(png_path.parents[3])} ({w}x{h})")


def write_derived_sizes(src_png: Path, out_dir: Path, sizes: list[tuple[str, int]]) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(src_png).convert("RGBA")
    written: dict[str, Path] = {}
    for label, size in sizes:
        if isinstance(size, tuple):
            w, h = size
        else:
            w, h = size, size
        resized = img.resize((w, h), Image.LANCZOS)
        out_path = out_dir / f"{label}.png"
        resized.save(out_path, optimize=True)
        written[label] = out_path
        print(f"  derived -> {out_path.name} ({w}x{h})")
    return written


def build_favicon(png192: Path, out_path: Path) -> None:
    """16+32+48 multi-icon .ico built from a single 1024 PNG."""
    img = Image.open(png192).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), format="ICO", sizes=sizes)
    print(f"  favicon -> {out_path.name}")


def build_og_image(icon_png: Path, out_path: Path) -> None:
    """OG 1200x630 with icon centred on yellow background + wordmark below."""
    W, H = 1200, 630
    bg_color = (245, 167, 0)  # optimism yellow
    img = Image.new("RGB", (W, H), bg_color)
    icon = Image.open(icon_png).convert("RGBA")
    # icon centred horizontally, ~ 60% of height
    icon_h = int(H * 0.55)
    icon_w = int(icon.width * icon_h / icon.height)
    icon = icon.resize((icon_w, icon_h), Image.LANCZOS)
    icon_x = (W - icon_w) // 2
    icon_y = int(H * 0.10)
    img.paste(icon, (icon_x, icon_y), icon)

    # wordmark below
    draw = ImageDraw.Draw(img)
    word = "Teman UMKM Kita"
    # Try a few font paths
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    fp = next((p for p in font_paths if os.path.exists(p)), None)
    if fp:
        font = ImageFont.truetype(fp, 64)
    else:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), word, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (W - text_w) // 2
    text_y = icon_y + icon_h + 16
    draw.text((text_x, text_y), word, fill=(252, 250, 247), font=font)  # Snow
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    print(f"  og -> {out_path.name} (1200x630)")


def main():
    OUT_MASTER.mkdir(parents=True, exist_ok=True)

    # 1. Render PNG masters from SVGs at exact canvas sizes
    print("== PNG masters ==")
    masters: dict[str, Path] = {}
    for variant_key, fname_lower in [
        ("primary-yellow",   "master logo primary yellow.svg"),
        ("primary-white",    "Master logo primary white.svg"),
        ("secondary-yellow", "master logo secondary yellow.svg"),
        ("secondary-white",  "master logo secondary white.svg"),
        ("icon-yellow",      "master logo icon yellow.svg"),
        ("icon-white",       "master logo icon white.svg"),
    ]:
        svg = None
        for p in MASTER_DIR.iterdir():
            if p.name.lower() == fname_lower.lower():
                svg = p; break
        if not svg:
            sys.exit(f"missing {fname_lower}")
        if "primary" in variant_key:
            w, h = CANVAS_SIZES["primary"]
        elif "secondary" in variant_key:
            w, h = CANVAS_SIZES["secondary"]
        else:
            w, h = CANVAS_SIZES["icon"]
        out = OUT_MASTER / f"{variant_key}.png"
        write_master(svg, out, w, h)
        masters[variant_key] = out

    # 2. Derived icon sizes (used for favicons + PWA icons)
    print("== Derived icon sizes ==")
    icon_yellow = masters["icon-yellow"]
    icon_sizes = [
        ("favicon-16", 16),
        ("favicon-32", 32),
        ("favicon-48", 48),
        ("icon-72", 72),
        ("icon-96", 96),
        ("icon-128", 128),
        ("icon-144", 144),
        ("icon-152", 152),
        ("icon-192", 192),
        ("icon-384", 384),
        ("icon-512", 512),
        ("apple-touch-icon", 180),
    ]
    written = write_derived_sizes(icon_yellow, OUT_DERIVED, icon_sizes)

    # 3. favicon.ico (16+32+48)
    print("== favicon.ico ==")
    build_favicon(written["icon-192"], OUT_DERIVED / "favicon.ico")

    # 4. OG image
    print("== og-image ==")
    build_og_image(written["icon-192"], OUT_DERIVED / "og-image.png")

    print("\nDONE")


if __name__ == "__main__":
    main()
