"""
Studio Pipeline Worker Daemon for Core Market Bot.
Monitors video_studio/temp/mined_clips/, automatically triggers 9:16 vertical render,
applies transparent Logo 'C' watermark, Phonk music, viral hook/CTA badges,
and prepares multi-channel variations into video_studio/output/ready_queue/.
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [studio_worker]: %(message)s",
)
log = logging.getLogger("studio_worker")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "video_studio"))

from video_studio.core.channels import generate_multichannel_pack
from video_studio.core.engine import build_9_16_vertical_short, convert_to_mp4, detect_action_highlights
from video_studio.core.metadata import generate_clip_social_metadata

MINED_DIR = BASE_DIR / "video_studio" / "temp" / "mined_clips"
OUTPUT_DIR = BASE_DIR / "video_studio" / "output"
READY_QUEUE_DIR = OUTPUT_DIR / "ready_queue"
PROCESSED_DIR = BASE_DIR / "video_studio" / "temp" / "processed_clips"
META_FILE = OUTPUT_DIR / "metadata.json"

MINED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
READY_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

VIRAL_MUSIC_ROTATION = [
    "s3bzs_pr_funk",
    "kordhell_murder",
    "dxrk_rave",
    "hensonn_sahara",
    "ghostface_whynot",
    "yeat_money",
    "ken_carson_rage",
    "night_lovell_darklight",
    "tevvez_legend",
    "izzamuzzic_shootout",
]

VIRAL_HOOKS = [
    "POV: You finally found the zero-recoil config 😳",
    "Ranked lobbies are getting impossible 💀",
    "POV: When your crosshair literally locks on heads 🎯",
    "Is this aim assist or pure skill? 🤫",
    "They reported me 8 times until this clip...",
    "Is this config even legal? 💀",
    "When the entire squad is watching you clutch 🎯",
]

BADGE_STYLES = ["dark-neon", "solid-yellow", "minimal"]
LOGO_COLORWAYS = ["gold", "cyan", "crimson", "purple", "emerald", "platinum", "stealth"]


def save_clip_metadata(entry: dict) -> None:
    data = []
    if META_FILE.exists():
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    # Avoid duplicate filenames
    data = [x for x in data if x.get("filename") != entry.get("filename")]
    data.insert(0, entry)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def process_raw_video(raw_video_path: Path) -> list[str]:
    """Processes a single raw video into 3-5 multi-channel optimized shorts."""
    log.info("Processing raw video: %s", raw_video_path.name)
    generated_files = []

    # 1. Convert to standardized MP4 if needed
    clean_mp4 = str(BASE_DIR / "video_studio" / "temp" / f"std_{uuid.uuid4().hex[:8]}.mp4")
    if not convert_to_mp4(str(raw_video_path), clean_mp4):
        clean_mp4 = str(raw_video_path)

    # 2. Detect high action highlights
    cuts = detect_action_highlights(clean_mp4, max_highlights=3, clip_duration=20.0)
    if not cuts:
        cuts = [0.0]

    # 3. Generate multi-channel package for 3 selected Core Market identities
    chan_pack = generate_multichannel_pack(count=3, hook_theme=random.choice(VIRAL_HOOKS))

    for idx, item in enumerate(chan_pack):
        clip_id = uuid.uuid4().hex[:6]
        channel_id = item["channel_id"]
        out_filename = f"farm_{channel_id}_{clip_id}.mp4"
        out_filepath = str(READY_QUEUE_DIR / out_filename)
        public_filepath = str(OUTPUT_DIR / out_filename)

        start_t = cuts[idx % len(cuts)]
        assigned_music = VIRAL_MUSIC_ROTATION[idx % len(VIRAL_MUSIC_ROTATION)]
        assigned_badge = BADGE_STYLES[idx % len(BADGE_STYLES)]
        assigned_logo = LOGO_COLORWAYS[idx % len(LOGO_COLORWAYS)]

        log.info("Rendering Short #%d for %s (Music: %s, Logo: %s)...", idx + 1, item["channel_name"], assigned_music, assigned_logo)

        success = await asyncio.to_thread(
            build_9_16_vertical_short,
            video_path=clean_mp4,
            output_path=out_filepath,
            start_time=start_t,
            duration=20.0,
            watermark_top=item["title"],
            watermark_bottom="⚡ 1-Hour FREE Trial • Link in Bio →",
            layout_style="zoom",
            hook_y=180,
            cta_y=1360,
            badge_style=assigned_badge,
            music_track=assigned_music,
            music_volume=0.35,
            logo_variant=assigned_logo,
            logo_position="top_right",
            logo_size=115,
            logo_opacity=0.85,
            template_style="cyber_hud",
        )

        if success and os.path.exists(out_filepath):
            # Duplicate to public output folder for instant web panel preview
            shutil.copy2(out_filepath, public_filepath)

            meta_entry = {
                "title": item["title"],
                "description": item["description"],
                "hashtags": item["hashtags"].split(),
                "hashtags_string": item["hashtags"],
                "pinned_comment": item["pinned_comment"],
                "channel_name": item["channel_name"],
                "channel_handle": item["channel_handle"],
                "optimal_time": "18:30 - 21:30 (Prime Engagement)",
                "strategy_tip": f"Auto-Généré pour {item['channel_name']} avec musique {assigned_music}",
            }

            clip_entry = {
                "filename": out_filename,
                "title": f"[{item['channel_name']}] {item['title']}",
                "channel_name": item["channel_name"],
                "channel_handle": item["channel_handle"],
                "meta": meta_entry,
            }
            save_clip_metadata(clip_entry)
            generated_files.append(out_filepath)
            log.info("✅ Generated ready short: %s", out_filename)

    # Clean intermediate temp MP4
    if clean_mp4 != str(raw_video_path) and os.path.exists(clean_mp4):
        try:
            os.remove(clean_mp4)
        except Exception:
            pass

    # Move processed raw video to processed folder
    target_archive = PROCESSED_DIR / raw_video_path.name
    try:
        shutil.move(str(raw_video_path), str(target_archive))
    except Exception as e:
        log.warning("Could not archive processed raw video: %s", e)

    return generated_files


async def run_pipeline_worker_loop() -> None:
    """Watches mined_clips/ and renders incoming gameplay continuously."""
    log.info("🚀 Starting Studio Pipeline Worker (Automated 9:16 Video Factory)...")

    while True:
        try:
            raw_clips = list(MINED_DIR.glob("*.mp4"))
            if raw_clips:
                log.info("Found %d pending raw clip(s) to process.", len(raw_clips))
                for clip_path in raw_clips:
                    await process_raw_video(clip_path)
            else:
                pass
        except Exception as e:
            log.error("Error in studio worker loop: %s", e, exc_info=True)

        # Poll every 20 seconds
        await asyncio.sleep(20)


if __name__ == "__main__":
    try:
        asyncio.run(run_pipeline_worker_loop())
    except (KeyboardInterrupt, SystemExit):
        log.info("Studio Pipeline Worker stopped.")
