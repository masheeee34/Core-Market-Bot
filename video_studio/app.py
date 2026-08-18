import asyncio
import json
import logging
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.channels import get_channel_profiles, generate_multichannel_pack
from core.downloader import download_youtube_video
from core.engine import (
    NVENC_ACTIVE,
    build_9_16_vertical_short,
    convert_to_mp4,
    detect_action_highlights,
    get_video_duration,
)
from core.metadata import generate_clip_social_metadata
from core.subtitles import generate_hormozi_ass_subtitles
from core.tts import generate_voiceover

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("studio.app")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
META_FILE = OUTPUT_DIR / "metadata.json"

# In-memory background task tracking
TASKS: dict[str, dict[str, Any]] = {}


def load_all_metadata() -> list[dict[str, Any]]:
    if not META_FILE.exists():
        return []
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            if isinstance(item, dict):
                meta = item.get("meta") or {}
                t = meta.get("title", "")
                if t.startswith("upload_") or " - Clutch Highlight" in t or t.endswith(".mp4"):
                    clean_title = "POV: You finally found the zero-recoil config 😳"
                    meta["title"] = clean_title
                    if "description" in meta:
                        lines = meta["description"].split("\n\n")
                        meta["description"] = f"{clean_title}\n\nTesting the cleanest setup on latest patch. Smooth tracking & zero recoil.\n\n" + (lines[-1] if len(lines) > 1 else "#warzone #cod #gaming #fyp")
                    item["title"] = clean_title
        return data
    except Exception:
        return []


def save_clip_metadata(clip_info: dict[str, Any]) -> None:
    data = load_all_metadata()
    data.insert(0, clip_info)
    try:
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error("Error saving metadata: %s", e)


