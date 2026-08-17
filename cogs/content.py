"""
Content Engine Cog — /render_clip Discord command.
Sends a gameplay video to the VPS FFmpeg pipeline and returns
ready-to-post TikTok/Shorts clips directly in Discord.
"""

import asyncio
import io
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("ticketbot.content")

STUDIO_URL = os.getenv("STUDIO_URL", "http://127.0.0.1:5050")

# ─────────────────────────────────────────────────────────────
#  EMBED DESIGN SYSTEM  —  Style unique, jamais vu sur Discord
# ─────────────────────────────────────────────────────────────

BRAND = "\033[1;36m◈ CORE MARKET\033[0m"

BLOCK_TOP    = "╔══════════════════════════════════════╗"
BLOCK_MID    = "╠══════════════════════════════════════╣"
BLOCK_BOT    = "╚══════════════════════════════════════╝"
LINE         = "│  {:<38}│"
EMPTY        = "│{:^40}│"

ACCENT_GOLD  = 0xFFD700
ACCENT_CYAN  = 0x00E5FF
ACCENT_GREEN = 0x00FF88
ACCENT_RED   = 0xFF3B3B


def _ansi(text: str) -> str:
    return f"```ansi\n{text}\n```"


def render_progress_bar(percent: int, width: int = 20) -> str:
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {percent}%"


def embed_render_started(task_id: str, filename: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_CYAN)
    e.set_author(name="⚡ CORE STUDIO  ·  Content Engine", icon_url=None)
    e.description = (
        _ansi(
            f"\033[1;36m{BLOCK_TOP}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[1;37m🎬  RENDERING PIPELINE STARTED\033[0m           \033[1;36m│\033[0m\n"
            f"\033[1;36m{BLOCK_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mFile :\033[0m  \033[1;33m{filename[:32]}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mTask :\033[0m  \033[1;35m{task_id}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mMode :\033[0m  \033[1;32mAuto-Clip 9:16 Vertical\033[0m\n"
            f"\033[1;36m{BLOCK_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  {render_progress_bar(10)}\033[0m\n"
            f"\033[1;36m{BLOCK_BOT}\033[0m"
        )
    )
    e.set_footer(text="CORE STUDIO  •  FFmpeg NVENC Pipeline  •  En cours…")
    return e


def embed_render_done(clips: list[dict], task_id: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_GREEN)
    e.set_author(name="✅ CORE STUDIO  ·  Clips Prêts à Poster")

    clips_block = ""
    for i, c in enumerate(clips[:5], 1):
        title = c.get("title", f"Clip #{i}")[:30]
        meta = c.get("meta", {})
        hook = meta.get("title", "—")[:32]
        time_slot = meta.get("optimal_time", "—")[:28]
        clips_block += (
            f"\033[1;33m  ◈ Clip #{i}\033[0m  \033[0;37m{title}\033[0m\n"
            f"\033[0;37m    Hook   :\033[0m  \033[1;37m{hook}\033[0m\n"
            f"\033[0;37m    Poster :\033[0m  \033[1;32m{time_slot}\033[0m\n"
        )

    e.description = (
        _ansi(
            f"\033[1;32m{BLOCK_TOP}\033[0m\n"
            f"\033[1;32m│\033[0m  \033[1;37m🎯  {len(clips)} CLIP(S) GÉNÉRÉS AVEC SUCCÈS\033[0m\n"
            f"\033[1;32m{BLOCK_MID}\033[0m\n"
            f"{clips_block}"
            f"\033[1;32m{BLOCK_MID}\033[0m\n"
            f"\033[1;32m│\033[0m  \033[0;37mTask ID :\033[0m  \033[1;35m{task_id}\033[0m\n"
            f"\033[1;32m│\033[0m  {render_progress_bar(100)}\033[0m\n"
            f"\033[1;32m{BLOCK_BOT}\033[0m"
        )
    )
    e.set_footer(text="CORE STUDIO  •  Clips téléchargeables ci-dessous  •  Postez entre 18h30 et 21h30")
    return e


def embed_render_error(error: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_RED)
    e.set_author(name="✗ CORE STUDIO  ·  Erreur de Rendu")
    e.description = (
        _ansi(
            f"\033[1;31m{BLOCK_TOP}\033[0m\n"
            f"\033[1;31m│\033[0m  \033[1;37m⛔  PIPELINE ERROR\033[0m\n"
            f"\033[1;31m{BLOCK_MID}\033[0m\n"
            f"\033[1;31m│\033[0m  \033[0;37m{error[:60]}\033[0m\n"
            f"\033[1;31m{BLOCK_BOT}\033[0m"
        )
    )
    e.set_footer(text="CORE STUDIO  •  Vérifiez le format du fichier (MP4, MKV, MOV)")
    return e


def embed_metadata_card(meta: dict, clip_num: int) -> discord.Embed:
    e = discord.Embed(color=ACCENT_GOLD)
    e.title = f"📋  Metadata Clip #{clip_num}"
    e.description = (
        _ansi(
            f"\033[1;33m  Title  :\033[0m  {meta.get('title','—')[:50]}\n"
            f"\033[1;33m  Tags   :\033[0m  {meta.get('hashtags_string','')[:60]}\n"
            f"\033[1;33m  Pinned :\033[0m  {meta.get('pinned_comment','')[:60]}\n"
            f"\033[1;33m  Poster :\033[0m  \033[1;32m{meta.get('optimal_time','—')}\033[0m"
        )
    )
    return e


# ─────────────────────────────────────────────────────────────
#  STUDIO API HELPERS
# ─────────────────────────────────────────────────────────────

