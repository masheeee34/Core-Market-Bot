import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks
from cogs.translator import translate_text

log = logging.getLogger("cogs.ai_support")
KB_FILE = Path("data/support_kb.json")
VOICE_CHANNEL_NAME = "🎧・if you need help"


def load_knowledge_base() -> list[dict[str, Any]]:
    if not KB_FILE.exists():
        return []
    try:
        with open(KB_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("topics", [])
    except Exception as e:
        log.error("Error loading knowledge base: %s", e)
        return []


def find_best_topic(query: str, topics: list[dict[str, Any]]) -> dict[str, Any] | None:
    query_tokens = set(re.findall(r"\w+", query.lower()))
    best_topic = None
    best_score = 0

    for topic in topics:
        keywords = set(topic.get("keywords", []))
        matches = query_tokens.intersection(keywords)
        score = len(matches)
        if score > best_score:
            best_score = score
            best_topic = topic

    return best_topic if best_score > 0 else None


class AISupportCog(commands.Cog):
    """24/7 Voice Support Desk & Intelligent AI DM Knowledge Assistant with Staff Live Feed."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.voice_watchdog.start()

    @tasks.loop(seconds=45)
    async def voice_watchdog(self) -> None:
        """Maintains 24/7 voice presence in '🎧・if you need help' across guilds."""
        for guild in self.bot.guilds:
            try:
                await self._ensure_voice_presence(guild)
            except Exception as e:
                log.debug("Voice watchdog check error on %s: %s", guild.name, e)

    @voice_watchdog.before_loop
    async def before_voice_watchdog(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            try:
                await self._ensure_voice_presence(guild)
            except Exception as e:
                log.debug("Initial voice connect error on %s: %s", guild.name, e)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Instantly reconnect if the bot gets disconnected from the support voice channel."""
        if member == self.bot.user and after.channel is None:
            await asyncio.sleep(2)
            if member.guild:
                await self._ensure_voice_presence(member.guild)

    async def _ensure_voice_presence(self, guild: discord.Guild) -> None:
        # 1. Find or create voice channel
        vchannel = discord.utils.get(guild.voice_channels, name=VOICE_CHANNEL_NAME)
        if not vchannel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
            }
            if guild.owner:
                overwrites[guild.owner] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True)
            vchannel = await guild.create_voice_channel(
                VOICE_CHANNEL_NAME,
                overwrites=overwrites,
                reason="24/7 Support Voice Desk",
            )
            log.info("Created 24/7 Support Voice Channel: %s", vchannel.name)

        # 2. Check and maintain active voice connection
        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            try:
                if voice_client:
                    await voice_client.disconnect(force=True)
                await vchannel.connect(reconnect=True, timeout=15.0, self_deaf=True)
                log.info("Connected to 24/7 Voice Desk in %s", guild.name)
            except Exception as e:
                log.warning("Could not connect to voice desk in %s: %s", guild.name, e)
        elif voice_client.channel != vchannel:
            try:
                await voice_client.move_to(vchannel)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """AI DM Support Engine: Answers questions in direct message & feeds live audit to staff."""
        if message.author.bot:
            return

        # Only process Direct Messages (DM)
        if not isinstance(message.channel, discord.DMChannel):
            return

        user = message.author
        query = message.content.strip()
        if not query:
            return

        topics = load_knowledge_base()
        best_topic = find_best_topic(query, topics)

        # Detect language / default to French or English
        is_french = any(w in query.lower() for w in ("bonjour", "salut", "comment", "prix", "aide", "merci", "cle", "est", "je"))

        if best_topic:
            answer = best_topic.get("response_fr" if is_french else "response_en", "")
        else:
            # Fallback to general support ticket invitation
            answer = (
                "🤖 **Core Market AI Assistant** :\n"
                "Merci pour votre message ! Pour obtenir une réponse personnalisée de notre équipe technique ou pour commander :\n\n"
                "👉 Ouvrez un ticket directement sur le serveur dans le salon **<#🎫・creer-un-ticket>** !"
                if is_french
                else (
                    "🤖 **Core Market AI Assistant** :\n"
                    "Thank you for your message! For personalized assistance or to place an order :\n\n"
                    "👉 Please open a support ticket on our server in **<#🎫・creer-un-ticket>**!"
                )
            )

        # Send DM response
        embed_reply = discord.Embed(
            title="🤖  CORE MARKET • AI SUPPORT ASSISTANT",
            description=answer,
            color=discord.Color.from_str("#0070FF"),
        )
        embed_reply.set_footer(text="CORE MARKET • 24/7 Automated Client Support • Open a ticket for human staff")
        try:
            await user.send(embed=embed_reply)
        except Exception as e:
            log.warning("Could not reply to DM from %s: %s", user, e)

        # 3. Staff Live Feed Notification in Guild Logs
        for guild in self.bot.guilds:
            log_ch = discord.utils.get(guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ") or discord.utils.get(
                guild.text_channels, name="📜・logs-tickets"
            ) or next((ch for ch in guild.text_channels if "log" in ch.name.lower()), None)

            if log_ch:
                embed_log = discord.Embed(
                    title="🤖  AI SUPPORT DM — LIVE CLIENT FEED",
                    description=(
                        f"▸ **Client :** {user.mention} (`{user.id}`)\n"
                        f"▸ **Detected Intent :** `{best_topic['id'] if best_topic else 'general_inquiry'}`\n\n"
                        "```ansi\n"
                        "\u001b[1;33m[ 💬 CLIENT QUESTION ]\u001b[0m\n"
                        "```\n"
                        f"{query[:1000]}\n\n"
                        "```ansi\n"
                        "\u001b[1;32m[ 🤖 AI BOT RESPONSE DELIVERED ]\u001b[0m\n"
                        "```\n"
                        f"{answer[:1000]}"
                    ),
                    color=discord.Color.from_str("#0070FF"),
                )
                if user.display_avatar:
                    embed_log.set_thumbnail(url=user.display_avatar.url)
                embed_log.set_footer(text="CORE MARKET • AI DM Interceptor • Live Staff Monitoring")
                try:
                    await log_ch.send(embed=embed_log)
                except Exception:
                    pass

    @app_commands.command(name="support_desk_reconnect", description="Force reconnect the bot to the 24/7 voice support desk")
    @app_commands.default_permissions(administrator=True)
    async def reconnect_voice_cmd(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        await interaction.response.defer(ephemeral=True)
        await self._ensure_voice_presence(interaction.guild)
        await interaction.followup.send("✅ Bot reconnected to 24/7 Voice Support Desk `🎧・if you need help`!", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AISupportCog(bot))
