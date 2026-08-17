import json
import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands
from cogs.translator import TranslateButtonView

log = logging.getLogger("cogs.ai_builder")

PRESET_TEMPLATES: dict[str, dict[str, Any]] = {
    "status": {
        "channel_name": "🟢・ꜱᴛᴀᴛᴜꜱ-ᴄʜᴇᴀᴛꜱ",
        "title": "🟢  CORE MARKET — LIVE CHEAT & SPOOFER STATUS",
        "description": (
            "> **Official real-time operational status for all Core Market software.**\n"
            "> *Updates automatically when anti-cheat patches or maintenance occurs.*\n\n"
            "```ansi\n"
            "\u001b[1;32m[ 🛡️ LIVE SOFTWARE & SPOOFER STATUS ]\u001b[0m\n"
            "```\n"
            "🟢 **TRINITY SPECTRE (BO7 / WZ)** ➔ ` UNDETECTED `\n"
            "   └─ *External Ring-0 • Streamproof • Safe*\n"
            "🟢 **M-CORE EXTERNAL** ➔ ` UNDETECTED `\n"
            "   └─ *Kernel Overlay • ESP & Aim • Safe*\n"
            "🟢 **PERMANENT HWID SPOOFER** ➔ ` UNDETECTED `\n"
            "   └─ *Motherboard / Disk / NIC Spoofed • Safe*\n"
            "🟢 **TEMPORARY SPOOFER** ➔ ` UNDETECTED `\n"
            "   └─ *Instant Spoof Session • Safe*\n"
            "🟢 **RICOCHET ANTI-CHEAT BYPASS** ➔ ` OPERATIONAL `\n"
            "   └─ *Hypervisor / Ring-0 Guard Active*\n\n"
            "```ansi\n"
            "\u001b[1;36m[ ⚡ QUICK ACCESS ]\u001b[0m\n"
            "```\n"
            "▸ **Claim Free Trial (1H) :** <#🎁・free-trial>\n"
            "▸ **Open Support Ticket :** <#🎫・creer-un-ticket>"
        ),
        "color": "#00FF66",
        "with_translate": True,
    },
    "announcements": {
        "channel_name": "📢・announcements",
        "title": "📢  CORE MARKET — OFFICIAL ANNOUNCEMENTS",
        "description": (
            "> **Welcome to the official Core Market announcement channel!**\n"
            "> Here you will find all software updates, discounts, and maintenance alerts.\n\n"
            "```ansi\n"
            "\u001b[1;33m[ ⚡ STAY UPDATED ]\u001b[0m\n"
            "```\n"
            "▸ Turn on server notifications to never miss a giveaway or flash sale.\n"
            "▸ Click the **`Auto-Translate`** button below any announcement to read in your language!"
        ),
        "color": "#0070FF",
        "with_translate": True,
    },
    "rules": {
        "channel_name": "📜・rules",
        "title": "📜  CORE MARKET — SERVER RULES & GUIDELINES",
        "description": (
            "> **Please read and respect the community rules before interacting.**\n\n"
            "```ansi\n"
            "\u001b[1;31m[ ⚖️ COMMUNITY GUIDELINES ]\u001b[0m\n"
            "```\n"
            "**` 1 ` Respect Staff & Members :** Toxicity, harassment, or racism will lead to an immediate ban.\n"
            "**` 2 ` No Advertising or Self-Promotion :** DM advertising or sending invite links is strictly forbidden.\n"
            "**` 3 ` Support via Tickets Only :** Do not mention staff in public channels for orders or support.\n"
            "**` 4 ` Scam Protection :** Staff will NEVER DM you first to ask for your password or payment.\n\n"
            "──────────────────────────────────────────\n"
            "✅ *Click the button below to accept the rules and unlock the server!*"
        ),
        "color": "#0070FF",
        "with_translate": True,
    },
    "faq": {
        "channel_name": "❓・faq-guide",
        "title": "❓  CORE MARKET — FAQ & PREREQUISITES GUIDE",
        "description": (
            "> **Find answers to the most common questions before launching your software.**\n\n"
            "```ansi\n"
            "\u001b[1;36m[ ⚙️ SYSTEM PREREQUISITES ]\u001b[0m\n"
            "```\n"
            "▸ **Virtualization (BIOS) :** Must be ENABLED (SVM Mode for AMD / Intel VT-x).\n"
            "▸ **Windows Security :** Add a folder exclusion on your Loader directory.\n"
            "▸ **Rival Anti-Cheats :** Close Vanguard (Valorant) and FaceIt before injection.\n\n"
            "```ansi\n"
            "\u001b[1;33m[ 📥 USEFUL LINKS ]\u001b[0m\n"
            "```\n"
            "▸ **GitBook Setup Guide :** https://trinityshop.gitbook.io/untitled/etapes-obligatoire/1.-virtualisation\n"
            "▸ **Download Loader (Mega) :** https://mega.nz/folder/w7VjQS6I#wav1HBID04Hj9w-N_2CVaQ"
        ),
        "color": "#0070FF",
        "with_translate": True,
    },
    "pricing": {
        "channel_name": "💳・pricing-tarifs",
        "title": "💳  CORE MARKET — OFFICIAL PRICING & PRODUCTS",
        "description": (
            "> **Undetected, Streamproof & Kernel-Level Solutions for Call of Duty.**\n\n"
            "```ansi\n"
            "\u001b[1;32m[ 🎯 M-CORE EXTERNAL (BO7 / WARZONE) ]\u001b[0m\n"
            "```\n"
            "▸ 24 Hours : **`5.99 €`**\n"
            "▸ 1 Week : **`15.99 €`**\n"
            "▸ 30 Days : **`35.99 €`**\n\n"
            "```ansi\n"
            "\u001b[1;35m[ 🔮 TRINITY SPECTRE (BO7 / WARZONE) ]\u001b[0m\n"
            "```\n"
            "▸ 24 Hours : **`7.99 €`**\n"
            "▸ 1 Week : **`21.99 €`**\n"
            "▸ 30 Days : **`44.99 €`**\n"
            "▸ Lifetime : **`119.99 €`**\n\n"
            "──────────────────────────────────────────\n"
            "💳 **Accepted Payments :** Credit Card, Crypto (BTC/LTC/USDT), PayPal, CashApp, Paysafecard.\n"
            "👉 **To purchase :** Open a ticket in <#🎫・creer-un-ticket> !"
        ),
        "color": "#0070FF",
        "with_translate": True,
    },
}


