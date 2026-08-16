import logging
import urllib.parse
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("cogs.translator")

FLAG_TO_LANG: dict[str, tuple[str, str]] = {
    "🇬🇧": ("en", "English"),
    "🇺🇸": ("en", "English"),
    "🇫🇷": ("fr", "Français"),
    "🇪🇸": ("es", "Español"),
    "🇩🇪": ("de", "Deutsch"),
    "🇰🇷": ("ko", "한국어 (Korean)"),
    "🇸🇦": ("ar", "العربية (Arabic)"),
    "🇨🇳": ("zh-CN", "中文 (Chinese)"),
    "🇯🇵": ("ja", "日本語 (Japanese)"),
    "🇧🇷": ("pt", "Português"),
    "🇷🇺": ("ru", "Русский"),
    "🇮🇹": ("it", "Italiano"),
    "🇹🇷": ("tr", "Türkçe"),
}


async def translate_text(text: str, target_lang: str) -> str:
    """Translates text asynchronously using Google Translate engine (0 API key needed)."""
    if not text.strip():
        return ""
    # Extract language code prefix (e.g. 'es-ES' -> 'es', 'zh-CN' -> 'zh-CN')
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


class TranslatorCog(commands.Cog):
    """Universal instant translation engine via Context Menu Apps and Flag reactions."""

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
        """Context menu action: Right-click any message -> Apps -> Translate Message."""
        await interaction.response.defer(ephemeral=True)

        user_locale = str(interaction.locale) or "en"
        target_lang = user_locale.split("-")[0] if "-" in user_locale and user_locale not in ("zh-CN", "zh-TW") else user_locale

        # Extract text from message content or embed
        source_text = message.content or ""
        embed_title = ""
        embed_desc = ""

        if message.embeds:
            first_embed = message.embeds[0]
            embed_title = first_embed.title or ""
            embed_desc = first_embed.description or ""

        full_text = source_text or f"{embed_title}\n\n{embed_desc}".strip()
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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Translates message into target language when reacting with country flag."""
        emoji_str = str(payload.emoji)
        if emoji_str not in FLAG_TO_LANG:
            return

        guild = self.bot.get_guild(payload.guild_id) if payload.guild_id else None
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
            user = guild.get_member(payload.user_id) or await self.bot.fetch_user(payload.user_id)
            if not user or user.bot:
                return

            target_code, lang_name = FLAG_TO_LANG[emoji_str]
            raw_text = message.content or ""
            if not raw_text and message.embeds:
                emb = message.embeds[0]
                raw_text = f"{emb.title or ''}\n\n{emb.description or ''}".strip()

            if not raw_text:
                return

            translated = await translate_text(raw_text, target_code)

            embed = discord.Embed(
                title=f"{emoji_str}  TRANSLATION — {lang_name.upper()}",
                description=f"> **From :** {channel.mention} • **Author :** {message.author.mention}\n\n{translated}",
                color=discord.Color.from_str("#0070FF"),
            )
            embed.set_footer(text="CORE MARKET • Instant Flag Translator")
            await user.send(embed=embed)
        except Exception as e:
            log.debug("Flag translation DM failed: %s", e)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TranslatorCog(bot))
