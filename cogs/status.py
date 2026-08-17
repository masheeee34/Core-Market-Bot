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

DEFAULT_STATUS: dict[str, dict[str, str]] = {
    "spectre": {"name": "TRINITY SPECTRE (BO7 / WZ)", "status": "UNDETECTED", "notes": "External Ring-0 • Streamproof • Safe"},
    "mcore": {"name": "M-CORE EXTERNAL", "status": "UNDETECTED", "notes": "Kernel Overlay • ESP & Aim • Safe"},
    "perm_spoofer": {"name": "PERMANENT HWID SPOOFER", "status": "UNDETECTED", "notes": "Motherboard / Disk / NIC Spoofed • Safe"},
    "temp_spoofer": {"name": "TEMPORARY SPOOFER", "status": "UNDETECTED", "notes": "Instant Spoof Session • Safe"},
    "ricochet": {"name": "RICOCHET ANTI-CHEAT BYPASS", "status": "OPERATIONAL", "notes": "Hypervisor / Ring-0 Guard Active"},
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


def load_status_data() -> dict[str, Any]:
    if not STATUS_FILE.exists():
        save_status_data(DEFAULT_STATUS)
        return DEFAULT_STATUS.copy()
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Error loading status data: %s", e)
        return DEFAULT_STATUS.copy()


def save_status_data(data: dict[str, Any]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_status_embed(data: dict[str, Any]) -> discord.Embed:
    clean_items = {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)}

    has_offline = any(item.get("status") in ("OFFLINE", "MAINTENANCE", "DETECTED") for item in clean_items.values())
    has_updating = any(item.get("status") in ("UPDATING", "TESTING") for item in clean_items.values())

    if has_offline:
        overall_title = "🔴  CORE MARKET — CHEAT STATUS (MAINTENANCE)"
        embed_color = discord.Color.from_str("#FF3333")
        ansi_header = "\u001b[1;31m[ ⚠️ ATTENTION • MAINTENANCE IN PROGRESS ]\u001b[0m"
    elif has_updating:
        overall_title = "🟡  CORE MARKET — CHEAT STATUS (UPDATING)"
        embed_color = discord.Color.from_str("#FFCC00")
        ansi_header = "\u001b[1;33m[ ⏳ GAME UPDATE • TESTING IN PROGRESS ]\u001b[0m"
    else:
        overall_title = "🟢  CORE MARKET — ALL CHEATS OPERATIONAL & UNDETECTED"
        embed_color = discord.Color.from_str("#00FF66")
        ansi_header = "\u001b[1;32m[ 🛡️ 100% OPERATIONAL & UNDETECTED ]\u001b[0m"

    lines = [
        "> **Real-time status monitor for all Call of Duty & Spoofer software.**\n"
        "> *Instant automated alerts when anti-cheat updates or patches drop.*\n\n"
        f"```ansi\n{ansi_header}\n```"
    ]

    for key, info in clean_items.items():
        st = info.get("status", "UNDETECTED").upper()
        emoji = STATUS_EMOJIS.get(st, "🟢")
        name = info.get("name", key.upper())
        notes = info.get("notes", "")

        if st in ("UNDETECTED", "OPERATIONAL"):
            status_box = f"```diff\n+ {name} ➔ [ {st} ]\n```"
        elif st in ("UPDATING", "TESTING"):
            status_box = f"```fix\n! {name} ➔ [ {st} ]\n```"
        else:
            status_box = f"```diff\n- {name} ➔ [ {st} ] (DO NOT USE)\n```"

        lines.append(f"{emoji} **{name}**")
        lines.append(status_box)
        if notes:
            lines.append(f"   └─ *{notes}*\n")

    lines.append(
        "```ansi\n"
        "\u001b[1;36m[ ⚡ QUICK ACCESS & ASSISTANCE ]\u001b[0m\n"
        "```\n"
        "▸ **🎁 Claim 1-Hour Free Trial :** <#🎁・free-trial>\n"
        "▸ **🎫 Technical Support & Orders :** <#🎫・creer-un-ticket>\n"
        f"▸ **Last Status Verification :** <t:{int(datetime.now(timezone.utc).timestamp())}:R>"
    )

    embed = discord.Embed(
        title=overall_title,
        description="\n".join(lines),
        color=embed_color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="CORE MARKET • Real-Time Protection • 100% Streamproof Hypervisor")
    return embed


async def update_status_message_and_channel(guild: discord.Guild, bot_user: discord.ClientUser, data: dict[str, Any]) -> tuple[bool, str]:
    """Finds or creates status channel, updates the live embed, and adjusts channel emoji."""
    clean_items = {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)}
    has_offline = any(item.get("status") in ("OFFLINE", "MAINTENANCE", "DETECTED") for item in clean_items.values())
    has_updating = any(item.get("status") in ("UPDATING", "TESTING") for item in clean_items.values())

    target_prefix = "🔴" if has_offline else ("🟡" if has_updating else "🟢")
    target_channel_name = f"{target_prefix}・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ"

    # Find status channel
    ch = (
        discord.utils.get(guild.text_channels, name="🟢・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ")
        or discord.utils.get(guild.text_channels, name="🟡・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ")
        or discord.utils.get(guild.text_channels, name="🔴・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ")
        or discord.utils.get(guild.text_channels, name="status-cheats")
        or next((c for c in guild.text_channels if "status" in c.name.lower()), None)
    )

    if not ch:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False, add_reactions=False, view_channel=True),
            guild.me: discord.PermissionOverwrite(send_messages=True, embed_links=True, view_channel=True),
        }
        ch = await guild.create_text_channel(target_channel_name, overwrites=overwrites, reason="Status Board")

    # Rename channel if prefix changed
    if ch.name != target_channel_name:
        try:
            await ch.edit(name=target_channel_name)
        except Exception:
            pass

    embed = build_status_embed(data)
    edited = False

    # Search existing status message sent by bot
    async for msg in ch.history(limit=15):
        if msg.author.id == bot_user.id and msg.embeds:
            await msg.edit(embed=embed)
            edited = True
            break

    if not edited:
        await ch.send(embed=embed)

    return True, f"Tableau de bord mis à jour dans {ch.mention} ({target_prefix}) !"


