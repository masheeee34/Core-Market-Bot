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
    watermark_top: str = "POV: You finally found the zero-recoil config 😳",
    watermark_bottom: str = "⚡ 1-Hour FREE Trial • Link in Bio →",
    layout_style: str = "zoom",
) -> bool:
    """
    Renders a High-Definition 9:16 vertical Short (1080x1920) with:
    - Full-Screen 9:16 Crosshair Crop: crop=ih*(9/16):ih:(iw-ow)/2:(ih-oh)/2,scale=1080:1920
    - Vector Top Hook Badge (y=180): Montserrat-Black, 85% Dark Pill, Drop Shadow
    - Vector Bottom CTA Badge (y=1360): Fixed Safe-Zone between crosshair & HUD weapon alerts, #FFE600 Neon Yellow Border
    - Crisp 60FPS High-Definition Encoding Profile (CRF 19, No pixel mush)
    """
    import uuid
    from video_studio.core.overlay import create_hook_badge, create_cta_badge

    temp_dir = Path(output_path).parent.parent / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    uid = uuid.uuid4().hex[:6]
    hook_png = str(temp_dir / f"hook_{uid}.png")
    cta_png = str(temp_dir / f"cta_{uid}.png")

    # Generate Vector HD Badges
    if watermark_top:
        create_hook_badge(watermark_top, hook_png, font_size=36)
    if watermark_bottom:
        create_cta_badge(watermark_bottom, cta_png, font_size=34)

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

    extra_inputs = 0
    hook_idx = -1
    cta_idx = -1

    if watermark_top and os.path.exists(hook_png):
        cmd.extend(["-i", hook_png])
        extra_inputs += 1
        hook_idx = extra_inputs

    if watermark_bottom and os.path.exists(cta_png):
        cmd.extend(["-i", cta_png])
        extra_inputs += 1
        cta_idx = extra_inputs

    audio_input_idx = -1
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])
        extra_inputs += 1
        audio_input_idx = extra_inputs

    # 1. Full-Screen 9:16 Crosshair Crop (No letterboxing/blur)
    filter_parts = [
        "[0:v]crop=ih*(9/16):ih:(iw-ow)/2:(ih-oh)/2,scale=1080:1920[base_v]"
    ]
    cur_v = "base_v"

    # Burn ASS subtitles if provided
    if subtitles_ass_path and os.path.exists(subtitles_ass_path):
        escaped_ass = subtitles_ass_path.replace("\\", "/").replace(":", "\\:")
        filter_parts.append(f"[{cur_v}]ass='{escaped_ass}'[with_subs]")
        cur_v = "with_subs"

    # Overlay Top Hook Badge at y=180
    if hook_idx > 0:
        filter_parts.append(f"[{cur_v}][{hook_idx}:v]overlay=(W-w)/2:180[with_hook]")
        cur_v = "with_hook"

    # Overlay Bottom CTA Badge at Safe-Zone y=1360
    if cta_idx > 0:
        filter_parts.append(f"[{cur_v}][{cta_idx}:v]overlay=(W-w)/2:1360[final_v]")
        cur_v = "final_v"
    else:
        filter_parts.append(f"[{cur_v}]null[final_v]")

    source_has_audio = has_audio_stream(video_path)

    # Audio Mixing
    if audio_input_idx > 0:
        if source_has_audio:
            filter_parts.append(f"[0:a]volume=0.35[bg_a];[{audio_input_idx}:a]volume=1.1[voice_a];[bg_a][voice_a]amix=inputs=2:duration=first[final_a]")
        else:
            filter_parts.append(f"[{audio_input_idx}:a]volume=1.1[final_a]")
    elif source_has_audio:
        filter_parts.append("[0:a]volume=1.4[final_a]")
    else:
        filter_parts.append(f"aevalsrc=0:d={duration}[final_a]")

    cmd.extend([
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        "[final_v]",
        "-map",
        "[final_a]",
    ])

    # HD Video Profile: Eliminates pixelation & compression mush during high-speed 60FPS motion
    cmd.extend([
        "-threads", "0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-b:v", "8M",
        "-maxrate", "12M",
        "-bufsize", "24M",
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
