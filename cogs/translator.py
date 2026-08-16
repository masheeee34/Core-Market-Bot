import logging
import urllib.parse
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("cogs.translator")

LANG_OPTIONS: list[dict[str, str]] = [
    {"label": "English", "value": "en", "emoji": "🇬🇧", "description": "Translate to English"},
    {"label": "Français", "value": "fr", "emoji": "🇫🇷", "description": "Traduire en Français"},
    {"label": "Español", "value": "es", "emoji": "🇪🇸", "description": "Traducir al Español"},
    {"label": "Deutsch", "value": "de", "emoji": "🇩🇪", "description": "Auf Deutsch übersetzen"},
    {"label": "한국어 (Korean)", "value": "ko", "emoji": "🇰🇷", "description": "한국어로 번역"},
    {"label": "العربية (Arabic)", "value": "ar", "emoji": "🇸🇦", "description": "ترجمة إلى العربية"},
    {"label": "中文 (Chinese)", "value": "zh-CN", "emoji": "🇨🇳", "description": "翻译为中文"},
    {"label": "日本語 (Japanese)", "value": "ja", "emoji": "🇯🇵", "description": "日本語に翻訳"},
    {"label": "Português", "value": "pt", "emoji": "🇧🇷", "description": "Traduzir para Português"},
    {"label": "Русский", "value": "ru", "emoji": "🇷🇺", "description": "Перевести на Русский"},
]


async def translate_text(text: str, target_lang: str) -> str:
    """Translates text asynchronously using Google Translate engine (0 API key needed)."""
    if not text.strip():
        return ""
    lang_code = target_lang.split("-")[0] if "-" in target_lang and target_lang not in ("zh-CN", "zh-TW") else target_lang
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang_code}&dt=t&q={urllib.parse.quote(text)}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return "".join([part[0] for part in data[0] if part and part[0]])
    except Exception as e:
        log.error("Translation error: %s", e)
    return text


def extract_message_text(message: discord.Message) -> str:
    source_text = message.content or ""
    embed_title = ""
    embed_desc = ""
    if message.embeds:
        emb = message.embeds[0]
        embed_title = emb.title or ""
        embed_desc = emb.description or ""
    return source_text or f"{embed_title}\n\n{embed_desc}".strip()


class LanguageSelectDropdown(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label=opt["label"],
                value=opt["value"],
                emoji=opt["emoji"],
                description=opt["description"],
            )
            for opt in LANG_OPTIONS
        ]
        super().__init__(
            placeholder="🌐 Select a Language to Translate...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="translate_select_dropdown",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        target_lang = self.values[0]
        message = interaction.message
        if not message:
            return

        text = extract_message_text(message)
        if not text:
            await interaction.followup.send("⚠️ No translatable text found in this message.", ephemeral=True)
            return

        translated = await translate_text(text, target_lang)
        embed = discord.Embed(
            title=f"🌐  TRANSLATION ({target_lang.upper()})",
            description=translated,
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text="CORE MARKET • 1-Click Translation Engine")
        await interaction.followup.send(embed=embed, ephemeral=True)


class TranslateButtonView(discord.ui.View):
    """Persistent 1-click translation view with auto-detect button and dropdown."""

    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(LanguageSelectDropdown())

    @discord.ui.button(
        label="Auto-Translate (1-Click)",
        emoji="🌐",
        style=discord.ButtonStyle.secondary,
        custom_id="translate_btn_auto",
    )
    async def auto_translate(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        user_locale = str(interaction.locale) or "en"
        target_lang = user_locale.split("-")[0] if "-" in user_locale and user_locale not in ("zh-CN", "zh-TW") else user_locale

        message = interaction.message
        if not message:
            return

        text = extract_message_text(message)
        if not text:
            await interaction.followup.send("⚠️ No translatable text found in this message.", ephemeral=True)
            return

        translated = await translate_text(text, target_lang)
        embed = discord.Embed(
            title=f"🌐  TRANSLATION ({user_locale.upper()})",
            description=f"> **Translated to your Discord language :**\n\n{translated}",
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text=f"CORE MARKET • Auto-detected Discord client language ({user_locale})")
        await interaction.followup.send(embed=embed, ephemeral=True)


class TranslatorCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="🌍 Translate Message",
            callback=self.translate_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def translate_context_menu(self, interaction: discord.Interaction, message: discord.Message) -> None:
        await interaction.response.defer(ephemeral=True)
        user_locale = str(interaction.locale) or "en"
        target_lang = user_locale.split("-")[0] if "-" in user_locale and user_locale not in ("zh-CN", "zh-TW") else user_locale

        full_text = extract_message_text(message)
        if not full_text:
            await interaction.followup.send("⚠️ No translatable text found in this message.", ephemeral=True)
            return

        translated = await translate_text(full_text, target_lang)
        embed = discord.Embed(
            title=f"🌍  TRANSLATION ({target_lang.upper()})",
            description=f"> **Original Author :** {message.author.mention}\n\n{translated}",
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text=f"CORE MARKET • Auto-translated to your Discord language ({user_locale})")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="announce", description="Post an official announcement with 1-click translation buttons")
    @app_commands.default_permissions(administrator=True)
    async def announce_cmd(self, interaction: discord.Interaction, title: str, content: str) -> None:
        embed = discord.Embed(
            title=f"📢  {title.upper()}",
            description=content.replace("\\n", "\n"),
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text="CORE MARKET • Official Announcement • Use button below to translate")
        await interaction.channel.send(embed=embed, view=TranslateButtonView())
        await interaction.response.send_message("✅ Announcement posted with 1-click translation buttons!", ephemeral=True)

    @app_commands.command(name="add_translate_button", description="Add translation buttons under an existing message")
    @app_commands.default_permissions(administrator=True)
    async def add_btn_cmd(self, interaction: discord.Interaction, message_id: str) -> None:
        try:
            msg = await interaction.channel.fetch_message(int(message_id))
            await msg.edit(view=TranslateButtonView())
            await interaction.response.send_message("✅ 1-Click Translation buttons attached to message!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error attaching view: {e}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TranslatorCog(bot))
    bot.add_view(TranslateButtonView())
