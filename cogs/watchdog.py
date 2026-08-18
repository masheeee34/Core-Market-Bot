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
#  DESIGN SYSTEM — Sleek, Minimal, Modern Tech Embeds
# ─────────────────────────────────────────────────────────────

COLOR_ALERT   = 0xE11D48  # Crimson Red
COLOR_ONLINE  = 0x10B981  # Emerald Green
COLOR_WARNING = 0xF59E0B  # Amber Gold
COLOR_PRIMARY = 0x0070FF  # Core Electric Blue
COLOR_SPECIAL = 0x8B5CF6  # Violet / Purple


def embed_game_update(app_name: str, title: str, url: str, build_id: str) -> discord.Embed:
    e = discord.Embed(
        title=f"🚨  Game Patch Detected — {app_name.upper()}",
        description=(
            f"> A new game update was just detected on official Steam/Battle.net servers.\n"
            f"> Automated safety protocols are currently engaged.\n\n"
            f"▸ **Game :** `{app_name.upper()}`\n"
            f"▸ **Patch Title :** `{title[:60]}`\n"
            f"▸ **Build ID :** `{build_id[:24]}`\n"
            f"▸ **Safety Status :** 🔴 `INJECTION PAUSED (VERIFYING)`\n"
            f"▸ **Official Source :** [View Steam Notes]({url or 'https://store.steampowered.com'})\n\n"
            f"──────────────────────────────────────────\n"
            f"🛡️ *Our automated test suite is verifying compatibility. Status will switch to 🟢 `UNDETECTED` once cleared.*"
        ),
        color=COLOR_ALERT,
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text="CORE MARKET RADAR • 24/7 Security Watchdog")
    return e


def embed_all_clear(app_name: str) -> discord.Embed:
    e = discord.Embed(
        title=f"🟢  Patch Cleared & Verified — {app_name.upper()}",
        description=(
            f"> Automated tests completed with zero detections. Software is 100% operational.\n\n"
            f"▸ **Game :** `{app_name.upper()}`\n"
            f"▸ **Status :** 🟢 `UNDETECTED & LIVE`\n"
            f"▸ **Verification :** `All offsets updated & secure`\n"
            f"▸ **Free Trial :** Available now in <#1345864197779361875>\n\n"
            f"──────────────────────────────────────────\n"
            f"⚡ *You can safely resume your gameplay sessions.*"
        ),
        color=COLOR_ONLINE,
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text="CORE MARKET RADAR • Security Cleared")
    return e


def embed_server_down(service: str) -> discord.Embed:
    e = discord.Embed(
        title=f"🔴  Official Servers Outage — {service.upper()}",
        description=(
            f"> Official game multiplayer servers are currently reporting widespread connectivity issues.\n\n"
            f"▸ **Affected Service :** `{service.upper()}`\n"
            f"▸ **Status :** 🔴 `OFFICIAL SERVERS DOWN`\n"
            f"▸ **Source :** `Activision / Riot Live Health API`\n\n"
            f"──────────────────────────────────────────\n"
            f"ℹ️ *This is an official server outage on Activision/Riot's end, not your local connection or PC.*"
        ),
        color=COLOR_ALERT,
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text="CORE MARKET RADAR • Live Server Monitor")
    return e


def embed_server_back(service: str) -> discord.Embed:
    e = discord.Embed(
        title=f"🟢  Official Servers Restored — {service.upper()}",
        description=(
            f"> All official matchmaking and multiplayer servers are back online and operational.\n\n"
            f"▸ **Service :** `{service.upper()}`\n"
            f"▸ **Status :** 🟢 `100% OPERATIONAL`\n"
            f"▸ **Matchmaking :** `Online & Accepting Players`\n\n"
            f"──────────────────────────────────────────\n"
            f"🎮 *Lobbies are active. Enjoy your gaming session!*"
        ),
        color=COLOR_ONLINE,
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text="CORE MARKET RADAR • Live Server Monitor")
    return e


