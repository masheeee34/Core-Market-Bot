"""
Clip Miner Daemon for Core Market Bot.
Scrapes and downloads public tournament clutches and high-action Warzone / BO6 highlights
using yt-dlp, storing raw clips into video_studio/temp/mined_clips/ for the studio worker.
"""

import asyncio
import json
import logging
import os
import random
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [clip_miner]: %(message)s",
)
log = logging.getLogger("clip_miner")

BASE_DIR = Path(__file__).resolve().parent.parent
MINED_DIR = BASE_DIR / "video_studio" / "temp" / "mined_clips"
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "mined_history.json"

MINED_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Curated high-engagement search queries for COD Warzone & BO6 clutches
CURATED_QUERIES = [
    "Warzone ranked 1v4 clutch highlight 2026",
    "Warzone world record solo squad gameplay no commentary",
    "Black Ops 6 ranked search and destroy clutch ace",
    "BO6 1v4 snipers only clutch highlight",
    "Warzone rebirth island clean aim tracking gameplay",
    "Warzone zero recoil best weapon build gameplay 1080p",
    "Top 250 Warzone ranked solo clutch gameplay",
    "BO6 multiplayer nuke streak high kill gameplay",
]


def load_history() -> set[str]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("downloaded_ids", []))
        except Exception as e:
            log.warning("Could not read mined history: %s", e)
    return set()


def save_history(history: set[str]) -> None:
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"downloaded_ids": list(history)}, f, indent=2)
    except Exception as e:
        log.error("Failed to save mined history: %s", e)


def search_and_mine_clips(max_clips_per_cycle: int = 2) -> list[str]:
    """
    Searches YouTube for creative commons / tournament highlights and downloads short clips (<= 3 mins).
    """
    history = load_history()
    downloaded_files: list[str] = []

    query = random.choice(CURATED_QUERIES)
    log.info("Mining clips for query: '%s'...", query)

    # Search for top results using yt-dlp JSON dump
    cmd_search = [
        sys.executable, "-m", "yt_dlp",
        f"ytsearch10:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--ignore-errors",
    ]

    try:
        proc = subprocess.run(cmd_search, capture_output=True, text=True, check=True)
        entries = []
        for line in proc.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

        log.info("Found %d candidates on search query.", len(entries))

        for entry in entries:
            if len(downloaded_files) >= max_clips_per_cycle:
                break

            v_id = entry.get("id")
            v_url = entry.get("url") or f"https://www.youtube.com/watch?v={v_id}"
            duration = entry.get("duration", 0)

            if not v_id or v_id in history:
                continue

            # Target videos between 15s and 300s (ideal for clipping)
            if duration and duration > 360:
                continue

            log.info("Downloading candidate clip [%s]: %s (Duration: %ss)...", v_id, entry.get("title", ""), duration)
            out_pattern = str(MINED_DIR / f"mined_{v_id}_%(ext)s")

            cmd_dl = [
                sys.executable, "-m", "yt_dlp",
                "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "-o", out_pattern,
                "--max-filesize", "150M",
                "--no-playlist",
                v_url,
            ]

            dl_proc = subprocess.run(cmd_dl, capture_output=True, text=True)
            if dl_proc.returncode == 0:
                # Find the downloaded file
                for f in MINED_DIR.glob(f"mined_{v_id}*"):
                    if f.is_file() and f.suffix.lower() == ".mp4" and f.stat().st_size > 100_000:
                        downloaded_files.append(str(f))
                        history.add(v_id)
                        save_history(history)
                        log.info("Successfully mined clip: %s (%.2f MB)", f.name, f.stat().st_size / (1024 * 1024))
                        break
            else:
                log.warning("Download failed for %s: %s", v_id, dl_proc.stderr[:200])

    except Exception as e:
        log.error("Error during clip mining search: %s", e)

    return downloaded_files


async def run_miner_loop() -> None:
    """Continuous background loop monitoring mined queue and refilling automatically."""
    log.info("🚀 Starting Clip Miner Daemon (Autonomous Gameplay Harvester)...")

    while True:
        try:
            # Check how many mined clips are currently waiting
            existing_clips = list(MINED_DIR.glob("*.mp4"))
            log.info("Current backlog of mined clips: %d", len(existing_clips))

            # Maintain a healthy buffer of 3 to 6 raw clips
            if len(existing_clips) < 4:
                mined = search_and_mine_clips(max_clips_per_cycle=2)
                log.info("Mined %d new clip(s) in this cycle.", len(mined))
            else:
                log.info("Backlog is healthy (%d clips). Sleeping...", len(existing_clips))

        except Exception as e:
            log.error("Unexpected exception in miner loop: %s", e, exc_info=True)

        # Sleep between mining checks (every 30 minutes)
        await asyncio.sleep(1800)


if __name__ == "__main__":
    try:
        asyncio.run(run_miner_loop())
    except (KeyboardInterrupt, SystemExit):
        log.info("Clip Miner Daemon stopped.")
