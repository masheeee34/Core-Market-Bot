"""
Content Engine Cog — /render_clip Discord command.
Sends a gameplay video to the VPS FFmpeg pipeline and returns
ready-to-post TikTok/Shorts clips directly in Discord with live real-time progress bar.
"""

import asyncio
import io
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Callable

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("ticketbot.content")

STUDIO_URL = os.getenv("STUDIO_URL", "http://127.0.0.1:5050")

# ─────────────────────────────────────────────────────────────
#  DESIGN SYSTEM — Sleek, Minimal, Modern Tech Embeds
# ─────────────────────────────────────────────────────────────

COLOR_PRIMARY = 0x0070FF  # Electric Blue
COLOR_SUCCESS = 0x10B981  # Emerald Green
COLOR_ALERT   = 0xE11D48  # Crimson Red
COLOR_WARNING = 0xF59E0B  # Amber Gold


def render_progress_bar(percent: int, width: int = 16) -> str:
    percent = max(0, min(100, percent))
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"`[{bar}]` **{percent}%**"


def embed_render_started(
    task_id: str,
    filename: str,
    percent: int = 15,
    message: str = "Intelligent action detection & multi-clip rendering in progress…",
) -> discord.Embed:
    e = discord.Embed(
        title="🎬  Rendering Pipeline Active",
        description=(
            f"> Your gameplay video is being processed in background on the VPS.\n\n"
            f"▸ **Source File :** `{filename}`\n"
            f"▸ **Task Identifier :** `{task_id}`\n"
            f"▸ **Output Format :** `9:16 Vertical (1080x1920) for TikTok/Shorts`\n"
            f"▸ **Live Progress :** {render_progress_bar(percent)}\n"
            f"▸ **Status :** `{message}`\n\n"
            f"──────────────────────────────────────────\n"
            f"⚙️ *Rendering on VPS with multi-threaded FFmpeg engine…*"
        ),
        color=COLOR_PRIMARY,
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text="CORE STUDIO • FFmpeg NVENC/CPU Pipeline")
    return e


def embed_render_done(clips: list[dict], task_id: str) -> discord.Embed:
    clips_list = ""
    for i, c in enumerate(clips[:5], 1):
        meta = c.get("meta", {})
        title = meta.get("title", f"Action Highlight #{i}")[:45]
        time_slot = meta.get("optimal_time", "Evening Prime (18:30 - 21:30)")
        clips_list += f"▸ **Clip #{i} :** `{title}`\n  *Best upload window:* `{time_slot}`\n\n"

    e = discord.Embed(
        title=f"✅  {len(clips)} Short(s) Ready to Post",
        description=(
            f"> High-intensity action clips have been successfully cropped, formatted, and rendered.\n\n"
            f"{clips_list}"
            f"──────────────────────────────────────────\n"
            f"📥 *All `.mp4` video files and copy-paste social metadata are attached below.*"
        ),
        color=COLOR_SUCCESS,
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text="CORE STUDIO • Processing Complete")
    return e


def embed_render_error(error: str) -> discord.Embed:
    e = discord.Embed(
        title="⛔  Pipeline Rendering Error",
        description=(
            f"> An unexpected error occurred while processing the video.\n\n"
            f"▸ **Error Detail :** `{error[:140]}`\n\n"
            f"──────────────────────────────────────────\n"
            f"ℹ️ *Please ensure the file is a valid video format (MP4, MKV, MOV) under 500 MB.*"
        ),
        color=COLOR_ALERT,
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text="CORE STUDIO • Error Logged")
    return e


def embed_metadata_card(meta: dict, clip_num: int) -> discord.Embed:
    e = discord.Embed(
        title=f"📋  Clip #{clip_num} — Social Copy & Strategy",
        description=(
            f"**Recommended Title / Hook**\n"
            f"```{meta.get('title', 'Dominating every lobby with this setup ⚡')}```\n"
            f"**Hashtags to Copy**\n"
            f"```{meta.get('hashtags_string', '#BO7 #Warzone #Gaming #FYP')}```\n"
            f"**Pinned Comment (Anti-Shadowban)**\n"
            f"```{meta.get('pinned_comment', '🎁 Free 1H Trial in bio link!')}```\n"
            f"▸ **Recommended Posting Slot :** `{meta.get('optimal_time', '18:30 - 21:30')}`\n"
            f"▸ **Strategy :** *{meta.get('strategy_tip', 'Maximum evening gaming audience retention.')}*"
        ),
        color=COLOR_WARNING,
    )
    e.set_footer(text="CORE STUDIO • Ready to Publish on TikTok / Shorts / Reels")
    return e


