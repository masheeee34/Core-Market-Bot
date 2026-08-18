import array
import logging
import os
import shutil
import subprocess
from typing import Any

import imageio_ffmpeg

log = logging.getLogger("studio.engine")

FFMPEG_EXE = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()


def is_nvenc_available() -> bool:
    """Checks if NVIDIA NVENC hardware encoder is supported by FFmpeg and GPU."""
    try:
        test_cmd = [FFMPEG_EXE, "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.05", "-c:v", "h264_nvenc", "-f", "null", "-"]
        res = subprocess.run(test_cmd, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


NVENC_ACTIVE = is_nvenc_available()
log.info("FFmpeg Path: %s (NVENC GPU Acceleration: %s)", FFMPEG_EXE, NVENC_ACTIVE)


def has_audio_stream(video_path: str) -> bool:
    """Returns True if the video contains an audio stream."""
    try:
        cmd = [FFMPEG_EXE, "-i", video_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return "Audio:" in res.stderr
    except Exception:
        return False


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
    """Converts any video format (MKV, MOV, WEBM, AVI) to MP4 fast."""
    # First attempt: ultra-fast container remux (0.1s)
    cmd_remux = [
        FFMPEG_EXE,
        "-y",
        "-i",
        input_path,
        "-c",
        "copy",
        output_path,
    ]
    try:
        subprocess.run(cmd_remux, capture_output=True, check=True)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
    except Exception:
        pass

    # Fallback: re-encode with all CPU threads at ultrafast speed
    video_codec = "h264_nvenc" if NVENC_ACTIVE else "libx264"
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-threads",
        "0",
        "-i",
        input_path,
        "-c:v",
        video_codec,
        "-preset",
        "p4" if NVENC_ACTIVE else "ultrafast",
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


def detect_action_highlights(
    video_path: str,
    max_highlights: int = 4,
    clip_duration: float = 30.0,
) -> list[float]:
    """
    Intelligently scans the entire video in ~0.5s to find gunfights, clutches,
    and high-intensity action peaks via audio energy profiling.
    Returns a list of optimal start timestamps (in seconds).
    """
    try:
        cmd = [
            FFMPEG_EXE,
            "-y",
            "-i",
            video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "1000",
            "-f",
            "s16le",
            "pipe:1",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw, _ = proc.communicate()

        if len(raw) % 2 != 0:
            raw = raw[: len(raw) - (len(raw) % 2)]

        samples = array.array("h")
        if raw:
            samples.frombytes(raw)
        total_duration = len(samples) / 1000.0

        if total_duration <= clip_duration:
            real_dur = get_video_duration(video_path)
            if real_dur > clip_duration:
                step = max(1.0, (real_dur - clip_duration) / max(1, max_highlights))
                return [round(i * step, 2) for i in range(max_highlights)]
            return [0.0]

        # Calculate energy in 2-second windows (2000 samples)
        window = 2000
        energies = []
        times = []
        for i in range(0, len(samples) - window, window):
            chunk = samples[i : i + window]
            rms = sum(x * x for x in chunk) / len(chunk)
            energies.append(rms)
            times.append(i / 1000.0)

        # Sort indices by highest sound energy / action intensity
        indexed_energies = sorted(enumerate(energies), key=lambda x: x[1], reverse=True)

        peaks: list[float] = []
        for idx, _ in indexed_energies:
            t = times[idx]
            # Skip first 15s (lobby / waiting) and last 10s
            if t < 15.0 or t > total_duration - 15.0:
                continue
            # Ensure peaks are separated by at least clip_duration
            if all(abs(t - p) >= clip_duration for p in peaks):
                peaks.append(t)
            if len(peaks) >= max_highlights:
                break

        # Fallback if video is quiet or short
        if not peaks:
            real_dur = max(total_duration, get_video_duration(video_path))
            step = max(clip_duration, (real_dur - clip_duration) / max(1, max_highlights))
            return [round(min(max(0.0, real_dur - clip_duration), i * step), 2) for i in range(max_highlights)]

        peaks.sort()

        # Center the clip starting ~6 seconds before the action peak
        start_times = [max(0.0, round(p - 6.0, 2)) for p in peaks]
        log.info("Detected %d action highlights: %s", len(start_times), start_times)
        return start_times

    except Exception as e:
        log.error("Error in action detection: %s", e)
        real_dur = get_video_duration(video_path)
        if real_dur > clip_duration:
            step = max(1.0, (real_dur - clip_duration) / max(1, max_highlights))
            return [round(i * step, 2) for i in range(max_highlights)]
        return [0.0]


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
    - Background: 1080x1920 heavily blurred & darkened for depth (downscale-optimized for 8x speed)
    - Foreground: 1080px wide centered crisp gameplay
    - Subtitles: Hormozi animated ASS burned in
    - High quality, lightweight bitrate (< 8MB per 30s) for Discord & social media compliance
    """
    # Optimized background blur: scale down to 270x480 -> blur -> scale up to 1080x1920 (instant speed)
    filter_complex_parts = [
        "[0:v]split=2[v_bg][v_fg];"
        "[v_bg]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=6:1,scale=1080:1920:flags=bilinear,eq=brightness=-0.15[bg_blur];"
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

    # Detect audio stream presence in source video
    source_has_audio = has_audio_stream(video_path)

    # Audio management
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])
        if source_has_audio:
            # Mix gameplay background audio (-10dB) with AI voiceover (100%)
            cmd.extend([
                "-filter_complex",
                filter_complex + ";[0:a]volume=0.35[bg_a];[1:a]volume=1.1[voice_a];[bg_a][voice_a]amix=inputs=2:duration=first[final_a]",
                "-map",
                "[final_v]",
                "-map",
                "[final_a]",
            ])
        else:
            cmd.extend([
                "-filter_complex",
                filter_complex + ";[1:a]volume=1.1[final_a]",
                "-map",
                "[final_v]",
                "-map",
                "[final_a]",
            ])
    elif source_has_audio:
        # Boost raw game audio by +3dB for punchy mobile TikTok audio
        cmd.extend([
            "-filter_complex",
            filter_complex + ";[0:a]volume=1.4[final_a]",
            "-map",
            "[final_v]",
            "-map",
            "[final_a]",
        ])
    else:
        # Generate silent audio track if no source audio exists to prevent blank audio stream errors
        cmd.extend([
            "-filter_complex",
            filter_complex + f";aevalsrc=0:d={duration}[final_a]",
            "-map",
            "[final_v]",
            "-map",
            "[final_a]",
        ])

    # Video & Audio Encoding Parameters (Optimized for quality + Discord <10MB upload limits)
    if NVENC_ACTIVE:
        cmd.extend([
            "-threads", "0",
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-rc", "vbr",
            "-cq", "24",
            "-b:v", "2.5M",
            "-maxrate", "3.2M",
            "-bufsize", "5M",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path,
        ])
    else:
        cmd.extend([
            "-threads", "0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-maxrate", "2.8M",
            "-bufsize", "5.6M",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path,
        ])

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        log.error("Error rendering Short: %s", e.stderr)
        return False