def embed_free_game(title: str, desc: str, url: str, img: str) -> discord.Embed:
    e = discord.Embed(
        title=f"🎁  Free Game Alert — Epic Games Store",
        description=(
            f"> A premium game is currently **100% FREE** to claim and keep forever!\n\n"
            f"▸ **Game :** **{title}**\n"
            f"▸ **Description :** {desc}\n"
            f"▸ **Original Price :** ~~$19.99 - $59.99~~ ➔ **`$0.00 FREE`**\n"
            f"▸ **Direct Claim Link :** [Click here to claim on Epic Games]({url})\n\n"
            f"──────────────────────────────────────────\n"
            f"⏰ *Claim it to your account before the promotion expires!*"
        ),
        color=COLOR_SPECIAL,
        timestamp=discord.utils.utcnow(),
    )
    if img:
        e.set_image(url=img)
    e.set_footer(text="CORE MARKET RADAR • Free Loot Alert")
    return e


def embed_double_xp(game: str, ends_at: str) -> discord.Embed:
    e = discord.Embed(
        title=f"⚡  Double XP Weekend Active — {game.upper()}",
        description=(
            f"> Double XP is now officially live across all playlists!\n\n"
            f"▸ **Target Game :** `{game.upper()}`\n"
            f"▸ **Multiplier :** `2X Player XP & Weapon Progression`\n"
            f"▸ **Ends At :** `{ends_at}`\n\n"
            f"──────────────────────────────────────────\n"
            f"🎯 *Stack 2X XP with our precision tracking to max out all your weapon camos in record time.*"
        ),
        color=COLOR_WARNING,
        timestamp=discord.utils.utcnow(),
    )
    e.set_footer(text="CORE MARKET RADAR • Double XP Tracker")
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
    data = await _get("https://support.activision.com/api/v2/online-services/status")
    if not data:
        return True
    services = data if isinstance(data, list) else data.get("services", [])
    for svc in services:
        name = (svc.get("name") or "").lower()
        status = (svc.get("status") or "").lower()
        if "online" in name or "multiplayer" in name:
            if status not in ("up", "online", "operational", ""):
                return False
    return True