# ─────────────────────────────────────────────────────────────
#  STUDIO API HELPERS
# ─────────────────────────────────────────────────────────────

async def _submit_render(
    video_bytes: bytes | None = None,
    filename: str | None = None,
    yt_url: str | None = None,
    num_clips: int = 3,
) -> dict[str, Any]:
    form = aiohttp.FormData()
    if video_bytes and filename:
        form.add_field("file", video_bytes, filename=filename, content_type="video/mp4")
    if yt_url:
        form.add_field("youtube_url", yt_url)
    form.add_field("mode", "multi_shorts")
    form.add_field("num_clips", str(num_clips))
    form.add_field("clip_len", "30")
    form.add_field("top_banner", "POV: You finally found the zero-recoil config 😳")
    form.add_field("bottom_cta", "⚡ 1-Hour FREE Trial : Link in Bio")

    timeout = aiohttp.ClientTimeout(total=180)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"{STUDIO_URL}/api/generate", data=form) as r:
            if r.status != 200:
                text = await r.text()
                try:
                    err_json = json.loads(text)
                    return {"success": False, "error": err_json.get("error", text)}
                except Exception:
                    return {"success": False, "error": f"HTTP {r.status}: {text[:120]}"}
            return await r.json()


async def _poll_task_live(
    task_id: str,
    interaction: discord.Interaction,
    filename: str,
    timeout: int = 300,
) -> dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + timeout
    last_percent = -1

    async with aiohttp.ClientSession() as session:
        while asyncio.get_event_loop().time() < deadline:
            try:
                async with session.get(f"{STUDIO_URL}/api/task_status/{task_id}") as r:
                    if r.status == 200:
                        data = await r.json()
                        status = data.get("status")
                        percent = data.get("percent", 20)
                        message = data.get("message", "Processing...")

                        if percent != last_percent and status != "done":
                            last_percent = percent
                            try:
                                await interaction.edit_original_response(
                                    embed=embed_render_started(task_id, filename, percent, message)
                                )
                            except Exception:
                                pass

                        if status in ("done", "error"):
                            return data
            except Exception as e:
                log.debug("Polling error for task %s: %s", task_id, e)

            await asyncio.sleep(2.5)

    return {"status": "error", "error": "Timeout — rendering took longer than expected."}


async def _download_clip(filename: str) -> bytes | None:
    url = f"{STUDIO_URL}/output/{filename}"
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as r:
            if r.status == 200:
                return await r.read()
    return None


# ─────────────────────────────────────────────────────────────
#  COG
# ─────────────────────────────────────────────────────────────

