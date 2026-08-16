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
    """Extracts all text from message content, embed titles, descriptions, fields, and footers."""
    # If the message is an auto-reply or button bar, look at the referenced message
    if message.reference and message.reference.resolved and isinstance(message.reference.resolved, discord.Message):
        message = message.reference.resolved

    parts: list[str] = []
    if message.content and message.content.strip():
        parts.append(message.content.strip())

    for emb in message.embeds:
        if emb.title:
            parts.append(f"**{emb.title}**")
        if emb.description:
            parts.append(emb.description)
        for field in emb.fields:
            parts.append(f"**{field.name}**\n{field.value}")
        if emb.footer and emb.footer.text:
            parts.append(f"*{emb.footer.text}*")

    full = "\n\n".join(parts).strip()
    return full[:3800] if len(full) > 3800 else full


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


class AnnounceModal(discord.ui.Modal, title="📢 Create Official Announcement"):
    title_input = discord.ui.TextInput(
        label="Announcement Title",
        placeholder="e.g. SPECIAL VOUCH GIVEAWAY & BO7 UPDATE",
        required=True,
        max_length=100,
    )
    content_input = discord.ui.TextInput(
        label="Content / Announcement Text",
        placeholder="Write your announcement details here...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000,
    )
    ping_input = discord.ui.TextInput(
        label="Mention (Optional: @everyone / @here)",
        placeholder="e.g. @everyone",
        required=False,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title=f"📢  {str(self.title_input).upper()}",
            description=str(self.content_input),
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text="CORE MARKET • Official Announcement • 1-Click Translation available below")

        ping_text = str(self.ping_input).strip()
        mention_content = f"{ping_text}\n" if ping_text in ("@everyone", "@here") else None

        await interaction.channel.send(content=mention_content, embed=embed, view=TranslateButtonView())
        await interaction.response.send_message("✅ Announcement published with 1-click translation buttons!", ephemeral=True)


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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Automatically adds translation buttons whenever staff posts in an announcement channel."""
        if message.author.bot or not message.guild:
            return

        channel_name = message.channel.name.lower()
        if any(w in channel_name for w in ("announc", "annonc", "news", "update")):
            try:
                await message.reply(
                    content="🌐 **Translate this announcement / Traduire cette annonce :**",
                    view=TranslateButtonView(),
                    mention_author=False,
                )
            except Exception as e:
                log.debug("Auto translate reply error: %s", e)

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

    @app_commands.command(name="announce", description="Open announcement creator with 1-click translation buttons")
    @app_commands.default_permissions(administrator=True)
    async def announce_cmd(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(AnnounceModal())

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