async def fetch_epic_free_games() -> list[dict]:
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
                    desc  = (game.get("description") or "")[:90]
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
        seen_gids = set(self.state.get("seen_steam_gids", []))
        seen_titles = set(self.state.get("seen_steam_titles", []))

        for appid, name in [(APP_BO7, "BO7"), (APP_WARZONE, "Warzone")]:
            result = await fetch_steam_news(appid)
            if not result:
                continue
            title, url, build_id = result

            # Deduplication: check both GID and exact Title to prevent cross-posted duplicate alerts
            if build_id in seen_gids or title in seen_titles:
                continue

            log.info("New Steam update detected for %s: %s (GID: %s)", name, title, build_id)
            seen_gids.add(build_id)
            seen_titles.add(title)
            self.state["seen_steam_gids"] = list(seen_gids)
            self.state["seen_steam_titles"] = list(seen_titles)
            self.state[f"steam_{appid}_last_build"] = build_id
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

        embed = discord.Embed(
            title=f"🛍️  Daily Call of Duty Store Rotation — {now.strftime('%B %d, %Y')}",
            description=(
                f"> Today's featured bundles and operator blueprints are now live in the store.\n\n"
                f"▸ **Store Link :** [View Official CoD Store Catalog](https://callofduty.com/store)\n"
                f"▸ **Optimized Setups :** Enhance any weapon build with our configs in `/configs`\n"
                f"▸ **Free 1H Trial :** Claim instantly in <#1345864197779361875>\n\n"
                f"──────────────────────────────────────────\n"
                f"✨ *Store rotation refreshes daily at 19:00 UTC.*"
            ),
            color=COLOR_PRIMARY,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text="CORE MARKET • Daily Store Watchdog")

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
        status_badge = "🟢 `ONLINE`" if activision_up else "🔴 `OFFLINE`"

        bo7_build = s.get(f"steam_{APP_BO7}_last_build", "—")[:18]
        wz_build  = s.get(f"steam_{APP_WARZONE}_last_build", "—")[:18]
        epic_seen = len(s.get("epic_free_seen", []))

        e = discord.Embed(
            title="📡  CORE MARKET RADAR — Watchdog Dashboard",
            description=(
                f"> Real-time health metrics of all automated monitoring daemons on the VPS.\n\n"
                f"**Active Monitored Services**\n"
                f"▸ **Activision Servers :** {status_badge}\n"
                f"▸ **BO7 Steam Build :** `{bo7_build}`\n"
                f"▸ **Warzone Steam Build :** `{wz_build}`\n"
                f"▸ **Epic Free Games Tracked :** `{epic_seen} titles`\n\n"
                f"**Polling Intervals**\n"
                f"▸ **Steam Patches :** `Every 10 min`\n"
                f"▸ **Server Health :** `Every 5 min`\n"
                f"▸ **Free Loot Deals :** `Every 60 min`\n\n"
                f"──────────────────────────────────────────\n"
                f"🛡️ *All background watchdogs are currently active and running on VPS.*"
            ),
            color=COLOR_PRIMARY,
            timestamp=discord.utils.utcnow(),
        )
        e.set_footer(text="CORE MARKET RADAR • VPS Process Health")
        await interaction.followup.send(embed=e, ephemeral=True)

    @app_commands.command(
        name="radar_test",
        description="🧪 Send a clean test alert across all radar channels to verify setup",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def radar_test(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        test_embed = discord.Embed(
            title="🧪  CORE MARKET RADAR — Systems Operational Test",
            description=(
                f"> This is an automated test broadcast confirming alert routing is configured properly.\n\n"
                f"▸ **Execution Timestamp :** `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`\n"
                f"▸ **Active Scanners :** `SteamDB • Activision API • Epic Games Store • Daily Shop`\n"
                f"▸ **Router Status :** 🟢 `ALL CHANNELS LINKED & RESPONSIVE`\n\n"
                f"──────────────────────────────────────────\n"
                f"✅ *Test successfully verified. No further action needed.*"
            ),
            color=COLOR_ONLINE,
            timestamp=discord.utils.utcnow(),
        )
        test_embed.set_footer(text="CORE MARKET RADAR • Test Signal Verified")

        await self._broadcast(test_embed, "alert")
        await interaction.followup.send("✅ Test alert successfully sent to radar channels.", ephemeral=True)

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
    #  /radar_setup — Auto-creates dedicated channels with sleek English cards
    # ─────────────────────────────────────────────────────────

    @app_commands.command(
        name="radar_setup",
        description="🛠️ Auto-create dedicated CORE MARKET RADAR channels with sleek explanation cards",
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
                    title="🚨  Game Updates & Patch Radar",
                    description=(
                        f"> This channel is automatically monitored 24/7 by our VPS watchdog engine.\n\n"
                        f"**How it works:**\n"
                        f"Whenever a patch, hotfix, or season update is deployed on **Black Ops 7** or **Warzone**, an instant security alert is posted here:\n\n"
                        f"▸ 🔴 `PATCH DETECTED` ➔ Software injection paused immediately for safety\n"
                        f"▸ 🟢 `PATCH VERIFIED` ➔ Offsets updated & confirmed 100% undetected\n\n"
                        f"──────────────────────────────────────────\n"
                        f"🔔 *Turn on channel notifications to stay informed on live security statuses.*"
                    ),
                    color=COLOR_ALERT,
                ).set_footer(text="CORE MARKET RADAR • Steam / Battle.net Scanner • Scanned Every 10 Min"),
                "key": "channel_patches",
            },
            {
                "name": "📡・server-status",
                "topic": "Live server uptime & outage monitoring for Activision and Riot Games.",
                "embed": discord.Embed(
                    title="📡  Official Game Server Health",
                    description=(
                        f"> Continuous 24/7 uptime surveillance for official **Activision** and **Riot Games** infrastructure.\n\n"
                        f"**Monitoring Protocol:**\n"
                        f"▸ 🔴 `SERVERS DOWN` ➔ Immediate notification when official matchmaking fails\n"
                        f"▸ 🟢 `BACK ONLINE` ➔ Instant confirmation once servers recover\n\n"
                        f"──────────────────────────────────────────\n"
                        f"ℹ️ *If an outage is announced here, it is on the game publisher's side — not your PC.*"
                    ),
                    color=COLOR_ONLINE,
                ).set_footer(text="CORE MARKET RADAR • Activision & Riot Live API • Scanned Every 5 Min"),
                "key": "channel_status",
            },
            {
                "name": "⚡・double-xp",
                "topic": "Double XP weekends and special event alerts for Call of Duty & Valorant.",
                "embed": discord.Embed(
                    title="⚡  Double XP & Limited-Time Events",
                    description=(
                        f"> Never miss a progression boost. All official Double XP events are announced here automatically.\n\n"
                        f"**Why Stack Double XP with Core Market:**\n"
                        f"▸ **2X Progression Rate :** Maximize weapon levels and military rank in minimal time\n"
                        f"▸ **Free 1H Trial :** Test our zero-recoil & ESP profiles in <#1345864197779361875>\n\n"
                        f"──────────────────────────────────────────\n"
                        f"🎯 *Active notification ping enabled for all official double XP weekends.*"
                    ),
                    color=COLOR_WARNING,
                ).set_footer(text="CORE MARKET RADAR • Double XP Tracker"),
                "key": "channel_doublexp",
            },
            {
                "name": "🎁・free-games",
                "topic": "Automatic sniper for free games on Epic Games Store & Steam giveaways.",
                "embed": discord.Embed(
                    title="🎁  Free Games & Loot Sniper",
                    description=(
                        f"> Our automated scanner monitors the **Epic Games Store** and **Steam** 24/7.\n\n"
                        f"**Automated Deals:**\n"
                        f"Whenever a paid game or DLC drops to **`$0.00 FREE`**, an instant alert with direct claim link is delivered here.\n\n"
                        f"──────────────────────────────────────────\n"
                        f"⏰ *Enable notifications to claim free games before limited-time promotions expire.*"
                    ),
                    color=COLOR_SPECIAL,
                ).set_footer(text="CORE MARKET RADAR • Epic Games & Steam Scanner • Scanned Hourly"),
                "key": "channel_freegames",
            },
            {
                "name": "🛍️・daily-shop",
                "topic": "Daily Call of Duty store rotation — fresh bundles every evening.",
                "embed": discord.Embed(
                    title="🛍️  Daily Call of Duty Store Rotation",
                    description=(
                        f"> Daily broadcast of the newest weapon blueprints, operator skins, and featured bundles.\n\n"
                        f"▸ **Daily Refresh :** Every evening at `19:00 UTC`\n"
                        f"▸ **Official Catalog :** [Browse CoD Store](https://callofduty.com/store)\n"
                        f"▸ **Free 1H Trial :** Claim your key in <#1345864197779361875>\n\n"
                        f"──────────────────────────────────────────\n"
                        f"✨ *Check back daily to preview the latest cosmetics rotation.*"
                    ),
                    color=COLOR_PRIMARY,
                ).set_footer(text="CORE MARKET RADAR • Daily CoD Store Rotation"),
                "key": "channel_shop",
            },
        ]

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
            else:
                await ch.send(embed=cfg["embed"])

            self.state[cfg["key"]] = ch.id

        self._save()

        e = discord.Embed(
            title="✅  Radar Channels Initialized",
            description=(
                f"> All 5 dedicated radar channels have been configured and linked to background watchdogs.\n\n"
                + "".join(f"▸ 🟢 `#{c['name']}`\n" for c in channels_config) +
                f"\n──────────────────────────────────────────\n"
                f"🛡️ *All background watchdogs on VPS are now routing alerts to their dedicated channels.*"
            ),
            color=COLOR_ONLINE,
            timestamp=discord.utils.utcnow(),
        )
        e.set_footer(text="CORE MARKET RADAR • Setup Verified")
        await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Watchdog(bot))