class ContentEngine(commands.Cog):
    """Pillar 3 — Content Engine & TikTok/Shorts Video Automation."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="render_clip",
        description="🎬 Upload raw gameplay or YouTube URL → VPS generates 9:16 Shorts ready for TikTok/YT",
    )
    @app_commands.describe(
        video="Raw gameplay video file (MP4, MKV, MOV — max 500 MB)",
        youtube_url="Optional YouTube gameplay URL to extract clips from",
        nb_clips="Number of clips to generate (1 to 5, default: 3)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def render_clip(
        self,
        interaction: discord.Interaction,
        video: discord.Attachment | None = None,
        youtube_url: str | None = None,
        nb_clips: int = 3,
    ) -> None:
        # Immediate defer to avoid Discord 3s timeout
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        if not video and not youtube_url:
            await interaction.edit_original_response(
                embed=embed_render_error("Please provide either a video file attachment OR a YouTube URL.")
            )
            return

        nb_clips = max(1, min(5, nb_clips))
        source_name = video.filename if video else (youtube_url or "YouTube Source")

        await interaction.edit_original_response(
            embed=embed_render_started("uploading…", source_name, percent=10, message="Preparing media stream for VPS Studio…")
        )

        video_bytes = None
        if video:
            if video.size > 500 * 1024 * 1024:
                await interaction.edit_original_response(
                    embed=embed_render_error("File too large — maximum 500 MB per upload.")
                )
                return

            try:
                video_bytes = await video.read()
            except Exception as exc:
                await interaction.edit_original_response(
                    embed=embed_render_error(f"Failed to read file from Discord: {exc}")
                )
                return

        try:
            await interaction.edit_original_response(
                embed=embed_render_started("initializing…", source_name, percent=20, message="Transferring video to VPS Studio engine…")
            )
            result = await _submit_render(
                video_bytes=video_bytes,
                filename=video.filename if video else None,
                yt_url=youtube_url,
                num_clips=nb_clips,
            )
        except Exception as exc:
            await interaction.edit_original_response(
                embed=embed_render_error(f"Studio API unreachable ({STUDIO_URL}): {exc}")
            )
            return

        if not result.get("success"):
            await interaction.edit_original_response(
                embed=embed_render_error(result.get("error", "Unknown error returned by Studio engine"))
            )
            return

        task_id = result["task_id"]
        task = await _poll_task_live(task_id, interaction, source_name)

        if task.get("status") == "error":
            await interaction.edit_original_response(
                embed=embed_render_error(task.get("error", "Unknown error occurred during rendering."))
            )
            return

        clips = task.get("clips", [])
        if not clips:
            await interaction.edit_original_response(
                embed=embed_render_error("No clips were generated. Check the video length or audio track.")
            )
            return

        await interaction.edit_original_response(embed=embed_render_done(clips, task_id))

        for i, clip in enumerate(clips[:5], 1):
            clip_filename = clip.get("filename")
            meta = clip.get("meta", {})
            if not clip_filename:
                continue

            clip_bytes = await _download_clip(clip_filename)
            if not clip_bytes:
                continue

            file = discord.File(io.BytesIO(clip_bytes), filename=f"core_market_short_{i}.mp4")
            try:
                await interaction.followup.send(
                    embed=embed_metadata_card(meta, i),
                    file=file,
                    ephemeral=True,
                )
            except discord.HTTPException as err:
                log.warning("Could not attach video file directly to Discord: %s", err)
                # Graceful fallback with direct download link if attachment limits are hit
                download_url = f"{STUDIO_URL}/output/{clip_filename}"
                meta_embed = embed_metadata_card(meta, i)
                meta_embed.add_field(
                    name="📥 Direct Video Download",
                    value=f"Discord upload limit reached. [**Click here to download clip #{i} (.mp4)**]({download_url})",
                    inline=False,
                )
                await interaction.followup.send(
                    embed=meta_embed,
                    ephemeral=True,
                )

    @app_commands.command(
        name="studio_status",
        description="🖥️ Check CORE STUDIO video pipeline status on VPS",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def studio_status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{STUDIO_URL}/api/status", timeout=aiohttp.ClientTimeout(total=5)) as r:
                    data = await r.json()

            nvenc = data.get("nvenc_gpu_active", False)
            gpu = data.get("gpu_name", "CPU Fallback")

            e = discord.Embed(
                title="🖥️  CORE STUDIO — Video Pipeline Health",
                description=(
                    f"> Real-time state of the video processing engine running on the VPS.\n\n"
                    f"▸ **Engine Status :** 🟢 `ONLINE`\n"
                    f"▸ **Hardware Acceleration :** `{gpu}`\n"
                    f"▸ **Service Endpoint :** `{STUDIO_URL}`\n"
                    f"▸ **Target Resolution :** `1080x1920 (9:16 Vertical)`\n\n"
                    f"──────────────────────────────────────────\n"
                    f"⚡ *Ready to process gameplay uploads via `/render_clip`.*"
                ),
                color=COLOR_SUCCESS if nvenc else COLOR_PRIMARY,
                timestamp=discord.utils.utcnow(),
            )
            e.set_footer(text="CORE STUDIO • VPS Microservice")
            await interaction.followup.send(embed=e, ephemeral=True)

        except Exception:
            e = discord.Embed(
                title="🔴  CORE STUDIO — Service Offline",
                description="> The studio microservice on the VPS is currently unreachable.",
                color=COLOR_ALERT,
            )
            await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ContentEngine(bot))
