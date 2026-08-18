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

        # Ensure video is standard MP4
        if not source_mp4.lower().endswith(".mp4"):
            task["message"] = "Converting raw gameplay to standard MP4 stream..."
            converted_path = str(TEMP_DIR / f"converted_{uuid.uuid4().hex[:8]}.mp4")
            conv_ok = await asyncio.to_thread(convert_to_mp4, source_mp4, converted_path)
            if conv_ok:
                source_mp4 = converted_path

        # Step 2: Voiceover & Subtitles (if requested)
        audio_path = None
        subtitles_ass = None

        if script:
            task["message"] = "Generating AI viral gamer voiceover (EdgeTTS)..."
            task["percent"] = 30
            tts_out = str(TEMP_DIR / f"tts_{uuid.uuid4().hex[:8]}.mp3")
            success_tts, word_cues = await generate_voiceover(script, tts_out, voice_key)

            if success_tts and os.path.exists(tts_out):
                audio_path = tts_out
                task["message"] = "Generating animated viral captions (ASS)..."
                task["percent"] = 40
                ass_out = str(TEMP_DIR / f"subs_{uuid.uuid4().hex[:8]}.ass")
                await asyncio.to_thread(
                    generate_hormozi_ass_subtitles,
                    word_cues,
                    ass_out,
                    raw_text=script,
                    style_theme=sub_style,
                )
                subtitles_ass = ass_out

        # Step 3: Intelligent Highlight Detection & Render
        duration = await asyncio.to_thread(get_video_duration, source_mp4)
        task["message"] = "Analyzing audio peaks & detecting top action moments..."
        task["percent"] = 45

        generated_clips = []

        if mode == "multi_shorts":
            if custom_start is not None and custom_start >= 0:
                start_timestamps = [custom_start]
            else:
                # Automatic intelligent peak action detection
                start_timestamps = await asyncio.to_thread(
                    detect_action_highlights,
                    source_mp4,
                    max_highlights=num_clips,
                    clip_duration=clip_len,
                )

            total_cuts = len(start_timestamps) if start_timestamps else 1
            if not start_timestamps:
                start_timestamps = [0.0]

            for idx, start_t in enumerate(start_timestamps):
                clip_id = uuid.uuid4().hex[:6]
                out_filename = f"short_{idx+1}_{clip_id}.mp4"
                out_filepath = str(OUTPUT_DIR / out_filename)

                start_min = int(start_t // 60)
                start_sec = int(start_t % 60)
                task["message"] = f"Rendering Action Short #{idx+1}/{total_cuts} at {start_min:02d}:{start_sec:02d}..."
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
                )

                if success and os.path.exists(out_filepath):
                    meta = generate_clip_social_metadata(
                        clip_title=top_banner if top_banner else None,
                        hook_text=top_banner,
                    )
                    clip_entry = {
                        "filename": out_filename,
                        "title": top_banner or f"Action Highlight #{idx+1} ({start_min:02d}:{start_sec:02d})",
                        "meta": meta,
                    }
                    save_clip_metadata(clip_entry)
                    generated_clips.append(clip_entry)
        else:
            # Single Full Video
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
    finally:
        # Clean up temporary upload and intermediate conversion files
        if local_video_path and os.path.exists(local_video_path) and "temp" in local_video_path.lower():
            try:
                os.remove(local_video_path)
            except Exception:
                pass


async def generate_handler(request: web.Request) -> web.Response:
    reader = await request.multipart()

    uploaded_filename = None
    local_video_path = None
    yt_url = None
    mode = "multi_shorts"
    clip_len = 30.0
    num_clips = 3
    custom_start = None
    script = ""
    voice_key = "en_gamer_christopher"
    sub_style = "hormozi_yellow"
    top_banner = "POV: You finally found the zero-recoil config 😳"
    bottom_cta = "⚡ 1-Hour FREE Trial • Link in Bio →"
    hook_y = 180
    cta_y = 1360
    badge_style = "dark-neon"
    layout_style = "zoom"
    music_track = "none"
    music_volume = 0.35
    custom_music_url = ""

    while True:
        part = await reader.next()
        if part is None:
            break

        name = part.name
        if name == "file":
            uploaded_filename = part.filename
            if uploaded_filename:
                temp_upload_path = TEMP_DIR / f"upload_{uuid.uuid4().hex[:8]}_{uploaded_filename}"
                with open(temp_upload_path, "wb") as f:
                    while True:
                        chunk = await part.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
                local_video_path = str(temp_upload_path)
        else:
            value = await part.text()
            if name == "youtube_url":
                yt_url = value.strip()
            elif name == "mode":
                mode = value
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
                        # Support both seconds (45) and MM:SS (01:25) format
                        if ":" in value:
                            m, s = value.strip().split(":")
                            custom_start = float(m) * 60 + float(s)
                        else:
                            custom_start = float(value)
                    except ValueError:
                        custom_start = None
            elif name == "script":
                script = value.strip()
            elif name == "voice":
                voice_key = value
            elif name == "sub_style":
                sub_style = value
            elif name == "top_banner":
                top_banner = value
            elif name == "bottom_cta":
                bottom_cta = value
            elif name == "hook_y":
                try:
                    hook_y = int(float(value))
                except ValueError:
                    hook_y = 180
            elif name == "cta_y":
                try:
                    cta_y = int(float(value))
                except ValueError:
                    cta_y = 1360
            elif name == "badge_style":
                badge_style = value
            elif name == "layout_style":
                layout_style = value
            elif name == "music_track":
                music_track = value.strip()
            elif name == "music_volume":
                try:
                    music_volume = float(value)
                except ValueError:
                    music_volume = 0.35
            elif name == "custom_music_url":
                custom_music_url = value.strip()

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
        )
    )

    return web.json_response({
        "success": True,
        "task_id": task_id,
    })


def create_app() -> web.Application:
    app = web.Application(client_max_size=1024 * 1024 * 500)  # Support up to 500MB video uploads
    app.router.add_get("/", index_handler)
    app.router.add_get("/api/status", status_handler)
    app.router.add_get("/api/clips", clips_handler)
    app.router.add_get("/api/task_status/{task_id}", task_status_handler)
    app.router.add_post("/api/generate", generate_handler)
    app.router.add_static("/static/", path=STATIC_DIR, name="static")
    app.router.add_static("/output/", path=OUTPUT_DIR, name="output")
    music_dir = BASE_DIR / "assets" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    app.router.add_static("/music/", path=music_dir, name="music")
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("STUDIO_PORT", 5050))
    print(f"🚀 CORE STUDIO AI is running on http://localhost:{port}")
    print(f"⚡ Hardware Acceleration: {'NVIDIA NVENC GPU' if NVENC_ACTIVE else 'VPS Multi-Core CPU (4 vCPUs)'}")
    web.run_app(app, host="127.0.0.1", port=port)
