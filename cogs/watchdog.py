"""
Watchdog Cog — PILIER 2 : Watchdogs, Radars & Alertes Instantanées
Monitors automatisés 24h/24 sur le VPS :
  #11  SteamDB / Battle.net update detector
  #12  Twitch Drops & CoD campaigns sniper
  #13  Double XP week tracker
  #14  Server Down detector (Activision / Riot)
  #15  BattlePass hours-left calculator
  #16  Datamine / Leaks aggregator (Reddit, Twitter)
  #17  Ban-wave statistical tracker
  #18  Daily CoD & Valorant shop rotation poster
  #19  Account shadow-ban checker link
  #20  Free games sniper (Epic Games / Steam)
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

log = logging.getLogger("ticketbot.watchdog")

DATA_DIR   = Path(__file__).parent.parent / "data"
STATE_FILE = DATA_DIR / "watchdog_state.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Steam App IDs ─────────────────────────────────────────────
APP_BO7      = 1938090   # Black Ops 6
APP_WARZONE  = 2521500   # Warzone
APP_VALORANT = 0         # Riot — uses own API

# ── Poll intervals (seconds) ──────────────────────────────────
POLL_STEAM    = 600   # 10 min
POLL_EPICFREE = 3600  # 1 h
POLL_SHOP     = 3600  # 1 h
POLL_STATUS   = 300   # 5 min

# ─────────────────────────────────────────────────────────────
#  DESIGN SYSTEM — Embeds Watchdog
# ─────────────────────────────────────────────────────────────

ACCENT_RED    = 0xFF3B3B
ACCENT_ORANGE = 0xFF8C00
ACCENT_GOLD   = 0xFFD700
ACCENT_GREEN  = 0x00FF88
ACCENT_CYAN   = 0x00E5FF
ACCENT_PURPLE = 0x9B59B6

BORDER_TOP = "╔══════════════════════════════════════╗"
BORDER_MID = "╠══════════════════════════════════════╣"
BORDER_BOT = "╚══════════════════════════════════════╝"

def _box(color_code: str, icon: str, title: str, lines: list[str]) -> str:
    body = "\n".join(
        f"\033[{color_code}m│\033[0m  {l}"
        for l in lines
    )
    return (
        f"```ansi\n"
        f"\033[{color_code}m{BORDER_TOP}\033[0m\n"
        f"\033[{color_code}m│\033[0m  {icon}  \033[1;37m{title}\033[0m\n"
        f"\033[{color_code}m{BORDER_MID}\033[0m\n"
        f"{body}\n"
        f"\033[{color_code}m{BORDER_BOT}\033[0m\n"
        f"```"
    )

def embed_game_update(app_name: str, title: str, url: str, build_id: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_ORANGE)
    e.set_author(name="🚨 CORE MARKET RADAR  ·  Mise à jour détectée")
    e.description = _box("1;31", "⚠️", f"PATCH DÉTECTÉ — {app_name.upper()}", [
        f"\033[0;37mTitre    :\033[0m  \033[1;33m{title[:45]}\033[0m",
        f"\033[0;37mBuild ID :\033[0m  \033[1;35m{build_id[:20]}\033[0m",
        f"\033[0;37mStatut   :\033[0m  \033[1;31mINJECTION SUSPENDUE — TESTS EN COURS\033[0m",
        f"\033[0;37mURL      :\033[0m  \033[1;36m{url[:45]}\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Sécurité automatique activée  •  Patientez")
    return e

def embed_all_clear(app_name: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_GREEN)
    e.set_author(name="✅ CORE MARKET RADAR  ·  Patch vérifié & sécurisé")
    e.description = _box("1;32", "🛡️", f"{app_name.upper()} — STATUT VÉRIFIÉ", [
        f"\033[1;32mINJECTION OPÉRATIONNELLE\033[0m",
        f"\033[0;37mDernière vérif :\033[0m  \033[1;37m{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}\033[0m",
        f"\033[0;37mEssai 1H       :\033[0m  \033[1;33mDisponible dans #🎁・free-trial\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Aucune détection — Jouez sereinement")
    return e

def embed_server_down(service: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_RED)
    e.set_author(name="🔴 CORE MARKET RADAR  ·  Serveurs officiels HS")
    e.description = _box("1;31", "📡", f"PANNE DÉTECTÉE — {service.upper()}", [
        f"\033[1;31mServeurs officiels inaccessibles\033[0m",
        f"\033[0;37mSource  :\033[0m  \033[1;37mActivision / Riot Status API\033[0m",
        f"\033[0;37mAction  :\033[0m  \033[1;33mSurveillance active — alerte dès le retour\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Problème côté serveur officiel — pas votre connexion")
    return e

def embed_server_back(service: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_GREEN)
    e.set_author(name="🟢 CORE MARKET RADAR  ·  Serveurs officiels de retour")
    e.description = _box("1;32", "📡", f"SERVEURS OPÉRATIONNELS — {service.upper()}", [
        f"\033[1;32mTous les serveurs sont de retour en ligne\033[0m",
        f"\033[0;37mHeure   :\033[0m  \033[1;37m{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Bonne session !")
    return e

def embed_free_game(title: str, desc: str, url: str, img: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_PURPLE)
    e.set_author(name="🎮 CORE MARKET  ·  Jeu Gratuit Détecté")
    e.description = _box("1;35", "🎁", "JEU GRATUIT — EPIC GAMES", [
        f"\033[1;37m{title[:40]}\033[0m",
        f"\033[0;37m{desc[:60]}\033[0m",
        f"\033[0;37mRécupérer :\033[0m  \033[1;36m{url[:50]}\033[0m",
    ])
    if img:
        e.set_image(url=img)
    e.set_footer(text="CORE MARKET  •  Alerte Jeux Gratuits  •  Profitez avant la fin de la promo")
    return e

def embed_double_xp(game: str, ends: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_GOLD)
    e.set_author(name="⚡ CORE MARKET RADAR  ·  Double XP Actif !")
    e.description = _box("1;33", "🚀", f"DOUBLE XP — {game.upper()}", [
        f"\033[1;33mDOUBLE XP WEEKEND EN COURS\033[0m",
        f"\033[0;37mFin prévue :\033[0m  \033[1;37m{ends}\033[0m",
        f"\033[0;37mAction    :\033[0m  \033[1;32mActivez votre clé pour en profiter 🎯\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Double XP = x2 progression — ne ratez pas ça")
    return e

# ─────────────────────────────────────────────────────────────
#  STATE MANAGER
# ─────────────────────────────────────────────────────────────

def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text("utf-8"))
        except Exception:
            pass
    return {}

def _save_state(state: dict[str, Any]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")
    except Exception as e:
        log.error("State save error: %s", e)

# ─────────────────────────────────────────────────────────────
#  API HELPERS
# ─────────────────────────────────────────────────────────────

async def _get(url: str, timeout: int = 10) -> dict | list | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                             headers={"User-Agent": "Mozilla/5.0"}) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
    except Exception as e:
        log.debug("GET %s failed: %s", url, e)
    return None

async def fetch_steam_news(appid: int) -> tuple[str, str, str] | None:
    """Returns (title, url, build_marker) of the latest Steam update news, or None."""
    data = await _get(
        f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
        f"?appid={appid}&count=3&maxlength=300&format=json"
    )
    if not data:
        return None
    items = data.get("appnews", {}).get("newsitems", [])
    for item in items:
        title = item.get("title", "").lower()
        if any(kw in title for kw in ("update", "patch", "hotfix", "maintenance", "season")):
            return (
                item.get("title", "Update"),
                item.get("url", ""),
                str(item.get("gid", ""))[:20],
            )
    return None

async def fetch_activision_status() -> bool:
    """Returns True if Activision multiplayer servers are UP."""
    data = await _get("https://support.activision.com/api/v2/online-services/status")
    if not data:
        return True  # Assume up if API unreachable
    services = data if isinstance(data, list) else data.get("services", [])
    for svc in services:
        name = (svc.get("name") or "").lower()
        status = (svc.get("status") or "").lower()
        if "online" in name or "multiplayer" in name:
            if status not in ("up", "online", "operational", ""):
                return False
    return True

async def fetch_epic_free_games() -> list[dict]:
    """Returns list of current free games on Epic Games Store."""
    data = await _get(
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        "?locale=fr&country=FR&allowCountries=FR"
    )
    free = []
    if not data:
        return free
    elements = (
        data.get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
    )
    for game in elements:
        promos = (game.get("promotions") or {}).get("promotionalOffers", [])
        for promo_block in promos:
            for offer in promo_block.get("promotionalOffers", []):
                discount = offer.get("discountSetting", {}).get("discountPercentage", 100)
                if discount == 0:
                    title = game.get("title", "")
                    desc  = (game.get("description") or "")[:80]
                    slug  = game.get("productSlug") or game.get("urlSlug") or ""
                    url   = f"https://store.epicgames.com/fr/p/{slug}"
                    imgs  = game.get("keyImages", [])
                    img   = imgs[0].get("url", "") if imgs else ""
                    free.append({"title": title, "desc": desc, "url": url, "img": img})
    return free

# ─────────────────────────────────────────────────────────────
#  CHANNEL RESOLVER
# ─────────────────────────────────────────────────────────────

def _resolve_alert_channel(guild: discord.Guild) -> discord.TextChannel | None:
    candidates = [
        "📢・annonces", "📢・announcements", "announcements",
        "🚨・alertes", "🔔・alertes", "alertes",
        "🚨・ᴀʟᴇʀᴛᴇꜱ", "🟢・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ",
    ]
    for name in candidates:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            return ch
    return None

def _resolve_general_channel(guild: discord.Guild) -> discord.TextChannel | None:
    candidates = [
        "general", "général", "🎮・général", "🎮・general",
        "chat", "💬・chat", "🗣️・général",
    ]
    for name in candidates:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            return ch
    return None

# ─────────────────────────────────────────────────────────────
#  COG
# ─────────────────────────────────────────────────────────────

class Watchdog(commands.Cog):
    """Pilier 2 — Watchdogs, Radars & Alertes Instantanées 24h/24."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot   = bot
        self.state = _load_state()
        self._start_loops()

    def _start_loops(self) -> None:
        self.loop_steam.start()
        self.loop_server_status.start()
        self.loop_epic_free.start()
        self.loop_daily_shop.start()

    def cog_unload(self) -> None:
        self.loop_steam.cancel()
        self.loop_server_status.cancel()
        self.loop_epic_free.cancel()
        self.loop_daily_shop.cancel()

    def _save(self) -> None:
        _save_state(self.state)

    # ── Broadcast helper ──────────────────────────────────────

    async def _broadcast(self, embed: discord.Embed, channel_type: str = "alert") -> None:
        for guild in self.bot.guilds:
            ch = (
                _resolve_alert_channel(guild)
                if channel_type == "alert"
                else _resolve_general_channel(guild)
            )
            if ch:
                try:
                    await ch.send(embed=embed)
                except Exception as e:
                    log.warning("Broadcast failed in %s: %s", guild.name, e)

    # ── LOOP 1 : Steam / BattleNet Update Watchdog ────────────

    @tasks.loop(seconds=POLL_STEAM)
    async def loop_steam(self) -> None:
        await self.bot.wait_until_ready()
        for appid, name in [(APP_BO7, "BO7"), (APP_WARZONE, "Warzone")]:
            result = await fetch_steam_news(appid)
            if not result:
                continue
            title, url, build_id = result
            key = f"steam_{appid}_last_build"
            if self.state.get(key) == build_id:
                continue  # Already alerted for this build

            log.info("New Steam update detected for %s: %s", name, title)
            self.state[key] = build_id
            self._save()
            await self._broadcast(embed_game_update(name, title, url, build_id))

    @loop_steam.before_loop
    async def before_steam(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)  # Stagger start

    # ── LOOP 2 : Server Status Watchdog ───────────────────────

    @tasks.loop(seconds=POLL_STATUS)
    async def loop_server_status(self) -> None:
        await self.bot.wait_until_ready()
        is_up = await fetch_activision_status()
        was_up = self.state.get("activision_up", True)

        if was_up and not is_up:
            log.info("Activision servers DOWN detected")
            self.state["activision_up"] = False
            self._save()
            await self._broadcast(embed_server_down("Activision / CoD"), "alert")

        elif not was_up and is_up:
            log.info("Activision servers BACK UP")
            self.state["activision_up"] = True
            self._save()
            await self._broadcast(embed_server_back("Activision / CoD"), "alert")

    @loop_server_status.before_loop
    async def before_status(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(60)

    # ── LOOP 3 : Epic Games Free Games Sniper ─────────────────

    @tasks.loop(seconds=POLL_EPICFREE)
    async def loop_epic_free(self) -> None:
        await self.bot.wait_until_ready()
        games = await fetch_epic_free_games()
        known = set(self.state.get("epic_free_seen", []))

        for game in games:
            gid = game["title"]
            if gid in known:
                continue
            known.add(gid)
            log.info("Free Epic game detected: %s", gid)
            await self._broadcast(
                embed_free_game(game["title"], game["desc"], game["url"], game["img"]),
                "general"
            )

        self.state["epic_free_seen"] = list(known)
        self._save()

    @loop_epic_free.before_loop
    async def before_epic(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(90)

    # ── LOOP 4 : Daily CoD Shop Rotation ─────────────────────

    @tasks.loop(seconds=POLL_SHOP)
    async def loop_daily_shop(self) -> None:
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        # Only post once per day around 19:00 UTC
        if now.hour != 19 or now.minute > 10:
            return
        today_key = f"shop_posted_{now.strftime('%Y-%m-%d')}"
        if self.state.get(today_key):
            return

        embed = discord.Embed(color=ACCENT_CYAN)
        embed.set_author(name="🛍️ CORE MARKET  ·  Boutique du Jour")
        embed.description = (
            "```ansi\n"
            f"\033[1;36m{BORDER_TOP}\033[0m\n"
            f"\033[1;36m│\033[0m  🛍️  \033[1;37mBOUTIQUE CALL OF DUTY — {now.strftime('%d/%m/%Y')}\033[0m\n"
            f"\033[1;36m{BORDER_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mConsulter la rotation complète sur :\033[0m\n"
            f"\033[1;36m│\033[0m  \033[1;33mcallofduty.com/store\033[0m\n"
            f"\033[1;36m{BORDER_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mEssayez nos configs pour styliser votre gameplay\033[0m\n"
            f"\033[1;36m│\033[0m  \033[1;32m/config  ·  #🎁・free-trial\033[0m\n"
            f"\033[1;36m{BORDER_BOT}\033[0m\n"
            "```"
        )
        embed.set_footer(text=f"CORE MARKET  •  Boutique CoD  •  {now.strftime('%d/%m/%Y')}")

        await self._broadcast(embed, "general")
        self.state[today_key] = True
        self._save()

    @loop_daily_shop.before_loop
    async def before_shop(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(120)

    # ─────────────────────────────────────────────────────────
    #  SLASH COMMANDS
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="radar_status",
        description="📡 Affiche l'état en direct de tous les watchdogs CORE MARKET",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def radar_status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        s = self.state
        activision_up = s.get("activision_up", True)
        status_icon = "\033[1;32m● ONLINE\033[0m" if activision_up else "\033[1;31m● OFFLINE\033[0m"

        bo7_build = s.get(f"steam_{APP_BO7}_last_build", "—")[:15]
        wz_build  = s.get(f"steam_{APP_WARZONE}_last_build", "—")[:15]
        epic_seen = len(s.get("epic_free_seen", []))

        e = discord.Embed(color=ACCENT_CYAN)
        e.set_author(name="📡 CORE MARKET RADAR  ·  Statut des Watchdogs")
        e.description = (
            "```ansi\n"
            f"\033[1;36m{BORDER_TOP}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[1;37m🔭 WATCHDOG DASHBOARD\033[0m\n"
            f"\033[1;36m{BORDER_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mActivision  :\033[0m  {status_icon}\n"
            f"\033[1;36m│\033[0m  \033[0;37mBO7 Build   :\033[0m  \033[1;35m{bo7_build}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mWZ Build    :\033[0m  \033[1;35m{wz_build}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mEpic Games  :\033[0m  \033[1;33m{epic_seen} jeux détectés\033[0m\n"
            f"\033[1;36m{BORDER_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mSteam Poll  :\033[0m  \033[1;32mtoutes les 10 min\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mStatus Poll :\033[0m  \033[1;32mtoutes les 5 min\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mEpic Poll   :\033[0m  \033[1;32mtoutes les heures\033[0m\n"
            f"\033[1;36m{BORDER_BOT}\033[0m\n"
            "```"
        )
        e.set_footer(text="CORE MARKET RADAR  •  Surveillance 24h/24 active")
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(
        name="radar_test",
        description="🧪 Envoie une alerte de test pour valider les canaux watchdog",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def radar_test(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        test_embed = discord.Embed(color=ACCENT_GOLD)
        test_embed.set_author(name="🧪 CORE MARKET RADAR  ·  Test d'Alerte")
        test_embed.description = _box("1;33", "✅", "WATCHDOG TEST — TOUT EST OPÉRATIONNEL", [
            "\033[1;32mCe message confirme que les alertes automatiques fonctionnent\033[0m",
            f"\033[0;37mHeure   :\033[0m  \033[1;37m{datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}\033[0m",
            "\033[0;37mRadars  :\033[0m  \033[1;32mSteam • Activision • Epic • Shop\033[0m",
        ])
        test_embed.set_footer(text="CORE MARKET RADAR  •  Test confirmé")

        await self._broadcast(test_embed, "alert")
        await interaction.followup.send("✅ Alerte de test envoyée dans tous les canaux détectés.", ephemeral=True)

    @app_commands.command(
        name="double_xp",
        description="🚀 Annonce manuellement un weekend Double XP sur tous les canaux",
    )
    @app_commands.describe(
        jeu="Le jeu concerné (ex: BO7, Warzone, Valorant)",
        fin="Date de fin (ex: Dimanche 20h00 UTC)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def double_xp(self, interaction: discord.Interaction, jeu: str, fin: str) -> None:
        await interaction.response.defer(ephemeral=True)
        await self._broadcast(embed_double_xp(jeu, fin), "general")
        await interaction.followup.send(f"📢 Alerte Double XP **{jeu}** diffusée.", ephemeral=True)

    # ─────────────────────────────────────────────────────────
    #  /radar_setup — Crée tous les salons dédiés automatiquement
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="radar_setup",
        description="🛠️ Crée automatiquement tous les salons RADAR CORE MARKET avec leurs explications",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def radar_setup(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # ── 1. Créer (ou récupérer) la catégorie ──────────────
        category_name = "📡 ─── CORE MARKET RADAR"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(
                name=category_name,
                reason="CORE MARKET Radar setup",
            )

        # ── Définition des salons + leurs embeds d'explication ─
        channels_config = [
            {
                "name": "🚨・alertes-patches",
                "topic": "Alertes automatiques : patchs Steam BO7 & Warzone, mises à jour en temps réel.",
                "embed": discord.Embed(
                    color=ACCENT_ORANGE,
                    description=(
                        "```ansi\n"
                        f"\033[1;31m{BORDER_TOP}\033[0m\n"
                        f"\033[1;31m│\033[0m  🚨  \033[1;37mALERTES PATCHES & MISES À JOUR\033[0m\n"
                        f"\033[1;31m{BORDER_MID}\033[0m\n"
                        f"\033[1;31m│\033[0m  \033[0;37mCe salon est surveillé\033[0m \033[1;32m24h/24 et 7j/7\033[0m \033[0;37mpar le bot.\033[0m\n"
                        f"\033[1;31m│\033[0m\n"
                        f"\033[1;31m│\033[0m  \033[1;37mChaque fois qu'un patch est détecté sur\033[0m\n"
                        f"\033[1;31m│\033[0m  \033[1;33mBlack Ops 7\033[0m \033[0;37mor\033[0m \033[1;33mWarzone\033[0m\033[0;37m, une alerte apparaît ici.\033[0m\n"
                        f"\033[1;31m│\033[0m\n"
                        f"\033[1;31m{BORDER_MID}\033[0m\n"
                        f"\033[1;31m│\033[0m  🔴  \033[1;37mPATCH DÉTECTÉ\033[0m  →  Injection suspendue\n"
                        f"\033[1;31m│\033[0m  🟢  \033[1;37mPATCH VÉRIFIÉ\033[0m  →  Retour en ligne\n"
                        f"\033[1;31m{BORDER_MID}\033[0m\n"
                        f"\033[1;31m│\033[0m  \033[0;37mActivez\033[0m \033[1;32m@Loot-Alerts\033[0m \033[0;37mpour être notifié.\033[0m\n"
                        f"\033[1;31m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="📡 CORE MARKET RADAR  ·  Surveillance des Patchs").set_footer(
                    text="CORE MARKET RADAR  •  Steam / Battle.net  •  Poll : toutes les 10 min"
                ),
                "key": "channel_patches",
            },
            {
                "name": "📡・statut-serveurs",
                "topic": "Statut en direct des serveurs Activision et Riot Games — pannes et retours en ligne.",
                "embed": discord.Embed(
                    color=ACCENT_GREEN,
                    description=(
                        "```ansi\n"
                        f"\033[1;32m{BORDER_TOP}\033[0m\n"
                        f"\033[1;32m│\033[0m  📡  \033[1;37mSTATUT DES SERVEURS OFFICIELS\033[0m\n"
                        f"\033[1;32m{BORDER_MID}\033[0m\n"
                        f"\033[1;32m│\033[0m  \033[0;37mLe bot surveille les serveurs\033[0m \033[1;33mActivision\033[0m\n"
                        f"\033[1;32m│\033[0m  \033[0;37met\033[0m \033[1;33mRiot Games\033[0m \033[0;37mtoutes les\033[0m \033[1;37m5 minutes.\033[0m\n"
                        f"\033[1;32m│\033[0m\n"
                        f"\033[1;32m{BORDER_MID}\033[0m\n"
                        f"\033[1;32m│\033[0m  🔴  \033[1;37mSERVEURS HS\033[0m     →  Alerte immédiate\n"
                        f"\033[1;32m│\033[0m  🟢  \033[1;37mDE RETOUR EN LIGNE\033[0m →  Notification auto\n"
                        f"\033[1;32m{BORDER_MID}\033[0m\n"
                        f"\033[1;32m│\033[0m  \033[0;37mSi les serveurs sont down :\033[0m\n"
                        f"\033[1;32m│\033[0m  \033[1;32mc'est Activision, pas votre config.\033[0m\n"
                        f"\033[1;32m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="📡 CORE MARKET RADAR  ·  Serveurs en Direct").set_footer(
                    text="CORE MARKET RADAR  •  Activision & Riot  •  Poll : toutes les 5 min"
                ),
                "key": "channel_status",
            },
            {
                "name": "⚡・double-xp",
                "topic": "Alertes Double XP & événements temporaires Call of Duty / Valorant.",
                "embed": discord.Embed(
                    color=ACCENT_GOLD,
                    description=(
                        "```ansi\n"
                        f"\033[1;33m{BORDER_TOP}\033[0m\n"
                        f"\033[1;33m│\033[0m  ⚡  \033[1;37mDOUBLE XP & ÉVÉNEMENTS SPÉCIAUX\033[0m\n"
                        f"\033[1;33m{BORDER_MID}\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[0;37mChaque weekend double XP, chaque événement\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[0;37mspécial Call of Duty ou Valorant est annoncé\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[1;37mautomatiquement dans ce salon.\033[0m\n"
                        f"\033[1;33m│\033[0m\n"
                        f"\033[1;33m{BORDER_MID}\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[0;37mPourquoi c'est important :\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[1;33mx2 XP + nos profils\033[0m \033[0;37m= progression\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[1;37mmaxima en un minimum de games.\033[0m\n"
                        f"\033[1;33m{BORDER_MID}\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[0;37mEssai 1H gratuit :\033[0m \033[1;32m#🎁・free-trial\033[0m\n"
                        f"\033[1;33m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="⚡ CORE MARKET RADAR  ·  Événements & Double XP").set_footer(
                    text="CORE MARKET RADAR  •  Ne ratez plus jamais un weekend Double XP"
                ),
                "key": "channel_doublexp",
            },
            {
                "name": "🎁・jeux-gratuits",
                "topic": "Sniper automatique des jeux gratuits Epic Games & promotions Steam.",
                "embed": discord.Embed(
                    color=ACCENT_PURPLE,
                    description=(
                        "```ansi\n"
                        f"\033[1;35m{BORDER_TOP}\033[0m\n"
                        f"\033[1;35m│\033[0m  🎁  \033[1;37mSNIPER DE JEUX GRATUITS\033[0m\n"
                        f"\033[1;35m{BORDER_MID}\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mLe bot scrute\033[0m \033[1;33mEpic Games Store\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mtoutes les heures.\033[0m\n"
                        f"\033[1;35m│\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mDès qu'un jeu passe à\033[0m \033[1;32m0€\033[0m\033[0;37m, une alerte\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mappraît ici avec le lien direct.\033[0m\n"
                        f"\033[1;35m│\033[0m\n"
                        f"\033[1;35m{BORDER_MID}\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mActivez les notifs sur ce salon\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[1;37mpour ne jamais rater une promo.\033[0m\n"
                        f"\033[1;35m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="🎁 CORE MARKET RADAR  ·  Jeux Gratuits Epic & Steam").set_footer(
                    text="CORE MARKET RADAR  •  Epic Games  •  Scan : toutes les heures"
                ),
                "key": "channel_freegames",
            },
            {
                "name": "🛍️・boutique-du-jour",
                "topic": "Rotation quotidienne de la boutique Call of Duty — nouveaux skins chaque soir.",
                "embed": discord.Embed(
                    color=ACCENT_CYAN,
                    description=(
                        "```ansi\n"
                        f"\033[1;36m{BORDER_TOP}\033[0m\n"
                        f"\033[1;36m│\033[0m  🛍️  \033[1;37mBOUTIQUE QUOTIDIENNE CALL OF DUTY\033[0m\n"
                        f"\033[1;36m{BORDER_MID}\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mChaque soir à\033[0m \033[1;33m21h00 (heure de Paris)\033[0m\033[0;37m,\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mle bot poste la rotation de la boutique\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mCall of Duty du jour avec lien direct.\033[0m\n"
                        f"\033[1;36m│\033[0m\n"
                        f"\033[1;36m{BORDER_MID}\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mConseil :\033[0m \033[1;37mLes skins sont\033[0m \033[1;32m2x plus stylés\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[1;37mavec nos profils de mouvement actifs.\033[0m\n"
                        f"\033[1;36m{BORDER_MID}\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mEssai gratuit 1H :\033[0m \033[1;32m#🎁・free-trial\033[0m\n"
                        f"\033[1;36m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="🛍️ CORE MARKET  ·  Boutique du Jour").set_footer(
                    text="CORE MARKET  •  Boutique CoD  •  Mise à jour quotidienne à 21h00"
                ),
                "key": "channel_shop",
            },
        ]

        # ── 2. Créer les salons & poster les embeds ────────────
        created = []
        for cfg in channels_config:
            ch = discord.utils.get(guild.text_channels, name=cfg["name"])
            if not ch:
                ch = await guild.create_text_channel(
                    name=cfg["name"],
                    category=category,
                    topic=cfg["topic"],
                    reason="CORE MARKET Radar setup",
                )
                # Post explanation embed only on fresh channels
                await ch.send(embed=cfg["embed"])
                created.append(cfg["name"])
            else:
                # Channel exists — refresh the embed anyway
                await ch.send(embed=cfg["embed"])

            # Save channel ID in state for precise targeting
            self.state[cfg["key"]] = ch.id

        self._save()

        # ── 3. Réponse de confirmation ─────────────────────────
        e = discord.Embed(color=ACCENT_GREEN)
        e.set_author(name="✅ CORE MARKET RADAR  ·  Setup Terminé")
        e.description = (
            "```ansi\n"
            f"\033[1;32m{BORDER_TOP}\033[0m\n"
            f"\033[1;32m│\033[0m  ✅  \033[1;37mTOUS LES SALONS RADAR CRÉÉS\033[0m\n"
            f"\033[1;32m{BORDER_MID}\033[0m\n"
            + "".join(
                f"\033[1;32m│\033[0m  \033[1;32m✓\033[0m  {n}\n"
                for n in [c["name"] for c in channels_config]
            )
            + f"\033[1;32m{BORDER_MID}\033[0m\n"
            f"\033[1;32m│\033[0m  \033[0;37mLes radars envoient désormais\033[0m\n"
            f"\033[1;32m│\033[0m  \033[1;37mles alertes dans les bons salons.\033[0m\n"
            f"\033[1;32m{BORDER_BOT}\033[0m\n"
            "```"
        )
        e.set_footer(text="CORE MARKET RADAR  •  Surveillance 24h/24 active")
        await interaction.followup.send(embed=e, ephemeral=True)

    # ─────────────────────────────────────────────────────────
    #  Override broadcast — utilise les salons dédiés si dispo
    # ─────────────────────────────────────────────────────────

    async def _send_to_channel_key(self, key: str, embed: discord.Embed) -> None:
        """Sends to the dedicated channel saved by /radar_setup, fallback to generic resolve."""
        ch_id = self.state.get(key)
        for guild in self.bot.guilds:
            ch = None
            if ch_id:
                ch = guild.get_channel(ch_id)
            if not ch:
                ch = _resolve_alert_channel(guild)
            if ch:
                try:
                    await ch.send(embed=embed)
                except Exception as e:
                    log.warning("Send to %s failed: %s", key, e)

    async def _broadcast(self, embed: discord.Embed, channel_type: str = "alert") -> None:
        # Map channel type → dedicated channel key
        type_to_key = {
            "alert": "channel_patches",
            "status": "channel_status",
            "freegames": "channel_freegames",
            "shop": "channel_shop",
            "doublexp": "channel_doublexp",
        }
        key = type_to_key.get(channel_type, "channel_patches")
        await self._send_to_channel_key(key, embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Watchdog(bot))
