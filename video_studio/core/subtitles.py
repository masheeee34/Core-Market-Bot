import os
import re
from typing import Any


def format_ass_time(seconds: float) -> str:
    """Formats seconds into ASS timestamp format H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def generate_hormozi_ass_subtitles(
    word_boundaries: list[dict[str, Any]],
    output_ass_path: str,
    raw_text: str = "",
    estimated_total_duration: float = 10.0,
    style_theme: str = "hormozi_yellow",
    words_per_batch: int = 3,
) -> bool:
    """
    Generates dynamic ASS subtitles in viral TikTok/Hormozi style with:
    - Big bold centered font (Arial Black / Impact)
    - Word-by-word active highlight & zoom pop effect
    - High contrast thick outline for maximum legibility on mobile screens
    - Automatic fallback chunking if raw text is passed
    """
    themes = {
        "hormozi_yellow": {
            "primary": "&H00FFFFFF",      # White default
            "highlight": "&H0000FFFF",    # Pure Yellow highlight (BGR: 00FFFF)
            "outline": "&H00000000",      # Deep Black Outline
            "shadow": "&H80000000",
        },
        "cyber_cyan": {
            "primary": "&H00FFFFFF",
            "highlight": "&H00FFFF00",    # Cyan highlight (BGR: FFFF00)
            "outline": "&H00000000",
            "shadow": "&H80000000",
        },
        "toxic_green": {
            "primary": "&H00FFFFFF",
            "highlight": "&H0000FF00",    # Pure Green highlight
            "outline": "&H00000000",
            "shadow": "&H80000000",
        },
    }

    t = themes.get(style_theme, themes["hormozi_yellow"])

    ass_header = f"""[Script Info]
Title: Hormozi Dynamic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,72,{t['primary']},{t['primary']},{t['outline']},{t['shadow']},-1,0,0,0,100,100,2,0,1,8,4,5,60,60,960,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []

    # If word boundaries were not captured, build evenly-spaced words from raw text
    if not word_boundaries and raw_text:
        words = [w.strip() for w in re.split(r"\s+", raw_text) if w.strip()]
        if words:
            time_per_word = max(0.25, estimated_total_duration / len(words))
            for idx, word in enumerate(words):
                w_offset = idx * time_per_word
                word_boundaries.append({
                    "text": word,
                    "offset": w_offset,
                    "duration": time_per_word,
                })

    if not word_boundaries:
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(ass_header)
        return True

    # Group words into small chunks (2-3 words per screen) for fast-paced viral reading
    chunks: list[list[dict[str, Any]]] = []
    for i in range(0, len(word_boundaries), words_per_batch):
        chunks.append(word_boundaries[i : i + words_per_batch])

    for chunk in chunks:
        for active_idx, active_word in enumerate(chunk):
            w_start = active_word["offset"]
            w_end = active_word["offset"] + active_word["duration"]

            # Build line with the active word highlighted in bright yellow/cyan and slightly larger
            line_words = []
            for j, w in enumerate(chunk):
                word_text = w["text"].upper()
                if j == active_idx:
                    line_words.append(r"{\c" + t["highlight"] + r"\fscx112\fscy112}" + word_text + r"{\r}")
                else:
                    line_words.append(r"{\c" + t["primary"] + r"\fscx100\fscy100}" + word_text + r"{\r}")

            formatted_text = " ".join(line_words)
            start_str = format_ass_time(w_start)
            end_str = format_ass_time(w_end)

            events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{formatted_text}")

    full_ass_content = ass_header + "\n".join(events)

    try:
        os.makedirs(os.path.dirname(output_ass_path), exist_ok=True)
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(full_ass_content)
        return True
    except Exception as e:
        print(f"Error saving ASS subtitles: {e}")
        return False