class CustomEmbedModal(discord.ui.Modal, title="🎨 Create Custom AI Embed"):
    embed_title = discord.ui.TextInput(
        label="Embed Title",
        placeholder="e.g. FLASH SALE -20% THIS WEEKEND",
        required=True,
        max_length=100,
    )
    embed_content = discord.ui.TextInput(
        label="Description / Body Content",
        placeholder="Write your formatted text or announcement here...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=3000,
    )
    embed_color = discord.ui.TextInput(
        label="Color Hex (Optional, e.g. #0070FF, #00FF66)",
        placeholder="#0070FF",
        required=False,
        max_length=10,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        color_str = str(self.embed_color).strip() or "#0070FF"
        try:
            color = discord.Color.from_str(color_str)
        except Exception:
            color = discord.Color.from_str("#0070FF")

        embed = discord.Embed(
            title=f"✨  {str(self.embed_title).upper()}",
            description=str(self.embed_content).replace("\\n", "\n"),
            color=color,
        )
        embed.set_footer(text="CORE MARKET • Official Embed • 1-Click Translation")

        await interaction.channel.send(embed=embed, view=TranslateButtonView())
        await interaction.response.send_message("✅ Embed published with 1-click translation buttons!", ephemeral=True)


class AIBuilderCog(commands.Cog):
    """Smart Channel & Embed Architect for Core Market."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ai_create_channel", description="Instantly create and format a professional channel with sleek embeds")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(
        template=[
            app_commands.Choice(name="🟢 Live Cheat & Spoofer Status (Tableau de bord)", value="status"),
            app_commands.Choice(name="📢 Official Announcements (avec Traducteur)", value="announcements"),
            app_commands.Choice(name="📜 Server Rules & Guidelines (Règlement)", value="rules"),
            app_commands.Choice(name="❓ FAQ & Installation Prerequisites (Guide)", value="faq"),
            app_commands.Choice(name="💳 Official Pricing & Plans (Tarifs)", value="pricing"),
        ],
    )
    async def create_channel_cmd(self, interaction: discord.Interaction, template: str) -> None:
        guild = interaction.guild
        if not guild:
            return

        await interaction.response.defer(ephemeral=True)
        tmpl = PRESET_TEMPLATES.get(template)
        if not tmpl:
            await interaction.followup.send("⚠️ Unknown template.", ephemeral=True)
            return

        channel_name = tmpl["channel_name"]

        # Check existing channel or create new
        ch = discord.utils.get(guild.text_channels, name=channel_name)
        if not ch:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(send_messages=False, add_reactions=False, view_channel=True),
                guild.me: discord.PermissionOverwrite(send_messages=True, embed_links=True, view_channel=True),
            }
            ch = await guild.create_text_channel(channel_name, overwrites=overwrites, reason="AI Builder Channel")

        embed = discord.Embed(
            title=tmpl["title"],
            description=tmpl["description"],
            color=discord.Color.from_str(tmpl["color"]),
        )
        embed.set_footer(text="CORE MARKET • Automated System • 1-Click Translation available")

        view = TranslateButtonView() if tmpl.get("with_translate") else None
        await ch.send(embed=embed, view=view)

        await interaction.followup.send(
            f"✅ Salon **{ch.mention}** créé et configuré avec succès avec son embed professionnel !",
            ephemeral=True,
        )

    @app_commands.command(name="ai_custom_embed", description="Open modal to create a custom styled embed with translation")
    @app_commands.default_permissions(administrator=True)
    async def custom_embed_cmd(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(CustomEmbedModal())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AIBuilderCog(bot))
