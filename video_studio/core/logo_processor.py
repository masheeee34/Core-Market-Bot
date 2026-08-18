"""
Logo Processing and Colorway Generator for Core Market Studio.
Extracts the uploaded 'C' logo, creates transparent PNGs, and generates 7 distinct color variants and 12 channel avatar icons.
"""

import os
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
LOGOS_DIR = BASE_DIR / "assets" / "logos"
AVATARS_DIR = BASE_DIR / "assets" / "avatars"

LOGOS_DIR.mkdir(parents=True, exist_ok=True)
AVATARS_DIR.mkdir(parents=True, exist_ok=True)


def process_and_generate_logo_variants(source_image_path: str) -> dict[str, str]:
    """
    Takes the source logo image (with solid background), removes background,
    and generates 7 transparent colorways + circular avatar profiles.
    """
    img = Image.open(source_image_path).convert("RGBA")
    w, h = img.size

    # Background color is sampled from corners (dark wine brown)
    corners = [
        img.getpixel((0, 0)),
        img.getpixel((w - 1, 0)),
        img.getpixel((0, h - 1)),
        img.getpixel((w - 1, h - 1)),
    ]
    bg_r = int(np.median([c[0] for c in corners]))
    bg_g = int(np.median([c[1] for c in corners]))
    bg_b = int(np.median([c[2] for c in corners]))

    arr = np.array(img, dtype=np.float32)
    diff = np.sqrt(
        (arr[:, :, 0] - bg_r) ** 2 +
        (arr[:, :, 1] - bg_g) ** 2 +
        (arr[:, :, 2] - bg_b) ** 2
    )

    # Threshold for transparency
    mask = np.clip((diff - 25.0) / 20.0, 0.0, 1.0)
    arr[:, :, 3] = arr[:, :, 3] * mask

    base_transparent = Image.fromarray(arr.astype(np.uint8), mode="RGBA")
    # Crop to bounding box
    bbox = base_transparent.getbbox()
    if bbox:
        base_transparent = base_transparent.crop(bbox)

    # Standardize size to 512x512 with padding
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    base_transparent.thumbnail((460, 460), Image.Resampling.LANCZOS)
    offset = ((512 - base_transparent.width) // 2, (512 - base_transparent.height) // 2)
    canvas.paste(base_transparent, offset, base_transparent)

    variants = {}

    # 1. Original Wine & Gold
    orig_path = LOGOS_DIR / "logo_original.png"
    canvas.save(orig_path, "PNG")
    variants["original"] = str(orig_path)

    # Helper to tint / recolor non-transparent pixels
    def create_tinted_variant(name: str, primary_rgb: tuple[int, int, int], secondary_rgb: tuple[int, int, int]):
        data = np.array(canvas, dtype=np.float32)
        alpha = data[:, :, 3] / 255.0
        
        # Calculate lightness/luminance
        lum = (0.299 * data[:, :, 0] + 0.587 * data[:, :, 1] + 0.114 * data[:, :, 2]) / 255.0

        # Where lum is high (outline/highlights) -> primary color
        # Where lum is low/mid (body of C) -> secondary color
        out_r = (lum * primary_rgb[0] + (1 - lum) * secondary_rgb[0])
        out_g = (lum * primary_rgb[1] + (1 - lum) * secondary_rgb[1])
        out_b = (lum * primary_rgb[2] + (1 - lum) * secondary_rgb[2])

        data[:, :, 0] = out_r
        data[:, :, 1] = out_g
        data[:, :, 2] = out_b
        data[:, :, 3] = alpha * 255.0

        variant_img = Image.fromarray(np.clip(data, 0, 255).astype(np.uint8), mode="RGBA")
        out_path = LOGOS_DIR / f"logo_{name}.png"
        variant_img.save(out_path, "PNG")
        variants[name] = str(out_path)
        return variant_img

    # 2. Gold Neon (Core Market Signature)
    create_tinted_variant("gold", (255, 240, 50), (200, 140, 10))

    # 3. Cyber Cyan
    create_tinted_variant("cyan", (0, 245, 255), (0, 90, 180))

    # 4. Crimson Red
    create_tinted_variant("crimson", (255, 60, 80), (140, 10, 25))

    # 5. Purple Vortex
    create_tinted_variant("purple", (220, 100, 255), (110, 20, 180))

    # 6. Emerald Acid Green
    create_tinted_variant("emerald", (40, 255, 140), (10, 130, 60))

    # 7. Pure Platinum White
    create_tinted_variant("platinum", (255, 255, 255), (140, 150, 170))

    # 8. Dark Stealth Obsidian
    create_tinted_variant("stealth", (180, 190, 205), (35, 45, 60))

    # Generate 12 Channel Avatars with circular backgrounds
    channel_themes = {
        "coremarket_clips": ("gold", (18, 20, 29)),
        "coremarket_warzone": ("gold", (35, 12, 15)),
        "coremarket_fps": ("emerald", (10, 28, 22)),
        "coremarket_meta": ("cyan", (12, 22, 38)),
        "coremarket_bo6": ("crimson", (28, 10, 12)),
        "core_aimvault": ("gold", (10, 10, 14)),
        "coremarket_ranked": ("gold", (22, 18, 8)),
        "coremarket_zero": ("gold", (12, 14, 20)),
        "coremarket_tactical": ("emerald", (20, 24, 18)),
        "coremarket_gg": ("purple", (25, 12, 35)),
        "coremarket_vortex": ("purple", (15, 12, 32)),
        "coremarket_prime": ("platinum", (16, 18, 24)),
    }

    for chan_id, (logo_var, bg_rgb) in channel_themes.items():
        var_path = LOGOS_DIR / f"logo_{logo_var}.png"
        if var_path.exists():
            v_img = Image.open(var_path).convert("RGBA")
            v_img.thumbnail((360, 360), Image.Resampling.LANCZOS)

            av_canvas = Image.new("RGBA", (512, 512), (*bg_rgb, 255))
            av_offset = ((512 - v_img.width) // 2, (512 - v_img.height) // 2)
            av_canvas.paste(v_img, av_offset, v_img)

            # Circular mask
            mask_img = Image.new("L", (512, 512), 0)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(mask_img)
            draw.ellipse((0, 0, 512, 512), fill=255)
            av_canvas.putalpha(mask_img)

            av_out = AVATARS_DIR / f"avatar_{chan_id}.png"
            av_canvas.save(av_out, "PNG")

    return variants


if __name__ == "__main__":
    src = r"C:\Users\ayman\.gemini\antigravity\brain\40fc26ea-a1c4-47f0-85d5-696676f39fd6\.user_uploaded\media_1787065290829.jpg"
    if os.path.exists(src):
        res = process_and_generate_logo_variants(src)
        print("Generated logo variants:", list(res.keys()))
