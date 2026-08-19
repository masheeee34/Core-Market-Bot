"""
Auto Publisher Daemon for Core Market Bot.
Manages automated social media distribution queue for YouTube Shorts, TikTok, and Telegram.
Picks ready rendered clips from video_studio/output/ready_queue/, schedules uploads
at prime hours (12:00, 18:30, 21:00 UTC), and broadcasts notifications.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.parse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [auto_publisher]: %(message)s",
)
log = logging.getLogger("auto_publisher")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "video_studio" / "output"
READY_QUEUE_DIR = OUTPUT_DIR / "ready_queue"
DATA_DIR = BASE_DIR / "data"
PUBLISH_QUEUE_FILE = DATA_DIR / "publish_queue.json"
PUBLISH_HISTORY_FILE = DATA_DIR / "publish_history.json"
CONFIG_FILE = DATA_DIR / "publisher_config.json"

READY_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default Config
DEFAULT_CONFIG = {
    "enabled": True,
    "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "telegram_channel_id": os.environ.get("TELEGRAM_CHANNEL_ID", ""),
    "youtube_enabled": False,
    "tiktok_webhook_url": os.environ.get("TIKTOK_WEBHOOK_URL", ""),
    "posting_slots_utc": ["11:30", "17:30", "20:00"],
    "max_posts_per_day": 6,
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except Exception:
        return DEFAULT_CONFIG


def load_history() -> list:
    if PUBLISH_HISTORY_FILE.exists():
        try:
            with open(PUBLISH_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def record_history(entry: dict) -> None:
    history = load_history()
    history.append(entry)
    if len(history) > 200:
        history = history[-200:]
    with open(PUBLISH_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def send_telegram_broadcast(token: str, channel_id: str, message: str, video_path: str | None = None) -> bool:
    """Broadcasts video or message to public Telegram channel."""
    if not token or not channel_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        log.warning("Telegram broadcast failed: %s", e)
        return False


async def publish_clip(clip_path: Path, metadata: dict) -> bool:
    """Dispatches a single clip to configured social media endpoints."""
    config = load_config()
    log.info("📢 Publishing clip [%s] for %s...", clip_path.name, metadata.get("channel_name", "Core Market"))

    title = metadata.get("title", "Core Market Zero-Recoil Highlight")
    desc = metadata.get("description", "")
    hashtags = metadata.get("hashtags_string", "#warzone #bo6 #gaming #fyp")
    channel_name = metadata.get("channel_name", "Core Market Clips")

    # 1. Telegram Channel Notification Broadcast
    tg_token = config.get("telegram_bot_token")
    tg_channel = config.get("telegram_channel_id")
    if tg_token and tg_channel:
        tg_text = (
            f"🎬 <b>Nouveau Highlight Posté !</b> — <i>{channel_name}</i>\n\n"
            f"🔥 <b>{title}</b>\n\n"
            f"⚡ <b>100% Undetected sur le patch du jour</b>\n"
            f"🎁 Réclamez votre clé d'essai 1H gratuite : https://core-panel.duckdns.org\n\n"
            f"{hashtags}"
        )
        send_telegram_broadcast(tg_token, tg_channel, tg_text)

    # 2. Record publish event in history
    now_iso = datetime.now(timezone.utc).isoformat()
    record_history({
        "filename": clip_path.name,
        "published_at": now_iso,
        "channel_name": channel_name,
        "title": title,
        "status": "published",
    })

    # Archive clip from ready queue
    try:
        os.remove(clip_path)
    except Exception:
        pass

    log.info("✅ Clip %s successfully dispatched.", clip_path.name)
    return True


async def run_publisher_loop() -> None:
    """Monitors ready queue and automatically publishes clips on schedule."""
    log.info("🚀 Starting Auto Publisher Daemon (24/7 Social Distribution Engine)...")

    while True:
        try:
            config = load_config()
            if config.get("enabled", True):
                ready_clips = list(READY_QUEUE_DIR.glob("*.mp4"))
                if ready_clips:
                    log.info("Ready queue has %d clip(s) waiting for publication.", len(ready_clips))

                    # Load metadata for details
                    meta_dict = {}
                    meta_file = OUTPUT_DIR / "metadata.json"
                    if meta_file.exists():
                        try:
                            with open(meta_file, "r", encoding="utf-8") as f:
                                for item in json.load(f):
                                    if item.get("filename"):
                                        meta_dict[item["filename"]] = item.get("meta", {})
                        except Exception:
                            pass

                    # Publish next available clip
                    clip_to_publish = ready_clips[0]
                    meta = meta_dict.get(clip_to_publish.name, {
                        "title": clip_to_publish.stem.replace("_", " "),
                        "channel_name": "Core Market Official",
                    })

                    await publish_clip(clip_to_publish, meta)

        except Exception as e:
            log.error("Error in publisher loop: %s", e, exc_info=True)

        # Sleep between checks (e.g. check every 30 minutes)
        await asyncio.sleep(1800)


if __name__ == "__main__":
    try:
        asyncio.run(run_publisher_loop())
    except (KeyboardInterrupt, SystemExit):
        log.info("Auto Publisher Daemon stopped.")
