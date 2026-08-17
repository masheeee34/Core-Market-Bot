import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.status import load_status_data, save_status_data, update_status_message_and_channel
from cogs.translator import TranslateButtonView

log = logging.getLogger("cogs.radar")
RADAR_STATE_FILE = Path("data/game_radar_state.json")

STEAM_COD_APPID = "1938090"  # Call of Duty (HQ / Warzone / BO6 / BO7)


def load_radar_state() -> dict[str, Any]:
    if not RADAR_STATE_FILE.exists():
        return {}
    try:
        with open(RADAR_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Error loading radar state: %s", e)
        return {}


def save_radar_state(data: dict[str, Any]) -> None:
    RADAR_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RADAR_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class RadarCog(commands.Cog):
    """Automated Game Patch & Anti-Cheat Update Monitor."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.patch_monitor.start()

    def cog_unload(self) -> None:
        self.patch_monitor.cancel()

    @tasks.loop(minutes=10)
    async def patch_monitor(self) -> None:
        """Polls Steam & game APIs to detect sudden version bumps or anti-cheat patches."""
        try:
            url = f"https://api.steampowered.com/ISteamApps/UpToDateCheck/v1/?appid={STEAM_COD_APPID}&version=0"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        required_version = str(data.get("response", {}).get("required_version", ""))
                        if required_version:
                            state = load_radar_state()
                            last_ver = state.get("last_cod_version")
                            if last_ver and last_ver != required_version:
                                log.warning("CoD Patch detected! Previous: %s, Current: %s", last_ver, required_version)
                                state["last_cod_version"] = required_version
                                state["last_patch_time"] = datetime.now(timezone.utc).isoformat()
                                save_radar_state(state)
                                await self._handle_detected_patch(
                                    game_name="Call of Duty (BO7 / Warzone)",
                                    patch_id=f"Build {required_version}",
                                    products=["spectre", "mcore"],
                                )
                            else:
                                state["last_cod_version"] = required_version
                                save_radar_state(state)
        except Exception as e:
            log.debug("Patch monitor check error: %s", e)

    @patch_monitor.before_loop
    async def before_patch_monitor(self) -> None:
        await self.bot.wait_until_ready()

    async def _handle_detected_patch(self, game_name: str, patch_id: str, products: list[str]) -> None:
        """Automatically flips affected software to UPDATING and notifies the guild."""
        status_data = load_status_data()
        for prod in products:
            if prod in status_data:
                status_data[prod]["status"] = "UPDATING"
                status_data[prod]["notes"] = f"Patch {patch_id} detected • Testing in progress"

        save_status_data(status_data)

        for guild in self.bot.guilds:
            if self.bot.user:
                await update_status_message_and_channel(guild, self.bot.user, status_data)

            # Broadcast security warning
            ann_ch = (
                discord.utils.get(guild.text_channels, name="📢・announcements")
                or discord.utils.get(guild.text_channels, name="announcements")
                or discord.utils.get(guild.text_channels, name="🟢・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ")
            )

            if ann_ch:
                embed = discord.Embed(
                    title="⚠️  SECURITY RADAR — GAME UPDATE DETECTED",
                    description=(
                        f"> **A new update has been pushed for `{game_name}` (`{patch_id}`).**\n\n"
                        "```ansi\n"
                        "\u001b[1;33m[ 🛡️ AUTOMATIC SAFETY FREEZE ]\u001b[0m\n"
                        "```\n"
                        "▸ **Action Taken :** Injection is temporarily marked **`UPDATING`**.\n"
                        "▸ **Recommendation :** Do **NOT** inject your software until tests are completed.\n"
                        "▸ **Estimated Verification :** 15 to 45 minutes.\n\n"
                        "──────────────────────────────────────────\n"
                        "🔔 *You will receive an automated notification as soon as testing is verified safe!*"
                    ),
                    color=discord.Color.gold(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_footer(text="CORE MARKET SECURITY • Zero-Ban Guard • Automated Radar")
                try:
                    await ann_ch.send(embed=embed, view=TranslateButtonView())
                except Exception as e:
                    log.warning("Could not send patch announcement: %s", e)

    @app_commands.command(name="game_patch_alert", description="Manually trigger an automated game update & freeze alert")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        game=[
            app_commands.Choice(name="Call of Duty (BO7 / Warzone)", value="cod"),
            app_commands.Choice(name="Valorant (Riot Vanguard)", value="valorant"),
        ],
    )
    async def manual_patch_alert_cmd(self, interaction: discord.Interaction, game: str, patch_notes: str | None = None) -> None:
        await interaction.response.defer(ephemeral=True)

        if game == "cod":
            game_name = "Call of Duty (BO7 / Warzone)"
            products = ["spectre", "mcore"]
        else:
            game_name = "Valorant (Riot Vanguard)"
            products = ["valorant_pulse"]

        patch_id = patch_notes or f"Patch {datetime.now(timezone.utc).strftime('%d/%m %H:%M')}"
        await self._handle_detected_patch(game_name=game_name, patch_id=patch_id, products=products)

        await interaction.followup.send(
            f"✅ Alerte radar déclenchée pour **{game_name}** ! Les logiciels ont été passés en `UPDATING` et l'annonce a été diffusée.",
            ephemeral=True,
        )

    @app_commands.command(name="game_patch_resolved", description="Resolve patch alert and mark software back to 100% UNDETECTED")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        game=[
            app_commands.Choice(name="Call of Duty (BO7 / Warzone)", value="cod"),
            app_commands.Choice(name="Valorant (Riot Vanguard)", value="valorant"),
            app_commands.Choice(name="Tous les logiciels (All Safe)", value="all"),
        ],
    )
    async def manual_patch_resolved_cmd(self, interaction: discord.Interaction, game: str) -> None:
        await interaction.response.defer(ephemeral=True)
        status_data = load_status_data()

        if game == "cod":
            targets = ["spectre", "mcore"]
            game_name = "Call of Duty"
        elif game == "valorant":
            targets = ["valorant_pulse"]
            game_name = "Valorant"
        else:
            targets = list(status_data.keys())
            game_name = "All Software"

        for key in targets:
            if key in status_data:
                status_data[key]["status"] = "UNDETECTED"
                status_data[key]["notes"] = "Verified 100% Safe & Operational after patch"

        save_status_data(status_data)

        if interaction.guild and self.bot.user:
            await update_status_message_and_channel(interaction.guild, self.bot.user, status_data)

            ann_ch = (
                discord.utils.get(interaction.guild.text_channels, name="📢・announcements")
                or discord.utils.get(interaction.guild.text_channels, name="announcements")
                or discord.utils.get(interaction.guild.text_channels, name="🟢・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ")
            )

            if ann_ch:
                embed = discord.Embed(
                    title="🟢  SECURITY RADAR — UPDATE COMPLETED & 100% SAFE",
                    description=(
                        f"> **Testing and bypass integrity verification for `{game_name}` is COMPLETE.**\n\n"
                        "```ansi\n"
                        "\u001b[1;32m[ 🛡️ 100% OPERATIONAL & UNDETECTED ]\u001b[0m\n"
                        "```\n"
                        "▸ **Status :** All software is fully operational and safe to inject.\n"
                        "▸ **Loader Action :** Restart your Loader to apply the latest offsets automatically.\n\n"
                        "──────────────────────────────────────────\n"
                        "🎮 *Good luck and enjoy your games with Core Market!*"
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.set_footer(text="CORE MARKET SECURITY • Zero-Ban Guard • Automated Radar")
                try:
                    await ann_ch.send(embed=embed, view=TranslateButtonView())
                except Exception:
                    pass

        await interaction.followup.send(
            f"✅ Sécurité confirmée pour **{game_name}** ! Statut repassé en `UNDETECTED` vert.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RadarCog(bot))