class StatusSelect(discord.ui.Select):
    def __init__(self, product_key: str, product_name: str) -> None:
        self.product_key = product_key
        options = [
            discord.SelectOption(label="UNDETECTED (Operational)", value="UNDETECTED", emoji="🟢", description="100% Safe to play"),
            discord.SelectOption(label="UPDATING (Testing / Patching)", value="UPDATING", emoji="🟡", description="Wait for update"),
            discord.SelectOption(label="OFFLINE (Maintenance)", value="OFFLINE", emoji="🔴", description="Do NOT use"),
        ]
        super().__init__(
            placeholder=f"Changer le statut de {product_name}...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        new_status = self.values[0]
        data = load_status_data()

        if self.product_key in data:
            data[self.product_key]["status"] = new_status
            save_status_data(data)

        if interaction.guild and interaction.client.user:
            await update_status_message_and_channel(interaction.guild, interaction.client.user, data)

        await interaction.followup.send(
            f"✅ **{data.get(self.product_key, {}).get('name', self.product_key)}** est désormais en **`{new_status}`** !",
            ephemeral=True,
        )


class StatusPanelControlView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        data = load_status_data()
        for key in ("spectre", "mcore", "perm_spoofer", "temp_spoofer"):
            if key in data:
                self.add_item(StatusSelect(key, data[key]["name"].split()[0]))


class StatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup_status_channel", description="Create or setup the official live status channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_status_cmd(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not self.bot.user:
            return
        await interaction.response.defer(ephemeral=True)
        data = load_status_data()
        ok, msg = await update_status_message_and_channel(interaction.guild, self.bot.user, data)
        await interaction.followup.send(f"{'✅' if ok else '⚠️'} {msg}", ephemeral=True)

    @app_commands.command(name="status_panel", description="Open interactive 1-click status management panel")
    @app_commands.default_permissions(administrator=True)
    async def status_panel_cmd(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="⚙️  PANNEAU D'ADMINISTRATION DU STATUT DES CHEATS",
            description=(
                "> **Sélectionnez un logiciel dans les menus déroulants ci-dessous pour changer son statut en direct.**\n"
                "> Le tableau de bord et le salon **`#status-cheats`** seront mis à jour instantanément."
            ),
            color=discord.Color.from_str("#0070FF"),
        )
        await interaction.response.send_message(embed=embed, view=StatusPanelControlView(), ephemeral=True)

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
        if not interaction.guild or not self.bot.user:
            return
        await interaction.response.defer(ephemeral=True)
        data = load_status_data()

        if product not in data:
            data[product] = {"name": product.upper(), "status": status, "notes": ""}

        data[product]["status"] = status
        if custom_notes:
            data[product]["notes"] = custom_notes
        save_status_data(data)

        # Update Discord live embed & channel name
        ok, msg = await update_status_message_and_channel(interaction.guild, self.bot.user, data)
        await interaction.followup.send(
            f"✅ Statut mis à jour : **{data[product]['name']}** ➔ **`{status}`** !\n{msg}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatusCog(bot))
