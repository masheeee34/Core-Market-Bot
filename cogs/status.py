import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("cogs.status")
STATUS_FILE = Path("data/cheat_status.json")

DEFAULT_STATUS = {
    "spectre": {"name": "TRINITY SPECTRE (BO7 / WZ)", "status": "UNDETECTED", "color": "green", "notes": "External Ring-0 • Streamproof • Safe"},
    "mcore": {"name": "M-CORE EXTERNAL", "status": "UNDETECTED", "color": "green", "notes": "Kernel Overlay • ESP & Aim • Safe"},
    "perm_spoofer": {"name": "PERMANENT HWID SPOOFER", "status": "UNDETECTED", "color": "green", "notes": "Motherboard / Disk / NIC Spoofed • Safe"},
    "temp_spoofer": {"name": "TEMPORARY SPOOFER", "status": "UNDETECTED", "color": "green", "notes": "Instant Spoof Session • Safe"},
    "ricochet": {"name": "RICOCHET ANTI-CHEAT BYPASS", "status": "OPERATIONAL", "color": "green", "notes": "Hypervisor / Ring-0 Guard Active"},
}

STATUS_EMOJIS = {
    "UNDETECTED": "🟢",
    "OPERATIONAL": "🟢",
    "UPDATING": "🟡",
    "TESTING": "🟡",
    "MAINTENANCE": "🔴",
    "DETECTED": "🔴",
    "OFFLINE": "🔴",
}

STATUS_COLORS = {
    "UNDETECTED": "#00FF66",
    "OPERATIONAL": "#00FF66",
    "UPDATING": "#FFCC00",
    "TESTING": "#FFCC00",
    "MAINTENANCE": "#FF3333",
    "DETECTED": "#FF0000",
    "OFFLINE": "#FF0000",
}


def load_status_data() -> dict[str, Any]:
    if not STATUS_FILE.exists():
        save_status_data(DEFAULT_STATUS)
        return DEFAULT_STATUS
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Error loading status data: %s", e)
        return DEFAULT_STATUS


def save_status_data(data: dict[str, Any]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_status_embed(data: dict[str, Any]) -> discord.Embed:
    all_green = all(item.get("status") in ("UNDETECTED", "OPERATIONAL") for item in data.values())
    embed_color = discord.Color.green() if all_green else discord.Color.gold()

    lines = [
        "> **Official real-time operational status for all Core Market software.**\n"
        "> *Updates automatically when anti-cheat patches or maintenance occurs.*\n\n"
        "```ansi\n"
        "\u001b[1;32m[ 🛡️ LIVE SOFTWARE & SPOOFER STATUS ]\u001b[0m\n"
        "```"
    ]

    for key, info in data.items():
        st = info.get("status", "UNDETECTED")
        emoji = STATUS_EMOJIS.get(st, "🟢")
        name = info.get("name", key.upper())
        notes = info.get("notes", "")

        status_badge = f"` {st} `" if st in ("UNDETECTED", "OPERATIONAL") else f"**` {st} `**"
        lines.append(f"{emoji} **{name}** ➔ {status_badge}")
        if notes:
            lines.append(f"   └─ *{notes}*")

    lines.append(
        "\n```ansi\n"
        "\u001b[1;36m[ ⚡ REFRESH & SUPPORT ]\u001b[0m\n"
        "```\n"
        "▸ **Need a Free Trial (1H)?** Claim in <#🎁・free-trial>\n"
        "▸ **Questions or Orders?** Open a ticket in <#🎫・creer-un-ticket>\n"
        f"▸ **Last Verified :** <t:{int(datetime.now(timezone.utc).timestamp())}:R>"
    )

    embed = discord.Embed(
        title="🟢  CORE MARKET — LIVE CHEAT & SPOOFER STATUS",
        description="\n".join(lines),
        color=embed_color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="CORE MARKET • 100% Streamproof & Ring-0 Hypervisor • Real-time Protection")
    return embed


class StatusCog(commands.Cog):
    """Live Cheat & Spoofer status board with automatic updates and interactive management."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup_status_channel", description="Create or setup the official live #status-cheats channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_status_cmd(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if not guild:
            return

        await interaction.response.defer(ephemeral=True)
        channel_name = "🟢・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ"

        # Check existing or create channel
        ch = discord.utils.get(guild.text_channels, name=channel_name) or discord.utils.get(
            guild.text_channels, name="status-cheats"
        )
        if not ch:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(send_messages=False, add_reactions=False, view_channel=True),
                guild.me: discord.PermissionOverwrite(send_messages=True, embed_links=True, view_channel=True),
            }
            ch = await guild.create_text_channel(
                channel_name,
                overwrites=overwrites,
                reason="Official Core Market Status Board",
            )

        data = load_status_data()
        embed = build_status_embed(data)

        # Post or edit message
        msg = await ch.send(embed=embed)
        data["_status_channel_id"] = ch.id
        data["_status_message_id"] = msg.id
        save_status_data(data)

        await interaction.followup.send(f"✅ Status Board created and published in {ch.mention}!", ephemeral=True)

    @app_commands.command(name="set_cheat_status", description="Update the live operational status of a cheat or spoofer")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        product=[
            app_commands.Choice(name="🔮 Trinity Spectre (BO7 / WZ)", value="spectre"),
            app_commands.Choice(name="🎯 M-Core External", value="mcore"),
            app_commands.Choice(name="🛡️ Permanent Spoofer", value="perm_spoofer"),
            app_commands.Choice(name="⚡ Temporary Spoofer", value="temp_spoofer"),
            app_commands.Choice(name="🛡️ Ricochet Bypass", value="ricochet"),
        ],
        status=[
            app_commands.Choice(name="🟢 UNDETECTED (Operational)", value="UNDETECTED"),
            app_commands.Choice(name="🟡 UPDATING (In Maintenance/Testing)", value="UPDATING"),
            app_commands.Choice(name="🔴 OFFLINE (Under Maintenance)", value="OFFLINE"),
        ],
    )
    async def update_status_cmd(
        self,
        interaction: discord.Interaction,
        product: str,
        status: str,
        custom_notes: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        data = load_status_data()

        if product not in data:
            data[product] = {"name": product.upper(), "status": status, "notes": ""}

        data[product]["status"] = status
        if custom_notes:
            data[product]["notes"] = custom_notes
        save_status_data(data)

        # Update the live message in Discord
        ch_id = data.get("_status_channel_id")
        msg_id = data.get("_status_message_id")
        if ch_id and msg_id:
            try:
                ch = self.bot.get_channel(int(ch_id))
                if isinstance(ch, discord.TextChannel):
                    msg = await ch.fetch_message(int(msg_id))
                    await msg.edit(embed=build_status_embed(data))
            except Exception as e:
                log.warning("Could not edit status message: %s", e)

        await interaction.followup.send(
            f"✅ Statut mis à jour pour **{data[product]['name']}** ➔ **`{status}`** !",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatusCog(bot))