async def index_handler(_: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")


async def status_handler(_: web.Request) -> web.Response:
    return web.json_response({
        "nvenc_gpu_active": NVENC_ACTIVE,
        "gpu_name": "NVIDIA NVENC GPU" if NVENC_ACTIVE else "VPS Multi-Core CPU (4 vCPUs)",
    })


async def channels_handler(_: web.Request) -> web.Response:
    return web.json_response({
        "success": True,
        "channels": get_channel_profiles()
    })


async def logos_handler(_: web.Request) -> web.Response:
    logos = [
        {"id": "gold", "name": "Gold Neon (#FFE600)", "desc": "Signature Core Market", "hex": "#FFE600"},
        {"id": "cyan", "name": "Cyber Cyan", "desc": "High-Tech Electric", "hex": "#00F0FF"},
        {"id": "crimson", "name": "Crimson Wine", "desc": "Original Cavaliers", "hex": "#860038"},
        {"id": "purple", "name": "Purple Vortex", "desc": "Gamer Neon Pink", "hex": "#A855F7"},
        {"id": "emerald", "name": "Emerald Green", "desc": "Acid Mint Precision", "hex": "#10B981"},
        {"id": "platinum", "name": "Pure Platinum", "desc": "Clean Minimalist White", "hex": "#FFFFFF"},
        {"id": "stealth", "name": "Dark Stealth", "desc": "Tactical Shadow Obsidian", "hex": "#64748B"},
    ]
    return web.json_response({"success": True, "logos": logos})


async def clips_handler(_: web.Request) -> web.Response:
    clips = load_all_metadata()
    return web.json_response({"success": True, "clips": clips})


async def task_status_handler(request: web.Request) -> web.Response:
    task_id = request.match_info.get("task_id", "")
    task = TASKS.get(task_id)
    if not task:
        return web.json_response({"status": "error", "error": "Task not found."}, status=404)
    return web.json_response(task)


async def run_generation_background(
    task_id: str,
    yt_url: str | None,
    local_video_path: str | None,
    mode: str,
    clip_len: float,
    num_clips: int,
    custom_start: float | None,
    script: str,
    voice_key: str,
    sub_style: str,
    top_banner: str,
    bottom_cta: str,
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
) -> None:
    task = TASKS.get(task_id)
    if not task:
        return

    try:
        # Step 1: Download or locate source video
        source_mp4 = None
        source_title = "Gameplay"
        if yt_url:
            task["message"] = "Downloading YouTube gameplay in HD 1080p..."
            task["percent"] = 15
            yt_res = await asyncio.to_thread(download_youtube_video, yt_url, str(TEMP_DIR))
            if not yt_res or not yt_res.get("filepath"):
                task["status"] = "error"
                task["error"] = "Failed to download YouTube video."
                return
            source_mp4 = yt_res["filepath"]
            source_title = yt_res.get("title", "YouTube Video")
        elif local_video_path:
            task["message"] = "Processing uploaded gameplay footage..."
            task["percent"] = 15
            source_mp4 = local_video_path
            source_title = Path(local_video_path).stem

        if not source_mp4 or not os.path.exists(source_mp4):
            task["status"] = "error"
            task["error"] = "Source video file not found."
            return

        duration = await asyncio.to_thread(get_video_duration, source_mp4)
        task["percent"] = 25

        # Step 2: Voiceover / Script (if provided)
        audio_path = None
        subtitles_ass = None
        if script and script.strip():
            task["message"] = "Generating AI Voiceover narration..."
            task["percent"] = 35
            audio_path = str(TEMP_DIR / f"voice_{uuid.uuid4().hex[:6]}.mp3")
            gen_ok = await asyncio.to_thread(generate_voiceover, script, voice_key, audio_path)
            if gen_ok and os.path.exists(audio_path):
                task["message"] = "Generating dynamic animated subtitles..."
                task["percent"] = 45
                subtitles_ass = str(TEMP_DIR / f"subs_{uuid.uuid4().hex[:6]}.ass")
                await asyncio.to_thread(
                    build_ass_subtitles,
                    text=script,
                    duration=clip_len,
                    output_path=subtitles_ass,
                    style=sub_style,
                )

        generated_clips = []

        # ──────────────────────────────────────────────────────────────
        # MODE A: Multi-Channel Farm Batch (1 Clip -> Multiple Channels)
        # ──────────────────────────────────────────────────────────────
        if mode in ("farm_batch", "multi_channels"):
            farm_channels_count = max(2, min(num_clips, 5))
            chan_pack = generate_multichannel_pack(
                base_title=top_banner,
                hook_text=top_banner,
                num_channels=farm_channels_count,
            )

            viral_music_rotation = [
                "s3bzs_pr_funk",
                "kordhell_murder",
                "dxrk_rave",
                "hensonn_sahara",
                "yeat_money",
            ]

            badge_styles_rotation = ["dark-neon", "solid-yellow", "minimal"]

            start_t = custom_start if (custom_start is not None and custom_start >= 0) else 0.0

            for idx, item in enumerate(chan_pack):
                clip_id = uuid.uuid4().hex[:6]
                out_filename = f"farm_{item['channel_id']}_{clip_id}.mp4"
                out_filepath = str(OUTPUT_DIR / out_filename)
                task["message"] = f"Rendering Channel Short #{idx+1}/{len(chan_pack)} ({item['channel_name']})..."
                task["percent"] = 50 + int((idx / len(chan_pack)) * 45)

                assigned_music = music_track if music_track not in ("none", "random_viral") else viral_music_rotation[idx % len(viral_music_rotation)]
                assigned_badge = badge_styles_rotation[idx % len(badge_styles_rotation)]

                success = await asyncio.to_thread(
                    build_9_16_vertical_short,
                    video_path=source_mp4,
                    output_path=out_filepath,
                    start_time=start_t,
                    duration=clip_len,
                    audio_path=audio_path,
                    subtitles_ass_path=subtitles_ass,
                    watermark_top=item["title"],
                    watermark_bottom=bottom_cta,
                    layout_style=layout_style,
                    hook_y=hook_y,
                    cta_y=cta_y,
                    badge_style=assigned_badge,
                    music_track=assigned_music,
                    music_volume=music_volume,
                    custom_music_url=custom_music_url,
                    logo_variant=logo_variant,
                    logo_position=logo_position,
                    logo_size=logo_size,
                    logo_opacity=logo_opacity,
                    template_style=template_style,
                )

                if success and os.path.exists(out_filepath):
                    meta_entry = {
                        "title": item["title"],
                        "description": item["description"],
                        "hashtags": item["hashtags"].split(),
                        "hashtags_string": item["hashtags"],
                        "pinned_comment": item["pinned_comment"],
                        "channel_name": item["channel_name"],
                        "channel_handle": item["channel_handle"],
                        "optimal_time": "18:30 - 21:30 (Prime Engagement)",
                        "strategy_tip": f"Assignée à {item['channel_name']} avec musique {assigned_music}",
                    }
                    clip_entry = {
                        "filename": out_filename,
                        "title": f"[{item['channel_name']}] {item['title']}",
                        "channel_name": item["channel_name"],
                        "channel_handle": item["channel_handle"],
                        "meta": meta_entry,
                    }
                    save_clip_metadata(clip_entry)
                    generated_clips.append(clip_entry)

        elif mode == "multi_shorts":
            task["message"] = "Detecting high-action moments..."
            task["percent"] = 40
            cuts = await asyncio.to_thread(
                detect_action_highlights,
                video_path=source_mp4,
                clip_duration=clip_len,
                num_clips=num_clips,
                custom_start=custom_start,
            )

            total_cuts = len(cuts)
            for idx, start_t in enumerate(cuts):
                clip_id = uuid.uuid4().hex[:6]
                out_filename = f"short_{idx+1}_{clip_id}.mp4"
                out_filepath = str(OUTPUT_DIR / out_filename)
                task["message"] = f"Rendering Action Short #{idx+1}/{total_cuts}..."
                task["percent"] = 50 + int((idx / total_cuts) * 45)

                success = await asyncio.to_thread(
                    build_9_16_vertical_short,
                    video_path=source_mp4,
                    output_path=out_filepath,
                    start_time=start_t,
                    duration=clip_len,
                    audio_path=audio_path if idx == 0 else None,
                    subtitles_ass_path=subtitles_ass if idx == 0 else None,
                    watermark_top=top_banner,
                    watermark_bottom=bottom_cta,
                    layout_style=layout_style,
                    hook_y=hook_y,
                    cta_y=cta_y,
                    badge_style=badge_style,
                    music_track=music_track,
                    music_volume=music_volume,
                    custom_music_url=custom_music_url,
                    logo_variant=logo_variant,
                    logo_position=logo_position,
                    logo_size=logo_size,
                    logo_opacity=logo_opacity,
                    template_style=template_style,
                )

                if success and os.path.exists(out_filepath):
                    meta = generate_clip_social_metadata(
                        clip_title=top_banner if top_banner else None,
                        hook_text=top_banner,
                    )
                    clip_entry = {
                        "filename": out_filename,
                        "title": top_banner or f"Action Highlight #{idx+1}",
                        "meta": meta,
                    }
                    save_clip_metadata(clip_entry)
                    generated_clips.append(clip_entry)
        else:
            clip_id = uuid.uuid4().hex[:6]
            out_filename = f"full_video_{clip_id}.mp4"
            out_filepath = str(OUTPUT_DIR / out_filename)
            render_len = min(duration, 60.0) if duration > 0 else 30.0

            task["message"] = "Rendering Full Video in 9:16 Vertical..."
            task["percent"] = 75

            start_t = custom_start if (custom_start is not None and custom_start >= 0) else 0.0

            success = await asyncio.to_thread(
                build_9_16_vertical_short,
                video_path=source_mp4,
                output_path=out_filepath,
                start_time=start_t,
                duration=render_len,
                audio_path=audio_path,
                subtitles_ass_path=subtitles_ass,
                watermark_top=top_banner,
                watermark_bottom=bottom_cta,
                layout_style=layout_style,
                hook_y=hook_y,
                cta_y=cta_y,
                badge_style=badge_style,
                music_track=music_track,
                music_volume=music_volume,
                custom_music_url=custom_music_url,
                logo_variant=logo_variant,
                logo_position=logo_position,
                logo_size=logo_size,
                logo_opacity=logo_opacity,
                template_style=template_style,
            )

            if success and os.path.exists(out_filepath):
                meta = generate_clip_social_metadata(
                    clip_title=top_banner if top_banner else None,
                    hook_text=top_banner,
                )
                clip_entry = {
                    "filename": out_filename,
                    "title": top_banner or "Viral Gameplay Short",
                    "meta": meta,
                }
                save_clip_metadata(clip_entry)
                generated_clips.append(clip_entry)

        task["status"] = "done"
        task["percent"] = 100
        task["message"] = f"Finished! Generated {len(generated_clips)} action clip(s) successfully 🎉"
        task["clips"] = generated_clips

    except Exception as e:
        log.error("Fatal error in generation task %s: %s", task_id, e, exc_info=True)
        task["status"] = "error"
        task["error"] = str(e)


async def generate_handler(request: web.Request) -> web.Response:
    reader = await request.multipart()

    yt_url = None
    local_video_path = None
    mode = "multi_shorts"
    clip_len = 30.0
    num_clips = 3
    custom_start = None
    script = ""
    voice_key = "adam"
    sub_style = "beast"
    top_banner = "POV: You finally found the zero-recoil config 😳"
    bottom_cta = "⚡ 1-Hour FREE Trial • Link in Bio →"
    layout_style = "zoom"
    hook_y = 180
    cta_y = 1360
    badge_style = "dark-neon"
    music_track = "none"
    music_volume = 0.35
    custom_music_url = ""
    logo_variant = "gold"
    logo_position = "top_right"
    logo_size = 120
    logo_opacity = 0.85
    template_style = "cyber_hud"

    while True:
        part = await reader.next()
        if part is None:
            break

        if part.name == "file":
            filename = part.filename or f"upload_{uuid.uuid4().hex[:8]}.mp4"
            target_path = TEMP_DIR / f"upload_{uuid.uuid4().hex[:8]}_{filename}"
            with open(target_path, "wb") as f:
                while True:
                    chunk = await part.read_chunk(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            local_video_path = str(target_path)

        elif part.form_name:
            name = part.name
            value = (await part.read()).decode("utf-8", errors="ignore").strip()

            if name == "youtube_url":
                yt_url = value.strip()
            elif name == "mode":
                mode = value.strip()
            elif name == "clip_len":
                try:
                    clip_len = float(value)
                except ValueError:
                    clip_len = 30.0
            elif name == "num_clips":
                try:
                    num_clips = int(value)
                except ValueError:
                    num_clips = 3
            elif name == "custom_start":
                if value.strip():
                    try:
                        if ":" in value:
                            parts = value.split(":")
                            custom_start = float(parts[0]) * 60 + float(parts[1])
                        else:
                            custom_start = float(value.replace("s", ""))
                    except ValueError:
                        custom_start = None
            elif name == "script":
                script = value.strip()
            elif name == "voice":
                voice_key = value.strip()
            elif name == "sub_style":
                sub_style = value.strip()
            elif name == "top_banner":
                top_banner = value.strip()
            elif name == "bottom_cta":
                bottom_cta = value.strip()
            elif name == "hook_y":
                try: hook_y = int(float(value))
                except ValueError: hook_y = 180
            elif name == "cta_y":
                try: cta_y = int(float(value))
                except ValueError: cta_y = 1360
            elif name == "badge_style":
                badge_style = value.strip()
            elif name == "layout_style":
                layout_style = value.strip()
            elif name == "music_track":
                music_track = value.strip()
            elif name == "music_volume":
                try:
                    music_volume = float(value)
                except ValueError:
                    music_volume = 0.35
            elif name == "custom_music_url":
                custom_music_url = value.strip()
            elif name == "logo_variant":
                logo_variant = value.strip()
            elif name == "logo_position":
                logo_position = value.strip()
            elif name == "logo_size":
                try: logo_size = int(value)
                except ValueError: logo_size = 120
            elif name == "logo_opacity":
                try: logo_opacity = float(value)
                except ValueError: logo_opacity = 0.85
            elif name == "template_style":
                template_style = value.strip()

    if not yt_url and not local_video_path:
        return web.json_response({"success": False, "error": "Please provide a video file or YouTube URL."}, status=400)

    task_id = uuid.uuid4().hex[:8]
    TASKS[task_id] = {
        "status": "running",
        "percent": 10,
        "message": "Starting intelligent action clipping job...",
        "clips": [],
    }

    asyncio.create_task(
        run_generation_background(
            task_id=task_id,
            yt_url=yt_url,
            local_video_path=local_video_path,
            mode=mode,
            clip_len=clip_len,
            num_clips=num_clips,
            custom_start=custom_start,
            script=script,
            voice_key=voice_key,
            sub_style=sub_style,
            top_banner=top_banner,
            bottom_cta=bottom_cta,
            layout_style=layout_style,
            hook_y=hook_y,
            cta_y=cta_y,
            badge_style=badge_style,
            music_track=music_track,
            music_volume=music_volume,
            custom_music_url=custom_music_url,
            logo_variant=logo_variant,
            logo_position=logo_position,
            logo_size=logo_size,
            logo_opacity=logo_opacity,
            template_style=template_style,
        )
    )

    return web.json_response({
        "success": True,
        "task_id": task_id,
    })


def create_app() -> web.Application:
    app = web.Application(client_max_size=1024 * 1024 * 500)
    app.router.add_get("/", index_handler)
    app.router.add_get("/api/status", status_handler)
    app.router.add_get("/api/channels", channels_handler)
    app.router.add_get("/api/logos", logos_handler)
    app.router.add_get("/api/clips", clips_handler)
    app.router.add_get("/api/task_status/{task_id}", task_status_handler)
    app.router.add_post("/api/generate", generate_handler)
    app.router.add_static("/static/", path=STATIC_DIR, name="static")
    app.router.add_static("/output/", path=OUTPUT_DIR, name="output")
    music_dir = BASE_DIR / "assets" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    app.router.add_static("/music/", path=music_dir, name="music")
    logos_dir = BASE_DIR / "assets" / "logos"
    logos_dir.mkdir(parents=True, exist_ok=True)
    app.router.add_static("/logos/", path=logos_dir, name="logos")
    avatars_dir = BASE_DIR / "assets" / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    app.router.add_static("/avatars/", path=avatars_dir, name="avatars")
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("STUDIO_PORT", 5050))
    print(f"🚀 CORE STUDIO AI is running on http://localhost:{port}")
    print(f"⚡ Hardware Acceleration: {'NVIDIA NVENC GPU' if NVENC_ACTIVE else 'VPS Multi-Core CPU (4 vCPUs)'}")
    web.run_app(app, host="127.0.0.1", port=port)
