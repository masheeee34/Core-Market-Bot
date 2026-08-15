import logging
import os
import subprocess
from typing import Any

import imageio_ffmpeg

log = logging.getLogger("studio.engine")

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()


def is_nvenc_available() -> bool:
    """Checks if NVIDIA NVENC hardware encoder is supported by FFmpeg and GPU."""
    try:
        res = subprocess.run([FFMPEG_EXE, "-encoders"], capture_output=True, text=True, check=True)
        return "h264_nvenc" in res.stdout
    except Exception:
        return False


NVENC_ACTIVE = is_nvenc_available()
log.info("FFmpeg Path: %s (NVENC GPU Acceleration: %s)", FFMPEG_EXE, NVENC_ACTIVE)


def get_video_duration(video_path: str) -> float:
    """Returns the duration of a video in seconds."""
    ffprobe_args = [
        FFMPEG_EXE,
        "-i",
        video_path,
    ]
    res = subprocess.run(ffprobe_args, capture_output=True, text=True)
    import re
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        hours, mins, secs = match.groups()
        return int(hours) * 3600 + int(mins) * 60 + float(secs)
    return 0.0


def convert_to_mp4(input_path: str, output_path: str) -> bool:
    """Converts any video format (MKV, MOV, WEBM, AVI) to MP4 using NVENC fast stream copy or re-encode."""
    video_codec = "h264_nvenc" if NVENC_ACTIVE else "libx264"
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i",
        input_path,
        "-c:v",
        video_codec,
        "-preset",
        "p4" if NVENC_ACTIVE else "veryfast",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_path,
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        log.error("Conversion error: %s", e.stderr)
        return False


def build_9_16_vertical_short(
    video_path: str,
    output_path: str,
    start_time: float = 0.0,
    duration: float = 30.0,
    audio_path: str | None = None,
    subtitles_ass_path: str | None = None,
    watermark_top: str = "⚡ CORE MARKET • 1H FREE TRIAL",
    watermark_bottom: str = "👉 LINK IN BIO • DISCORD.GG/NPXP9UK9JG",
) -> bool:
    """
    Renders a dynamic 9:16 vertical Short (1080x1920) with:
    - Background: 1080x1920 heavily blurred & darkened for depth
    - Foreground: 1080px wide centered crisp gameplay
    - Subtitles: Hormozi animated ASS burned in
    - Fast rendering via NVIDIA NVENC (RTX 3050)
    """
    video_codec = "h264_nvenc" if NVENC_ACTIVE else "libx264"

    # Filtergraph: Split input into background (scale & blur) + foreground (crisp centered overlay)
    # [0:v] split [bg][fg]; [bg] scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,eq=brightness=-0.2 [bg_blurred];
    # [fg] scale=1080:-1 [fg_scaled]; [bg_blurred][fg_scaled] overlay=(W-w)/2:(H-h)/2 [base]
    
    filter_complex_parts = [
        "[0:v]split=2[v_bg][v_fg];"
        "[v_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.15[bg_blur];"
        "[v_fg]scale=1080:-2[fg_scaled];"
        "[bg_blur][fg_scaled]overlay=(W-w)/2:(H-h)/2[base_comp]"
    ]

    current_tag = "base_comp"

    # Burn ASS subtitles if provided
    if subtitles_ass_path and os.path.exists(subtitles_ass_path):
        escaped_ass = subtitles_ass_path.replace("\\", "/").replace(":", "\\:")
        filter_complex_parts.append(f"[{current_tag}]ass='{escaped_ass}'[with_subs]")
        current_tag = "with_subs"

    # Add stylish top banner text
    if watermark_top:
        escaped_top = watermark_top.replace(":", "\\:").replace("'", "")
        filter_complex_parts.append(
            f"[{current_tag}]drawtext=text='{escaped_top}':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=120:box=1:boxcolor=black@0.7:boxborderw=14[with_top]"
        )
        current_tag = "with_top"

    # Add bottom CTA banner text
    if watermark_bottom:
        escaped_bottom = watermark_bottom.replace(":", "\\:").replace("'", "")
        filter_complex_parts.append(
            f"[{current_tag}]drawtext=text='{escaped_bottom}':fontcolor=#00e5ff:fontsize=32:x=(w-text_w)/2:y=h-160:box=1:boxcolor=black@0.75:boxborderw=12[final_v]"
        )
        current_tag = "final_v"

    filter_complex = ";".join(filter_complex_parts)
    if not filter_complex.endswith("[final_v]"):
        filter_complex += f";[{current_tag}]null[final_v]"

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-ss",
        str(start_time),
        "-t",
        str(duration),
        "-i",
        video_path,
    ]

    # Add custom Voiceover Audio if specified
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])
        # Mix gameplay background audio (-15dB) with AI voiceover (100%)
        cmd.extend([
            "-filter_complex",
            filter_complex + ";[0:a]volume=0.25[bg_a];[1:a]volume=1.0[voice_a];[bg_a][voice_a]amix=inputs=2:duration=first[final_a]",
            "-map",
            "[final_v]",
            "-map",
            "[final_a]",
        ])
    else:
        cmd.extend([
            "-filter_complex",
            filter_complex,
            "-map",
            "[final_v]",
            "-map",
            "0:a?",
        ])

    cmd.extend([
        "-c:v",
        video_codec,
        "-preset",
        "p4" if NVENC_ACTIVE else "veryfast",
        "-b:v",
        "8M",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_path,
    ])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        log.error("Error rendering Short: %s", e.stderr)
        return False
