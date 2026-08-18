import array
import logging
import os
import shutil
import subprocess
from pathlib import Path
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
    hook_y: int = 180,
    cta_y: int = 1360,
    badge_style: str = "dark-neon",
    music_track: str = "none",
    music_volume: float = 0.35,
    custom_music_url: str = "",
    logo_variant: str = "gold",
    logo_position: str = "top_right",
    logo_size: int = 120,
    logo_opacity: float = 0.85,
    template_style: str = "cyber_hud",
) -> bool:
    """
    Renders a High-Definition 9:16 vertical Short (1080x1920) with:
    - Full-Screen 9:16 Crosshair Crop: crop=ih*(9/16):ih:(iw-ow)/2:(ih-oh)/2,scale=1080:1920
    - Dynamic Transparent Logo Watermark 'C' (7 colorways, custom X/Y and opacity)
    - Vector Top Hook Badge: Montserrat-Black, 85% Dark Pill, Drop Shadow (customizable Y)
    - Vector Bottom CTA Badge: Safe-Zone Y (default 1360), Customizable style ('dark-neon', 'solid-yellow', 'minimal')
    - Viral Background Music: 10 curated tracks or custom YouTube audio mixed seamlessly
    - Crisp 60FPS High-Definition Encoding Profile (CRF 19, No pixel mush)
    """
    import uuid
    try:
        from video_studio.core.overlay import create_hook_badge, create_cta_badge
    except ImportError:
        from core.overlay import create_hook_badge, create_cta_badge

    temp_dir = Path(output_path).parent.parent / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    uid = uuid.uuid4().hex[:6]
    hook_png = str(temp_dir / f"hook_{uid}.png")
    cta_png = str(temp_dir / f"cta_{uid}.png")

    # Generate Vector HD Badges
    if watermark_top:
        create_hook_badge(watermark_top, hook_png, font_size=36)
    if watermark_bottom:
        create_cta_badge(watermark_bottom, cta_png, font_size=34, badge_style=badge_style)

    # Resolve Background Music Track
    music_file_path = None
    music_dir = Path(__file__).parent.parent / "assets" / "music"

    if custom_music_url and custom_music_url.strip():
        try:
            try:
                from video_studio.core.downloader import download_youtube_audio
            except ImportError:
                from core.downloader import download_youtube_audio
            custom_target = str(temp_dir / f"custom_music_{uid}.mp3")
            downloaded = download_youtube_audio(custom_music_url.strip(), custom_target)
            if downloaded and os.path.exists(downloaded):
                music_file_path = downloaded
        except Exception as e:
            log.warning("Failed to download custom music: %s", e)
    elif music_track and music_track != "none" and music_track != "random_viral":
        for ext in [".mp3", ".m4a", ".wav", ".aac"]:
            candidate = music_dir / f"{music_track}{ext}"
            if candidate.exists():
                music_file_path = str(candidate)
                break

    # Resolve Logo Watermark
    logos_dir = Path(__file__).parent.parent / "assets" / "logos"
    logo_file_path = None
    if logo_variant and logo_variant != "none" and logo_position != "none":
        candidate_logo = logos_dir / f"logo_{logo_variant}.png"
        if candidate_logo.exists():
            logo_file_path = str(candidate_logo)

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
    logo_idx = -1

    if watermark_top and os.path.exists(hook_png):
        cmd.extend(["-i", hook_png])
        extra_inputs += 1
        hook_idx = extra_inputs

    if watermark_bottom and os.path.exists(cta_png):
        cmd.extend(["-i", cta_png])
        extra_inputs += 1
        cta_idx = extra_inputs

    if logo_file_path and os.path.exists(logo_file_path):
        cmd.extend(["-i", logo_file_path])
        extra_inputs += 1
        logo_idx = extra_inputs

    audio_input_idx = -1
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])
        extra_inputs += 1
        audio_input_idx = extra_inputs

    music_input_idx = -1
    if music_file_path and os.path.exists(music_file_path):
        cmd.extend(["-i", music_file_path])
        extra_inputs += 1
        music_input_idx = extra_inputs

    # 1. Full-Screen 9:16 Crosshair Crop
    filter_parts = [
        "[0:v]crop=ih*(9/16):ih:(iw-ow)/2:(ih-oh)/2,scale=1080:1920[base_v]"
    ]
    cur_v = "base_v"

    # Burn ASS subtitles if provided
    if subtitles_ass_path and os.path.exists(subtitles_ass_path):
        escaped_ass = subtitles_ass_path.replace("\\", "/").replace(":", "\\:")
        filter_parts.append(f"[{cur_v}]ass='{escaped_ass}'[with_subs]")
        cur_v = "with_subs"

    # Overlay Logo Watermark
    if logo_idx > 0:
        l_size = max(50, min(240, int(logo_size)))
        l_opac = max(0.1, min(1.0, float(logo_opacity)))

        filter_parts.append(f"[{logo_idx}:v]scale={l_size}:-1,format=rgba,colorchannelmixer=aa={l_opac}[logo_scaled]")

        if logo_position == "top_left":
            pos_str = "x=40:y=45"
        elif logo_position == "bottom_right":
            pos_str = "x=W-w-40:y=H-h-240"
        elif logo_position == "center_floating":
            pos_str = "x=(W-w)/2:y=950"
        else: # top_right default
            pos_str = "x=W-w-40:y=45"

        filter_parts.append(f"[{cur_v}][logo_scaled]overlay={pos_str}[with_logo]")
        cur_v = "with_logo"

    # Overlay Top Hook Badge at hook_y
    if hook_idx > 0:
        filter_parts.append(f"[{cur_v}][{hook_idx}:v]overlay=(W-w)/2:{hook_y}[with_hook]")
        cur_v = "with_hook"

    # Overlay Bottom CTA Badge at cta_y
    if cta_idx > 0:
        filter_parts.append(f"[{cur_v}][{cta_idx}:v]overlay=(W-w)/2:{cta_y}[final_v]")
        cur_v = "final_v"
    else:
        filter_parts.append(f"[{cur_v}]null[final_v]")

    source_has_audio = has_audio_stream(video_path)

    # Audio Mixing with Viral Background Music Support
    if music_input_idx > 0:
        # Music is present
        vol = max(0.05, min(1.0, float(music_volume)))
        if source_has_audio:
            filter_parts.append(
                f"[0:a]volume=1.0[game_a];"
                f"[{music_input_idx}:a]aloop=loop=-1:size=2e+09,volume={vol}[music_a];"
                f"[game_a][music_a]amix=inputs=2:duration=first:dropout_transition=2[mixed_a]"
            )
            cur_a = "mixed_a"
        else:
            filter_parts.append(
                f"[{music_input_idx}:a]aloop=loop=-1:size=2e+09,volume={vol},atrim=0:{duration}[mixed_a]"
            )
            cur_a = "mixed_a"

        if audio_input_idx > 0:
            filter_parts.append(
                f"[{cur_a}]volume=0.85[duck_a];[{audio_input_idx}:a]volume=1.2[voice_a];[duck_a][voice_a]amix=inputs=2:duration=first[final_a]"
            )
        else:
            filter_parts.append(f"[{cur_a}]volume=1.0[final_a]")

    elif audio_input_idx > 0:
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
