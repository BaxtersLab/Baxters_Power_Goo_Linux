#!/usr/bin/env python3
"""
Generate PNG icons for Baxters Power Goo (Linux).
Creates icon_16.png, icon_32.png, icon_48.png, icon_256.png
in the assets/ directory.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 32, 48, 256]
ASSETS_DIR = Path(__file__).parent / "assets"
ASSETS_DIR.mkdir(exist_ok=True)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Background circle — deep purple
    margin = max(1, size // 12)
    d.ellipse([margin, margin, size - margin, size - margin], fill=(70, 20, 100, 255))

    # Goo blob — bright green
    cx, cy = size // 2, size // 2
    r = int(size * 0.30)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(50, 220, 80, 255))

    # Small drip
    drip_w = max(2, r // 3)
    drip_h = max(3, r // 2)
    d.ellipse(
        [cx - drip_w // 2, cy + r - 2, cx + drip_w // 2, cy + r + drip_h],
        fill=(50, 220, 80, 255),
    )

    # "G" text — only for sizes ≥ 32
    if size >= 32:
        text_size = max(8, size // 4)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", text_size)
        except (OSError, IOError):
            font = ImageFont.load_default()
        text = "G"
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = cx - tw // 2
        ty = cy - th // 2 - max(1, r // 6)
        d.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

    return img


def main() -> None:
    for size in SIZES:
        icon = draw_icon(size)
        out = ASSETS_DIR / f"icon_{size}.png"
        icon.save(out, "PNG")
        print(f"  ✓ {out.name}  ({size}×{size})")


if __name__ == "__main__":
    main()
