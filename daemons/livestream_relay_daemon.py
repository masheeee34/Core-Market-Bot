"""
Livestream Relay Daemon for Core Market Bot.
Streams a 24/7 continuous gameplay loop with Phonk music, transparent Logo 'C',
and live Undetected status overlay to Kick / YouTube Live via FFmpeg RTMP.
"""

import asyncio
import json
import logging
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [livestream_relay]: %(message)s",
)
log = logging.getLogger("livestream_relay")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "video_studio" / "output"
ASSETS_DIR = BASE_DIR / "video_studio" / "assets"
MUSIC_DIR = ASSETS_DIR / "music"
LOGOS_DIR = ASSETS_DIR / "logos"
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "stream_config.json"
PLAYLIST_FILE = BASE_DIR / "video_studio" / "temp" / "live_playlist.txt"

DATA_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "video_studio" / "temp").mkdir(parents=True, exist_ok=True)

DEFAULT_STREAM_CONFIG = {
    "enabled": False,  # Enable by setting RTMP URL and stream key
    "rtmp_url": "rtmp://live.kick.com/app/",
    "stream_key": "",
    "resolution": "1080x1920",  # or 1920x1080 for horizontal
    "bitrate": "4500k",
    "fps": 60,
    "logo_variant": "gold",
    "status_banner": "🟢 CORE MARKET | 100% UNDETECTED | 🎁 1H FREE TRIAL IN BIO",
}


def load_stream_config() -> dict:
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_STREAM_CONFIG, f, indent=2)
        return DEFAULT_STREAM_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_STREAM_CONFIG, **json.load(f)}
    except Exception:
        return DEFAULT_STREAM_CONFIG


def generate_playlist() -> list[str]:
    """Finds all available generated MP4 clips and writes a concat playlist file."""
    clips = list(OUTPUT_DIR.glob("*.mp4"))
    if not clips:
        # Fallback to temp or sample
        clips = list((BASE_DIR / "video_studio" / "temp").glob("*.mp4"))

    if not clips:
        log.warning("No video clips found in output/ for streaming.")
        return []

    # Shuffle for fresh stream variety
    random.shuffle(clips)

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\n")

    log.info("Generated stream playlist with %d video(s).", len(clips))
    return [str(c) for c in clips]


def build_stream_command(config: dict) -> list[str]:
    """Constructs FFmpeg RTMP broadcast pipeline."""
    target_rtmp = config["rtmp_url"].rstrip("/") + "/" + config["stream_key"].lstrip("/")
    logo_path = LOGOS_DIR / f"logo_{config.get('logo_variant', 'gold')}.png"

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    cmd = [
        ffmpeg_bin,
        "-re",
        "-f", "concat",
        "-safe", "0",
        "-stream_loop", "-1",
        "-i", str(PLAYLIST_FILE),
    ]

    extra_inputs = 0
    logo_idx = -1

    if logo_path.exists():
        cmd.extend(["-i", str(logo_path)])
        extra_inputs += 1
        logo_idx = extra_inputs

    # Filter complex for logo watermark & status overlay
    filters = []
    cur_v = "0:v"

    if logo_idx > 0:
        filters.append(f"[{logo_idx}:v]scale=120:-1,format=rgba,colorchannelmixer=aa=0.9[logo]")
        filters.append(f"[{cur_v}][logo]overlay=W-w-35:35[with_logo]")
        cur_v = "with_logo"

    # Draw lower-third live text
    status_text = config.get("status_banner", "🟢 CORE MARKET | 100% UNDETECTED | 1H FREE TRIAL")
    escaped_text = status_text.replace(":", "\\:").replace("'", "")
    filters.append(
        f"[{cur_v}]drawtext=text='{escaped_text}':fontcolor=white:fontsize=28:box=1:boxcolor=black@0.75:boxborderw=10:x=(w-text_w)/2:y=h-140[final_v]"
    )

    cmd.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[final_v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", config.get("bitrate", "4500k"),
        "-maxrate", "5000k",
        "-bufsize", "9000k",
        "-pix_fmt", "yuv420p",
        "-g", str(config.get("fps", 60) * 2),
        "-c:a", "aac",
        "-b:a", "160k",
        "-ar", "44100",
        "-f", "flv",
        target_rtmp,
    ])

    return cmd


async def run_stream_relay_loop() -> None:
    """Monitors configuration and manages the live FFmpeg RTMP process 24/7."""
    log.info("🚀 Starting Livestream Relay Daemon (24/7 RTMP Engine for Kick & YouTube)...")

    while True:
        try:
            config = load_stream_config()

            if not config.get("enabled", False) or not config.get("stream_key"):
                log.info("Livestreaming is currently idle. (To start, set 'enabled': true and 'stream_key' in data/stream_config.json)")
                await asyncio.sleep(60)
                continue

            playlist = generate_playlist()
            if not playlist:
                log.warning("No clips available to stream. Sleeping 60s...")
                await asyncio.sleep(60)
                continue

            cmd = build_stream_command(config)
            log.info("📡 Launching 24/7 RTMP Stream to %s...", config.get("rtmp_url"))

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            # Await process exit (or reconnection on disconnect)
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                log.warning("Stream disconnected with return code %d: %s", proc.returncode, stderr.decode()[:300] if stderr else "")
                log.info("Reconnecting stream in 5 seconds...")
                await asyncio.sleep(5)

        except Exception as e:
            log.error("Exception in livestream relay daemon: %s", e, exc_info=True)
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(run_stream_relay_loop())
    except (KeyboardInterrupt, SystemExit):
        log.info("Livestream Relay Daemon stopped.")
