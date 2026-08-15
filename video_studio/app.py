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

from core.downloader import download_youtube_video
from core.engine import (
    NVENC_ACTIVE,
    build_9_16_vertical_short,
    convert_to_mp4,
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


def load_all_metadata() -> list[dict[str, Any]]:
    if not META_FILE.exists():
        return []
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
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
        "gpu_name": "NVIDIA GeForce RTX 3050" if NVENC_ACTIVE else "CPU Fallback",
    })


async def clips_handler(_: web.Request) -> web.Response:
    clips = load_all_metadata()
    return web.json_response(clips)


async def generate_handler(request: web.Request) -> web.Response:
    reader = await request.multipart()

    uploaded_filename = None
    local_video_path = None
    yt_url = None
    mode = "multi_shorts"
    script = ""
    voice_key = "en_gamer_christopher"
    sub_style = "hormozi_yellow"
    top_banner = "⚡ CORE MARKET • 1H FREE TRIAL"
    bottom_cta = "👉 LINK IN BIO • DISCORD.GG/NPXP9UK9JG"

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

    # 1. Acquire video source
    source_mp4 = None
    source_title = "Gameplay"

    if yt_url:
        log.info("Downloading YouTube video: %s", yt_url)
        yt_res = download_youtube_video(yt_url, str(TEMP_DIR))
        if not yt_res or not os.path.exists(yt_res["filepath"]):
            return web.json_response({"success": False, "error": "Could not download YouTube video."}, status=400)
        source_mp4 = yt_res["filepath"]
        source_title = yt_res.get("title", "YouTube Video")
    elif local_video_path and os.path.exists(local_video_path):
        source_title = Path(local_video_path).stem
        if not local_video_path.lower().endswith(".mp4"):
            log.info("Converting %s to MP4 via NVENC...", local_video_path)
            conv_out = str(TEMP_DIR / f"converted_{uuid.uuid4().hex[:8]}.mp4")
            if convert_to_mp4(local_video_path, conv_out):
                source_mp4 = conv_out
            else:
                source_mp4 = local_video_path
        else:
            source_mp4 = local_video_path
    else:
        return web.json_response({"success": False, "error": "No valid video file or YouTube URL provided."}, status=400)

    # 2. Voiceover & Subtitles (if script provided)
    audio_path = None
    subtitles_ass = None

    if script:
        log.info("Generating AI voiceover & word-level subtitles...")
        audio_out = str(TEMP_DIR / f"voice_{uuid.uuid4().hex[:8]}.mp3")
        ass_out = str(TEMP_DIR / f"subs_{uuid.uuid4().hex[:8]}.ass")

        success_tts, word_cues = await generate_voiceover(script, audio_out, voice_key=voice_key)
        if success_tts:
            audio_path = audio_out
            generate_hormozi_ass_subtitles(word_cues, ass_out, raw_text=script, style_theme=sub_style)
            subtitles_ass = ass_out

    # 3. Multi-Shorts or Full Video Render
    duration = get_video_duration(source_mp4)
    log.info("Source video duration: %.1f seconds", duration)

    generated_clips = []

    if mode == "multi_shorts":
        short_len = 30.0  # 30-second viral format
        num_shorts = max(1, min(5, int(duration // short_len)))
        if duration < 30.0:
            num_shorts = 1
            short_len = max(5.0, duration)

        for i in range(num_shorts):
            start_t = i * short_len
            clip_id = uuid.uuid4().hex[:6]
            out_filename = f"short_{i+1}_{clip_id}.mp4"
            out_filepath = str(OUTPUT_DIR / out_filename)

            log.info("Rendering Short %d/%d (Start: %.1fs, Len: %.1fs)...", i + 1, num_shorts, start_t, short_len)
            success = build_9_16_vertical_short(
                video_path=source_mp4,
                output_path=out_filepath,
                start_time=start_t,
                duration=short_len,
                audio_path=audio_path if i == 0 else None,
                subtitles_ass_path=subtitles_ass if i == 0 else None,
                watermark_top=top_banner,
                watermark_bottom=bottom_cta,
            )

            if success and os.path.exists(out_filepath):
                meta = generate_clip_social_metadata(clip_title=f"{source_title} - Part {i+1}")
                clip_entry = {
                    "filename": out_filename,
                    "title": f"Short #{i+1} • {source_title}",
                    "meta": meta,
                }
                save_clip_metadata(clip_entry)
                generated_clips.append(clip_entry)
    else:
        # Full single video
        clip_id = uuid.uuid4().hex[:6]
        out_filename = f"full_video_{clip_id}.mp4"
        out_filepath = str(OUTPUT_DIR / out_filename)

        render_len = min(duration, 60.0) if duration > 0 else 30.0
        success = build_9_16_vertical_short(
            video_path=source_mp4,
            output_path=out_filepath,
            start_time=0.0,
            duration=render_len,
            audio_path=audio_path,
            subtitles_ass_path=subtitles_ass,
            watermark_top=top_banner,
            watermark_bottom=bottom_cta,
        )

        if success and os.path.exists(out_filepath):
            meta = generate_clip_social_metadata(clip_title=source_title)
            clip_entry = {
                "filename": out_filename,
                "title": source_title,
                "meta": meta,
            }
            save_clip_metadata(clip_entry)
            generated_clips.append(clip_entry)

    return web.json_response({
        "success": True,
        "count": len(generated_clips),
        "clips": generated_clips,
    })


def create_app() -> web.Application:
    app = web.Application(client_max_size=1024 * 1024 * 500)  # Support up to 500MB video uploads
    app.router.add_get("/", index_handler)
    app.router.add_get("/api/status", status_handler)
    app.router.add_get("/api/clips", clips_handler)
    app.router.add_post("/api/generate", generate_handler)
    app.router.add_static("/static/", path=STATIC_DIR, name="static")
    app.router.add_static("/output/", path=OUTPUT_DIR, name="output")
    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("STUDIO_PORT", 5050))
    print(f"🚀 CORE STUDIO AI is running on http://localhost:{port}")
    print(f"⚡ Hardware Acceleration: {'NVIDIA NVENC (RTX 3050)' if NVENC_ACTIVE else 'CPU'}")
    web.run_app(app, host="127.0.0.1", port=port)
