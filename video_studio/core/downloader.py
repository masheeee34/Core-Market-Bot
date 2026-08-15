import logging
import os
import re
from typing import Any

import yt_dlp

log = logging.getLogger("studio.downloader")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")[:60]


def download_youtube_video(url: str, output_dir: str) -> dict[str, Any] | None:
    """Downloads a YouTube video in highest quality MP4 using yt-dlp."""
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": os.path.join(output_dir, "%(title)s_%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return None

            filename = ydl.prepare_filename(info)
            # Ensure it ends with .mp4 after merge
            if not filename.endswith(".mp4"):
                base, _ = os.path.splitext(filename)
                filename = base + ".mp4"

            return {
                "title": info.get("title", "YouTube Video"),
                "duration": info.get("duration", 0),
                "filepath": filename,
                "thumbnail": info.get("thumbnail", ""),
                "id": info.get("id", ""),
            }
    except Exception as e:
        log.error("Error downloading YouTube video: %s", e)
        return None