async def _submit_render(video_bytes: bytes, filename: str, num_clips: int = 5) -> dict[str, Any]:
    form = aiohttp.FormData()
    form.add_field("file", video_bytes, filename=filename, content_type="video/mp4")
    form.add_field("mode", "multi_shorts")
    form.add_field("num_clips", str(num_clips))
    form.add_field("clip_len", "30")
    form.add_field("top_banner", "⚡ CORE MARKET • 1H FREE TRIAL")
    form.add_field("bottom_cta", "👉 LINK IN BIO • DISCORD.GG/NPXP9UK9JG")

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{STUDIO_URL}/api/generate", data=form) as r:
            return await r.json()


async def _poll_task(task_id: str, timeout: int = 300) -> dict[str, Any]:
    deadline = asyncio.get_event_loop().time() + timeout
    async with aiohttp.ClientSession() as session:
        while asyncio.get_event_loop().time() < deadline:
            async with session.get(f"{STUDIO_URL}/api/task_status/{task_id}") as r:
                data = await r.json()
                if data.get("status") in ("done", "error"):
                    return data
            await asyncio.sleep(4)
    return {"status": "error", "error": "Timeout — le rendu a pris trop de temps."}


async def _download_clip(filename: str) -> bytes | None:
    url = f"{STUDIO_URL}/output/{filename}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                return await r.read()
    return None


# ─────────────────────────────────────────────────────────────
#  COG
# ─────────────────────────────────────────────────────────────

class ContentEngine(commands.Cog):
    """Pilier 3 — Content Engine & Automatisation Vidéo TikTok/Shorts."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="render_clip",
        description="🎬 Upload un gameplay brut → le VPS génère des Shorts 9:16 prêts à poster sur TikTok/YT",
    )
    @app_commands.describe(
        video="Fichier vidéo gameplay brut (MP4, MKV, MOV — max 500 Mo)",
        nb_clips="Nombre de clips à générer (1 à 10, défaut : 5)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def render_clip(
        self,
        interaction: discord.Interaction,
        video: discord.Attachment,
        nb_clips: int = 5,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        nb_clips = max(1, min(10, nb_clips))
        filename = video.filename

        # Guard: file size (500 MB max)
        if video.size > 500 * 1024 * 1024:
            await interaction.followup.send(
                embed=embed_render_error("Fichier trop lourd — maximum 500 Mo par upload."),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            embed=embed_render_started("pending…", filename),
            ephemeral=True,
        )

        # Download attachment from Discord CDN
        try:
            video_bytes = await video.read()
        except Exception as exc:
            await interaction.edit_original_response(embed=embed_render_error(str(exc)))
            return

        # Submit to Studio API
        try:
            result = await _submit_render(video_bytes, filename, nb_clips)
        except Exception as exc:
            await interaction.edit_original_response(embed=embed_render_error(f"Studio API unreachable: {exc}"))
            return

        if not result.get("success"):
            await interaction.edit_original_response(embed=embed_render_error(result.get("error", "Erreur inconnue")))
            return

        task_id = result["task_id"]
        await interaction.edit_original_response(embed=embed_render_started(task_id, filename))

        # Poll until done
        task = await _poll_task(task_id)

        if task.get("status") == "error":
            await interaction.edit_original_response(embed=embed_render_error(task.get("error", "Erreur inconnue")))
            return

        clips = task.get("clips", [])
        await interaction.edit_original_response(embed=embed_render_done(clips, task_id))

        # Deliver clips as Discord file attachments
        for i, clip in enumerate(clips[:5], 1):
            clip_filename = clip.get("filename")
            meta = clip.get("meta", {})
            if not clip_filename:
                continue

            clip_bytes = await _download_clip(clip_filename)
            if not clip_bytes:
                continue

            file = discord.File(io.BytesIO(clip_bytes), filename=f"core_market_short_{i}.mp4")
            await interaction.followup.send(
                embed=embed_metadata_card(meta, i),
                file=file,
                ephemeral=True,
            )

    @app_commands.command(
        name="studio_status",
        description="🖥️ Vérifie l'état du pipeline vidéo CORE STUDIO sur le VPS",
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
            gpu = data.get("gpu_name", "CPU")
            status_line = "\033[1;32mONLINE ✓\033[0m" if nvenc else "\033[1;33mCPU Mode\033[0m"

            e = discord.Embed(color=ACCENT_GREEN if nvenc else ACCENT_GOLD)
            e.set_author(name="🖥️  CORE STUDIO — Pipeline Status")
            e.description = (
                "```ansi\n"
                f"\033[1;36m╔══════════════════════════════════════╗\033[0m\n"
                f"\033[1;36m│\033[0m  \033[1;37mSTUDIO VPS PIPELINE\033[0m\n"
                f"\033[1;36m╠══════════════════════════════════════╣\033[0m\n"
                f"\033[1;36m│\033[0m  Status  :  {status_line}\n"
                f"\033[1;36m│\033[0m  Encoder :  \033[1;33m{gpu}\033[0m\n"
                f"\033[1;36m│\033[0m  URL     :  \033[1;35m{STUDIO_URL}\033[0m\n"
                f"\033[1;36m╚══════════════════════════════════════╝\033[0m\n"
                "```"
            )
            await interaction.followup.send(embed=e, ephemeral=True)

        except Exception:
            e = discord.Embed(color=ACCENT_RED)
            e.description = "```ansi\n\033[1;31m✗ CORE STUDIO OFFLINE — VPS unreachable\033[0m\n```"
            await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ContentEngine(bot))
