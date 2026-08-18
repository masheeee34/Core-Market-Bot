"""
HD Vector Overlay Generator (Pillow / PIL)
Generates high-resolution transparent PNG badges with:
- Anti-aliased pill-shaped rounded rectangles (border-radius: 9999px)
- Ultra-bold typography (Montserrat-Black / Bebas Neue)
- Soft realistic drop-shadows (Gaussian blur)
- Dual-color high-contrast text rendering
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
DEFAULT_FONT_PATH = str(FONTS_DIR / "Montserrat-Black.ttf")
ALT_FONT_PATH = str(FONTS_DIR / "Montserrat-ExtraBold.ttf")
BEBAS_FONT_PATH = str(FONTS_DIR / "BebasNeue-Regular.ttf")


def get_font(size: int, font_name: str = "montserrat_black") -> ImageFont.FreeTypeFont:
    font_map = {
        "montserrat_black": DEFAULT_FONT_PATH,
        "montserrat_extrabold": ALT_FONT_PATH,
        "bebas": BEBAS_FONT_PATH,
    }
    target_path = font_map.get(font_name, DEFAULT_FONT_PATH)

    if os.path.exists(target_path):
        try:
            return ImageFont.truetype(target_path, size)
        except Exception:
            pass

    # System Fallback
    for fallback in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arialbd.ttf",
        "arial.ttf",
    ]:
        if os.path.exists(fallback):
            try:
                return ImageFont.truetype(fallback, size)
            except Exception:
                pass

    return ImageFont.load_default()


def create_hook_badge(
    text: str,
    output_path: str,
    font_size: int = 36,
    max_width: int = 980,
) -> str:
    """
    Generates a sleek, high-engagement Top Hook Badge (Pilule noire 85%, bordure subtile, drop shadow).
    """
    font = get_font(font_size, "montserrat_black")

    # Measure text bounding box
    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy_img)
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Adjust font size if text is too wide
    if text_w > max_width:
        scale_ratio = max_width / text_w
        font_size = max(24, int(font_size * scale_ratio))
        font = get_font(font_size, "montserrat_black")
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    padding_x = 36
    padding_y = 18
    badge_w = text_w + (padding_x * 2)
    badge_h = text_h + (padding_y * 2)
    radius = badge_h // 2

    # Canvas with shadow margin
    shadow_blur = 12
    shadow_offset_y = 6
    margin = shadow_blur * 2
    canvas_w = badge_w + margin * 2
    canvas_h = badge_h + margin * 2 + shadow_offset_y

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 1. Draw Drop Shadow
    shadow_mask = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_mask)
    s_x0 = margin
    s_y0 = margin + shadow_offset_y
    s_x1 = s_x0 + badge_w
    s_y1 = s_y0 + badge_h
    s_draw.rounded_rectangle([s_x0, s_y0, s_x1, s_y1], radius=radius, fill=(0, 0, 0, 175))
    shadow_blurred = shadow_mask.filter(ImageFilter.GaussianBlur(shadow_blur))
    canvas.alpha_composite(shadow_blurred)

    # 2. Draw Pill Body (85% Dark) & Subtle White Border (12%)
    body_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(body_img)
    b_x0 = margin
    b_y0 = margin
    b_x1 = b_x0 + badge_w
    b_y1 = b_y0 + badge_h

    # Fill
    b_draw.rounded_rectangle([b_x0, b_y0, b_x1, b_y1], radius=radius, fill=(8, 10, 16, 218))
    # Border
    b_draw.rounded_rectangle([b_x0, b_y0, b_x1, b_y1], radius=radius, outline=(255, 255, 255, 38), width=2)

    # 3. Draw Ultra-Bold White Text
    t_x = b_x0 + padding_x - bbox[0]
    t_y = b_y0 + padding_y - bbox[1]
    b_draw.text((t_x, t_y), text, font=font, fill=(255, 255, 255, 255))

    canvas.alpha_composite(body_img)
    canvas.save(output_path, "PNG")
    return output_path


def create_cta_badge(
    text: str = "⚡ 1-Hour FREE Trial • Link in Bio →",
    output_path: str = "",
    font_size: int = 34,
    badge_style: str = "dark-neon",
) -> str:
    """
    Generates the High-Conversion CTA Badge:
    - badge_style="dark-neon" (Default): 90% dark body + #FFE600 Neon Yellow 3px border + Yellow/White text
    - badge_style="solid-yellow": Solid #FFE600 Yellow pill + Ultra-bold Black text
    - badge_style="minimal": 85% dark body + subtle white border + White text
    """
    font_bold = get_font(font_size, "montserrat_black")

    # Split into sections: Primary Hook (Yellow) + Secondary CTA (White)
    if "•" in text:
        parts = text.split("•", 1)
        part1 = parts[0].strip()
        sep = " • "
        part2 = parts[1].strip()
    elif ":" in text:
        parts = text.split(":", 1)
        part1 = parts[0].strip()
        sep = " : "
        part2 = parts[1].strip()
    else:
        part1 = text.strip()
        sep = ""
        part2 = ""

    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy_img)

    bbox1 = dummy_draw.textbbox((0, 0), part1, font=font_bold)
    w1 = bbox1[2] - bbox1[0]
    h1 = bbox1[3] - bbox1[1]

    bbox_sep = dummy_draw.textbbox((0, 0), sep, font=font_bold) if sep else (0, 0, 0, 0)
    w_sep = bbox_sep[2] - bbox_sep[0]

    bbox2 = dummy_draw.textbbox((0, 0), part2, font=font_bold) if part2 else (0, 0, 0, 0)
    w2 = bbox2[2] - bbox2[0]

    total_text_w = w1 + w_sep + w2
    max_h = max(h1, bbox2[3] - bbox2[1] if part2 else 0, 32)

    padding_x = 42
    padding_y = 20
    badge_w = total_text_w + (padding_x * 2)
    badge_h = max_h + (padding_y * 2)
    radius = badge_h // 2

    # Canvas size with shadow margin
    shadow_blur = 14
    shadow_offset_y = 6
    margin = shadow_blur * 2
    canvas_w = badge_w + margin * 2
    canvas_h = badge_h + margin * 2 + shadow_offset_y

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 1. Drop Shadow
    shadow_mask = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_mask)
    s_x0 = margin
    s_y0 = margin + shadow_offset_y
    s_x1 = s_x0 + badge_w
    s_y1 = s_y0 + badge_h
    s_draw.rounded_rectangle([s_x0, s_y0, s_x1, s_y1], radius=radius, fill=(0, 0, 0, 200))
    shadow_blurred = shadow_mask.filter(ImageFilter.GaussianBlur(shadow_blur))
    canvas.alpha_composite(shadow_blurred)

    # 2. Draw Pill Body & Border based on badge_style
    body_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(body_img)
    b_x0 = margin
    b_y0 = margin
    b_x1 = b_x0 + badge_w
    b_y1 = b_y0 + badge_h

    if badge_style == "solid-yellow":
        # Solid Yellow Body
        b_draw.rounded_rectangle([b_x0, b_y0, b_x1, b_y1], radius=radius, fill=(255, 230, 0, 255))
        b_draw.rounded_rectangle([b_x0, b_y0, b_x1, b_y1], radius=radius, outline=(0, 0, 0, 60), width=2)
    elif badge_style == "minimal":
        # Dark Minimal Body
        b_draw.rounded_rectangle([b_x0, b_y0, b_x1, b_y1], radius=radius, fill=(12, 14, 20, 220))
        b_draw.rounded_rectangle([b_x0, b_y0, b_x1, b_y1], radius=radius, outline=(255, 255, 255, 45), width=2)
    else:
        # dark-neon (Default)
        b_draw.rounded_rectangle([b_x0, b_y0, b_x1, b_y1], radius=radius, fill=(10, 10, 14, 230))
        b_draw.rounded_rectangle([b_x0, b_y0, b_x1, b_y1], radius=radius, outline=(255, 230, 0, 245), width=3)

    # 3. Draw Hierarchical Text
    cur_x = b_x0 + padding_x
    text_y = b_y0 + padding_y - bbox1[1]

    if badge_style == "solid-yellow":
        # Black Text
        b_draw.text((cur_x, text_y), part1, font=font_bold, fill=(0, 0, 0, 255))
        cur_x += w1
        if sep:
            b_draw.text((cur_x, text_y), sep, font=font_bold, fill=(60, 60, 60, 230))
            cur_x += w_sep
        if part2:
            b_draw.text((cur_x, text_y), part2, font=font_bold, fill=(0, 0, 0, 255))
    elif badge_style == "minimal":
        # White Text
        b_draw.text((cur_x, text_y), part1, font=font_bold, fill=(255, 255, 255, 255))
        cur_x += w1
        if sep:
            b_draw.text((cur_x, text_y), sep, font=font_bold, fill=(148, 163, 184, 230))
            cur_x += w_sep
        if part2:
            b_draw.text((cur_x, text_y), part2, font=font_bold, fill=(255, 255, 255, 255))
    else:
        # dark-neon: Yellow Part 1 + White Part 2
        b_draw.text((cur_x, text_y), part1, font=font_bold, fill=(255, 230, 0, 255))
        cur_x += w1
        if sep:
            b_draw.text((cur_x, text_y), sep, font=font_bold, fill=(148, 163, 184, 230))
            cur_x += w_sep
        if part2:
            b_draw.text((cur_x, text_y), part2, font=font_bold, fill=(255, 255, 255, 255))

    canvas.alpha_composite(body_img)
    canvas.save(output_path, "PNG")
    return output_path
