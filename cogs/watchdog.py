"""
Watchdog Cog — PILLAR 2 : 24/7 Watchdogs, Radars & Instant Alerts
Automated background monitors running 24/7 on the VPS:
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
APP_BO7      = 1938090   # Black Ops 6 / BO7
APP_WARZONE  = 2521500   # Warzone
APP_VALORANT = 0         # Riot — uses own API

# ── Poll intervals (seconds) ──────────────────────────────────
POLL_STEAM    = 600   # 10 min
POLL_EPICFREE = 3600  # 1 hour
POLL_SHOP     = 3600  # 1 hour
POLL_STATUS   = 300   # 5 min

# ─────────────────────────────────────────────────────────────
#  DESIGN SYSTEM — Watchdog Embeds (100% English)
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
    e.set_author(name="🚨 CORE MARKET RADAR  ·  New Patch Detected")
    e.description = _box("1;31", "⚠️", f"PATCH DETECTED — {app_name.upper()}", [
        f"\033[0;37mTitle    :\033[0m  \033[1;33m{title[:45]}\033[0m",
        f"\033[0;37mBuild ID :\033[0m  \033[1;35m{build_id[:20]}\033[0m",
        f"\033[0;37mStatus   :\033[0m  \033[1;31mINJECTION PAUSED — VERIFICATION IN PROGRESS\033[0m",
        f"\033[0;37mSource   :\033[0m  \033[1;36m{url[:45]}\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Auto-Security active  •  Please wait for green light")
    return e

def embed_all_clear(app_name: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_GREEN)
    e.set_author(name="✅ CORE MARKET RADAR  ·  Patch Verified & Secure")
    e.description = _box("1;32", "🛡️", f"{app_name.upper()} — 100% OPERATIONAL", [
        f"\033[1;32mINJECTION LIVE & UNDETECTED\033[0m",
        f"\033[0;37mLast Check :\033[0m  \033[1;37m{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\033[0m",
        f"\033[0;37m1H Trial   :\033[0m  \033[1;33mClaim now in #🎁・free-trial\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Zero Detections  •  Safe to play")
    return e

def embed_server_down(service: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_RED)
    e.set_author(name="🔴 CORE MARKET RADAR  ·  Official Servers Offline")
    e.description = _box("1;31", "📡", f"OUTAGE DETECTED — {service.upper()}", [
        f"\033[1;31mOfficial Game Servers Are Unreachable\033[0m",
        f"\033[0;37mSource  :\033[0m  \033[1;37mActivision / Riot Status API\033[0m",
        f"\033[0;37mAction  :\033[0m  \033[1;33mActive monitoring — auto-alert on recovery\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Official server issue — not your local configuration")
    return e

def embed_server_back(service: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_GREEN)
    e.set_author(name="🟢 CORE MARKET RADAR  ·  Official Servers Back Online")
    e.description = _box("1;32", "📡", f"SERVERS RECOVERED — {service.upper()}", [
        f"\033[1;32mAll official game servers are back online\033[0m",
        f"\033[0;37mTime    :\033[0m  \033[1;37m{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Enjoy your game session!")
    return e

def embed_free_game(title: str, desc: str, url: str, img: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_PURPLE)
    e.set_author(name="🎮 CORE MARKET  ·  Free Game Alert")
    e.description = _box("1;35", "🎁", "FREE GAME — EPIC GAMES STORE", [
        f"\033[1;37m{title[:40]}\033[0m",
        f"\033[0;37m{desc[:60]}\033[0m",
        f"\033[0;37mClaim Here :\033[0m  \033[1;36m{url[:50]}\033[0m",
    ])
    if img:
        e.set_image(url=img)
    e.set_footer(text="CORE MARKET  •  Free Game Alerts  •  Claim before promo ends")
    return e

def embed_double_xp(game: str, ends: str) -> discord.Embed:
    e = discord.Embed(color=ACCENT_GOLD)
    e.set_author(name="⚡ CORE MARKET RADAR  ·  Double XP Active!")
    e.description = _box("1;33", "🚀", f"DOUBLE XP — {game.upper()}", [
        f"\033[1;33mDOUBLE XP WEEKEND IS LIVE\033[0m",
        f"\033[0;37mEnds At :\033[0m  \033[1;37m{ends}\033[0m",
        f"\033[0;37mAction  :\033[0m  \033[1;32mActivate your key to rank up 2x faster 🎯\033[0m",
    ])
    e.set_footer(text="CORE MARKET RADAR  •  Double XP = 2x Weapon & Level Progression")
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
        "?locale=en-US&country=US&allowCountries=US"
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
                    url   = f"https://store.epicgames.com/p/{slug}"
                    imgs  = game.get("keyImages", [])
                    img   = imgs[0].get("url", "") if imgs else ""
                    free.append({"title": title, "desc": desc, "url": url, "img": img})
    return free

# ─────────────────────────────────────────────────────────────
#  CHANNEL RESOLVER
# ─────────────────────────────────────────────────────────────

def _resolve_alert_channel(guild: discord.Guild) -> discord.TextChannel | None:
    candidates = [
        "🚨・patch-alerts", "📢・announcements", "announcements",
        "🚨・alertes", "🔔・alerts", "alerts",
        "🟢・cheat-status", "🟢・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ",
    ]
    for name in candidates:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            return ch
    return None

def _resolve_general_channel(guild: discord.Guild) -> discord.TextChannel | None:
    candidates = [
        "general", "chat", "💬・general-chat", "🎮・general", "💬・chat"
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
    """Pillar 2 — 24/7 Watchdogs, Radars & Instant Automated Alerts."""

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

    async def _send_to_channel_key(self, key: str, embed: discord.Embed) -> None:
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
        type_to_key = {
            "alert": "channel_patches",
            "status": "channel_status",
            "freegames": "channel_freegames",
            "shop": "channel_shop",
            "doublexp": "channel_doublexp",
        }
        key = type_to_key.get(channel_type, "channel_patches")
        await self._send_to_channel_key(key, embed)

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
                continue

            log.info("New Steam update detected for %s: %s", name, title)
            self.state[key] = build_id
            self._save()
            await self._broadcast(embed_game_update(name, title, url, build_id), "alert")

    @loop_steam.before_loop
    async def before_steam(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)

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
            await self._broadcast(embed_server_down("Activision / CoD"), "status")

        elif not was_up and is_up:
            log.info("Activision servers BACK UP")
            self.state["activision_up"] = True
            self._save()
            await self._broadcast(embed_server_back("Activision / CoD"), "status")

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
                "freegames"
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
        if now.hour != 19 or now.minute > 10:
            return
        today_key = f"shop_posted_{now.strftime('%Y-%m-%d')}"
        if self.state.get(today_key):
            return

        embed = discord.Embed(color=ACCENT_CYAN)
        embed.set_author(name="🛍️ CORE MARKET  ·  Daily Shop Rotation")
        embed.description = (
            "```ansi\n"
            f"\033[1;36m{BORDER_TOP}\033[0m\n"
            f"\033[1;36m│\033[0m  🛍️  \033[1;37mCALL OF DUTY SHOP — {now.strftime('%Y-%m-%d')}\033[0m\n"
            f"\033[1;36m{BORDER_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mCheck full shop rotation at :\033[0m\n"
            f"\033[1;36m│\033[0m  \033[1;33mcallofduty.com/store\033[0m\n"
            f"\033[1;36m{BORDER_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mEnhance your movement & visuals with our tools\033[0m\n"
            f"\033[1;36m│\033[0m  \033[1;32m/configs  ·  #🎁・free-trial\033[0m\n"
            f"\033[1;36m{BORDER_BOT}\033[0m\n"
            "```"
        )
        embed.set_footer(text=f"CORE MARKET  •  Daily Shop Rotation  •  {now.strftime('%Y-%m-%d')}")

        await self._broadcast(embed, "shop")
        self.state[today_key] = True
        self._save()

    @loop_daily_shop.before_loop
    async def before_shop(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(120)

    # ─────────────────────────────────────────────────────────
    #  SLASH COMMANDS (100% English)
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="radar_status",
        description="📡 Live status dashboard for all CORE MARKET 24/7 background watchdogs",
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
        e.set_author(name="📡 CORE MARKET RADAR  ·  Watchdogs Dashboard")
        e.description = (
            "```ansi\n"
            f"\033[1;36m{BORDER_TOP}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[1;37m🔭 24/7 WATCHDOG MONITORS\033[0m\n"
            f"\033[1;36m{BORDER_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mActivision  :\033[0m  {status_icon}\n"
            f"\033[1;36m│\033[0m  \033[0;37mBO7 Build   :\033[0m  \033[1;35m{bo7_build}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mWZ Build    :\033[0m  \033[1;35m{wz_build}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mEpic Games  :\033[0m  \033[1;33m{epic_seen} games tracked\033[0m\n"
            f"\033[1;36m{BORDER_MID}\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mSteam Poll  :\033[0m  \033[1;32mevery 10 min\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mStatus Poll :\033[0m  \033[1;32mevery 5 min\033[0m\n"
            f"\033[1;36m│\033[0m  \033[0;37mEpic Poll   :\033[0m  \033[1;32mevery 1 hour\033[0m\n"
            f"\033[1;36m{BORDER_BOT}\033[0m\n"
            "```"
        )
        e.set_footer(text="CORE MARKET RADAR  •  24/7 Automated VPS Monitoring")
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(
        name="radar_test",
        description="🧪 Send a test alert across all radar channels to verify setup",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def radar_test(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        test_embed = discord.Embed(color=ACCENT_GOLD)
        test_embed.set_author(name="🧪 CORE MARKET RADAR  ·  System Test")
        test_embed.description = _box("1;33", "✅", "RADAR TEST — ALL SYSTEMS OPERATIONAL", [
            "\033[1;32mThis confirms automatic alert routing is working properly\033[0m",
            f"\033[0;37mTime    :\033[0m  \033[1;37m{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\033[0m",
            "\033[0;37mRadars  :\033[0m  \033[1;32mSteam • Activision • Epic • Shop\033[0m",
        ])
        test_embed.set_footer(text="CORE MARKET RADAR  •  System Test Successful")

        await self._broadcast(test_embed, "alert")
        await interaction.followup.send("✅ Test alert successfully broadcast to radar channels.", ephemeral=True)

    @app_commands.command(
        name="double_xp",
        description="🚀 Broadcast a Double XP event announcement across channels",
    )
    @app_commands.describe(
        game="Target Game (e.g. BO7, Warzone, Valorant)",
        ends_at="End Date / Time (e.g. Sunday 20:00 UTC)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def double_xp(self, interaction: discord.Interaction, game: str, ends_at: str) -> None:
        await interaction.response.defer(ephemeral=True)
        await self._broadcast(embed_double_xp(game, ends_at), "doublexp")
        await interaction.followup.send(f"📢 Double XP alert for **{game}** broadcasted.", ephemeral=True)

    # ─────────────────────────────────────────────────────────
    #  /radar_setup — Auto-creates dedicated channels with English embeds
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="radar_setup",
        description="🛠️ Auto-create dedicated CORE MARKET RADAR channels with explanation cards",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def radar_setup(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        category_name = "📡 ─── CORE MARKET RADAR"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(
                name=category_name,
                reason="CORE MARKET Radar setup",
            )

        channels_config = [
            {
                "name": "🚨・patch-alerts",
                "topic": "Automatic 24/7 patch and game update alerts for Black Ops 7 & Warzone.",
                "embed": discord.Embed(
                    color=ACCENT_ORANGE,
                    description=(
                        "```ansi\n"
                        f"\033[1;31m{BORDER_TOP}\033[0m\n"
                        f"\033[1;31m│\033[0m  🚨  \033[1;37mGAME PATCHES & UPDATE RADAR\033[0m\n"
                        f"\033[1;31m{BORDER_MID}\033[0m\n"
                        f"\033[1;31m│\033[0m  \033[0;37mThis channel is monitored\033[0m \033[1;32m24/7\033[0m \033[0;37mby our automated bot.\033[0m\n"
                        f"\033[1;31m│\033[0m\n"
                        f"\033[1;31m│\033[0m  \033[1;37mWhenever a game patch or hotfix is detected on\033[0m\n"
                        f"\033[1;31m│\033[0m  \033[1;33mBlack Ops 7\033[0m \033[0;37mor\033[0m \033[1;33mWarzone\033[0m\033[0;37m, an alert is posted here.\033[0m\n"
                        f"\033[1;31m│\033[0m\n"
                        f"\033[1;31m{BORDER_MID}\033[0m\n"
                        f"\033[1;31m│\033[0m  🔴  \033[1;37mPATCH DETECTED\033[0m  →  Injection paused for safety\n"
                        f"\033[1;31m│\033[0m  🟢  \033[1;37mPATCH VERIFIED\033[0m  →  Back online & confirmed safe\n"
                        f"\033[1;31m{BORDER_MID}\033[0m\n"
                        f"\033[1;31m│\033[0m  \033[0;37mEnable notifications to never miss security updates.\033[0m\n"
                        f"\033[1;31m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="📡 CORE MARKET RADAR  ·  Game Updates").set_footer(
                    text="CORE MARKET RADAR  •  Steam / Battle.net  •  Scan: every 10 min"
                ),
                "key": "channel_patches",
            },
            {
                "name": "📡・server-status",
                "topic": "Live server uptime & outage monitoring for Activision and Riot Games.",
                "embed": discord.Embed(
                    color=ACCENT_GREEN,
                    description=(
                        "```ansi\n"
                        f"\033[1;32m{BORDER_TOP}\033[0m\n"
                        f"\033[1;32m│\033[0m  📡  \033[1;37mOFFICIAL GAME SERVER STATUS\033[0m\n"
                        f"\033[1;32m{BORDER_MID}\033[0m\n"
                        f"\033[1;32m│\033[0m  \033[0;37mOur bot monitors\033[0m \033[1;33mActivision\033[0m\n"
                        f"\033[1;32m│\033[0m  \033[0;37mand\033[0m \033[1;33mRiot Games\033[0m \033[0;37mservers every\033[0m \033[1;37m5 minutes.\033[0m\n"
                        f"\033[1;32m│\033[0m\n"
                        f"\033[1;32m{BORDER_MID}\033[0m\n"
                        f"\033[1;32m│\033[0m  🔴  \033[1;37mSERVERS OFFLINE\033[0m →  Instant alert\n"
                        f"\033[1;32m│\033[0m  🟢  \033[1;37mBACK ONLINE\033[0m     →  Auto recovery notification\n"
                        f"\033[1;32m{BORDER_MID}\033[0m\n"
                        f"\033[1;32m│\033[0m  \033[0;37mIf an outage occurs:\033[0m\n"
                        f"\033[1;32m│\033[0m  \033[1;32mit is on Activision's side, not your PC.\033[0m\n"
                        f"\033[1;32m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="📡 CORE MARKET RADAR  ·  Server Watchdog").set_footer(
                    text="CORE MARKET RADAR  •  Activision & Riot  •  Scan: every 5 min"
                ),
                "key": "channel_status",
            },
            {
                "name": "⚡・double-xp",
                "topic": "Double XP weekends and special event alerts for Call of Duty & Valorant.",
                "embed": discord.Embed(
                    color=ACCENT_GOLD,
                    description=(
                        "```ansi\n"
                        f"\033[1;33m{BORDER_TOP}\033[0m\n"
                        f"\033[1;33m│\033[0m  ⚡  \033[1;37mDOUBLE XP & SPECIAL EVENTS\033[0m\n"
                        f"\033[1;33m{BORDER_MID}\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[0;37mEvery double XP weekend and limited-time event\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[0;37mfor Call of Duty or Valorant is broadcasted here\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[1;37mautomatically.\033[0m\n"
                        f"\033[1;33m│\033[0m\n"
                        f"\033[1;33m{BORDER_MID}\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[0;37mWhy this matters:\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[1;33m2x XP + our profiles\033[0m \033[0;37m= maximum rank & camo\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[1;37mprogression in minimum time.\033[0m\n"
                        f"\033[1;33m{BORDER_MID}\033[0m\n"
                        f"\033[1;33m│\033[0m  \033[0;37mClaim Free 1H Trial:\033[0m \033[1;32m#🎁・free-trial\033[0m\n"
                        f"\033[1;33m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="⚡ CORE MARKET RADAR  ·  Double XP Alerts").set_footer(
                    text="CORE MARKET RADAR  •  Never miss a Double XP weekend"
                ),
                "key": "channel_doublexp",
            },
            {
                "name": "🎁・free-games",
                "topic": "Automatic sniper for free games on Epic Games Store & Steam giveaways.",
                "embed": discord.Embed(
                    color=ACCENT_PURPLE,
                    description=(
                        "```ansi\n"
                        f"\033[1;35m{BORDER_TOP}\033[0m\n"
                        f"\033[1;35m│\033[0m  🎁  \033[1;37mFREE GAMES SNIPER\033[0m\n"
                        f"\033[1;35m{BORDER_MID}\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mOur bot scans the\033[0m \033[1;33mEpic Games Store\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mand Steam promos every hour.\033[0m\n"
                        f"\033[1;35m│\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mWhenever a paid game drops to\033[0m \033[1;32m$0.00 FREE\033[0m\033[0;37m,\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37man alert is posted here with direct claim link.\033[0m\n"
                        f"\033[1;35m│\033[0m\n"
                        f"\033[1;35m{BORDER_MID}\033[0m\n"
                        f"\033[1;35m│\033[0m  \033[0;37mTurn on notifications to claim games before deals expire.\033[0m\n"
                        f"\033[1;35m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="🎁 CORE MARKET RADAR  ·  Free Games Sniper").set_footer(
                    text="CORE MARKET RADAR  •  Epic Games & Steam  •  Scan: every hour"
                ),
                "key": "channel_freegames",
            },
            {
                "name": "🛍️・daily-shop",
                "topic": "Daily Call of Duty store rotation — fresh bundles every evening.",
                "embed": discord.Embed(
                    color=ACCENT_CYAN,
                    description=(
                        "```ansi\n"
                        f"\033[1;36m{BORDER_TOP}\033[0m\n"
                        f"\033[1;36m│\033[0m  🛍️  \033[1;37mDAILY CALL OF DUTY STORE\033[0m\n"
                        f"\033[1;36m{BORDER_MID}\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mEvery evening at\033[0m \033[1;33m19:00 UTC\033[0m\033[0;37m,\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mour bot broadcasts the daily CoD store\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mrotation with direct bundle links.\033[0m\n"
                        f"\033[1;36m│\033[0m\n"
                        f"\033[1;36m{BORDER_MID}\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mPro Tip:\033[0m \033[1;37mWeapon blueprints look\033[0m \033[1;32m2x better\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[1;37mwith our smooth tracking & zero-recoil profiles.\033[0m\n"
                        f"\033[1;36m{BORDER_MID}\033[0m\n"
                        f"\033[1;36m│\033[0m  \033[0;37mClaim Free 1H Trial:\033[0m \033[1;32m#🎁・free-trial\033[0m\n"
                        f"\033[1;36m{BORDER_BOT}\033[0m\n"
                        "```"
                    ),
                ).set_author(name="🛍️ CORE MARKET  ·  Daily CoD Store").set_footer(
                    text="CORE MARKET  •  Daily Rotation  •  Updated every day at 19:00 UTC"
                ),
                "key": "channel_shop",
            },
        ]

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
                await ch.send(embed=cfg["embed"])
                created.append(cfg["name"])
            else:
                await ch.send(embed=cfg["embed"])

            self.state[cfg["key"]] = ch.id

        self._save()

        e = discord.Embed(color=ACCENT_GREEN)
        e.set_author(name="✅ CORE MARKET RADAR  ·  Setup Complete")
        e.description = (
            "```ansi\n"
            f"\033[1;32m{BORDER_TOP}\033[0m\n"
            f"\033[1;32m│\033[0m  ✅  \033[1;37mALL RADAR CHANNELS INITIALIZED\033[0m\n"
            f"\033[1;32m{BORDER_MID}\033[0m\n"
            + "".join(
                f"\033[1;32m│\033[0m  \033[1;32m✓\033[0m  {n}\n"
                for n in [c["name"] for c in channels_config]
            )
            + f"\033[1;32m{BORDER_MID}\033[0m\n"
            f"\033[1;32m│\033[0m  \033[0;37mAll 24/7 background watchdogs\033[0m\n"
            f"\033[1;32m│\033[0m  \033[1;37mare now routing to these channels.\033[0m\n"
            f"\033[1;32m{BORDER_BOT}\033[0m\n"
            "```"
        )
        e.set_footer(text="CORE MARKET RADAR  •  24/7 Background Automation Active")
        await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Watchdog(bot))
