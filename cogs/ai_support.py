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


ACTIVITIES: list[tuple[discord.ActivityType, str]] = [
    (discord.ActivityType.playing, "🎮 BO7 & Warzone External (Ring-0)"),
    (discord.ActivityType.listening, "🎧 24/7 Voice Support • DM me for help!"),
    (discord.ActivityType.watching, "🛡️ Ricochet Bypass | 100% Streamproof"),
    (discord.ActivityType.competing, "🎁 /giveaway • Weighted Odds"),
    (discord.ActivityType.playing, "🌐 1-Click Multi-Language Translation"),
    (discord.ActivityType.watching, "🎫 Core Market • Free Trial (1H)"),
]


class AISupportCog(commands.Cog):
    """24/7 Voice Support Desk & Intelligent AI DM Knowledge Assistant with Staff Live Feed."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._presence_index = 0
        self.voice_watchdog.start()
        self.rotating_presence.start()

    def cog_unload(self) -> None:
        self.voice_watchdog.cancel()
        self.rotating_presence.cancel()

    @tasks.loop(seconds=30)
    async def rotating_presence(self) -> None:
        """Dynamically rotates the bot's rich presence activity and custom status."""
        try:
            act_type, act_name = ACTIVITIES[self._presence_index % len(ACTIVITIES)]
            self._presence_index += 1
            await self.bot.change_presence(
                activity=discord.Activity(type=act_type, name=act_name),
                status=discord.Status.online,
            )
        except Exception as e:
            log.debug("Presence update error: %s", e)

    @rotating_presence.before_loop
    async def before_rotating_presence(self) -> None:
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=120)
    async def voice_watchdog(self) -> None:
        """Maintains 24/7 voice presence in '🎧・if you need help' across guilds."""
        for guild in self.bot.guilds:
            try:
                # Only attempt reconnect if completely disconnected
                voice_client = guild.voice_client
                if not voice_client or not voice_client.is_connected():
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
            log.info("Bot voice disconnected, scheduling auto-reconnect...")
            await asyncio.sleep(5)
            if member.guild:
                await self._ensure_voice_presence(member.guild)

    async def _ensure_voice_presence(self, guild: discord.Guild) -> tuple[bool, str]:
        # 1. Find or create voice channel
        vchannel = discord.utils.get(guild.voice_channels, name=VOICE_CHANNEL_NAME)
        if not vchannel:
            try:
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
            except Exception as e:
                return False, f"Impossible de créer le salon vocal : {e}"

        # Ensure explicit permissions for bot
        try:
            perms = vchannel.permissions_for(guild.me)
            if not perms.connect or not perms.view_channel:
                await vchannel.set_permissions(guild.me, connect=True, speak=True, view_channel=True)
        except Exception:
            pass

        # 2. Check and maintain active voice connection (micro mute only, no deafen)
        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            try:
                if voice_client:
                    try:
                        await voice_client.disconnect(force=True)
                    except Exception:
                        pass
                await vchannel.connect(reconnect=True, timeout=30.0, self_deaf=False, self_mute=True)
                log.info("Connected to 24/7 Voice Desk in %s", guild.name)
                return True, f"Connecté avec succès à {vchannel.name} !"
            except Exception as e:
                log.warning("Could not connect to voice desk in %s: %s", guild.name, e)
                return False, f"Erreur de connexion vocale : {e}"
        elif voice_client.channel.id != vchannel.id:
            try:
                await voice_client.move_to(vchannel)
                return True, f"Déplacé vers {vchannel.name} !"
            except Exception as e:
                return False, f"Erreur de déplacement : {e}"

        return True, f"Déjà connecté dans {vchannel.name}"

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

        # 1. Translate query to English for universal KB lookup & detect source language
        translated_en, detected_lang = await translate_text(query, target_lang="en")

        topics = load_knowledge_base()
        best_topic = find_best_topic(query, topics) or find_best_topic(translated_en, topics)

        is_french = detected_lang.startswith("fr") or any(
            w in query.lower() for w in ("bonjour", "salut", "comment", "prix", "aide", "merci", "cle", "est", "je")
        )

        GUIDE_URL = "https://trinityshop.gitbook.io/untitled/etapes-obligatoire/1.-virtualisation"
        LOADER_URL = "https://mega.nz/folder/w7VjQS6I#wav1HBID04Hj9w-N_2CVaQ"

        if best_topic:
            raw_answer = best_topic.get("response_fr" if is_french else "response_en", "")
            if not is_french and detected_lang not in ("en", "auto", ""):
                answer, _ = await translate_text(best_topic.get("response_en", raw_answer), target_lang=detected_lang)
            else:
                answer = raw_answer

            embed_reply = discord.Embed(
                title=f"🤖  CORE MARKET ASSISTANT — {best_topic['id'].replace('_', ' ').upper()}",
                description=answer,
                color=discord.Color.from_str("#0070FF"),
            )
        else:
            if is_french:
                description = (
                    f"> **Bonjour {user.name} ! Bienvenue sur l'assistance Core Market.**\n"
                    "> Je suis l'assistant intelligent. Posez-moi votre question ou consultez les sujets ci-dessous :\n\n"
                    "```ansi\n"
                    "\u001b[1;33m[ 💡 QUESTIONS FRÉQUENTES RECONNUES ]\u001b[0m\n"
                    "```\n"
                    "▸ **🎁 Clé d'essai 1H :** Demandez *\"comment avoir la clé d'essai\"* ou allez dans <#🎁・free-trial>\n"
                    "▸ **⚙️ Virtualisation BIOS :** Demandez *\"comment activer SVM / VT-x\"*\n"
                    "▸ **📥 Téléchargement Loader :** Demandez *\"lien de téléchargement\"*\n"
                    "▸ **💳 Tarifs & Achat :** Demandez *\"les prix\"* pour M-Core et Trinity Spectre\n"
                    "▸ **🛡️ Streamproof & Sécurité :** Demandez *\"est-ce indétectable\"*\n\n"
                    "```ansi\n"
                    "\u001b[1;32m[ 🎫 SUPPORT HUMAIN & COMMANDES ]\u001b[0m\n"
                    "```\n"
                    "▸ Besoin d'aide personnalisée ? Ouvrez un ticket dans **<#🎫・creer-un-ticket>**."
                )
            else:
                base_desc = (
                    f"> **Hello {user.name}! Welcome to Core Market AI Helpdesk.**\n"
                    "> I am your automated assistant. Ask me anything or browse our popular topics:\n\n"
                    "```ansi\n"
                    "\u001b[1;33m[ 💡 POPULAR QUESTIONS YOU CAN ASK ]\u001b[0m\n"
                    "```\n"
                    "▸ **🎁 Free Trial 1H :** Ask *\"how to get free trial\"* or claim in <#🎁・free-trial>\n"
                    "▸ **⚙️ BIOS Setup :** Ask *\"how to enable SVM / VT-x virtualization\"*\n"
                    "▸ **📥 Download Loader :** Ask *\"download link\"* to get our official files\n"
                    "▸ **💳 Pricing & Buy :** Ask *\"pricing\"* for M-Core & Trinity Spectre keys\n"
                    "▸ **🛡️ Streamproof :** Ask *\"is it undetected / streamproof\"*\n\n"
                    "```ansi\n"
                    "\u001b[1;32m[ 🎫 HUMAN SUPPORT & ORDERS ]\u001b[0m\n"
                    "```\n"
                    "▸ Need dedicated human assistance? Open a ticket in **<#🎫・creer-un-ticket>**."
                )
                if detected_lang not in ("en", "auto", ""):
                    description, _ = await translate_text(base_desc, target_lang=detected_lang)
                else:
                    description = base_desc

            embed_reply = discord.Embed(
                title=f"🤖  CORE MARKET • 24/7 AI HELPDESK ({detected_lang.upper()})",
                description=description,
                color=discord.Color.from_str("#0070FF"),
            )

        embed_reply.set_footer(text="CORE MARKET • 24/7 Automated Client Support • Open a ticket for human staff")

        # Quick link buttons
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Setup Guide (GitBook)", url=GUIDE_URL, emoji="📖"))
        view.add_item(discord.ui.Button(label="Download Loader (Mega)", url=LOADER_URL, emoji="📥"))

        try:
            await user.send(embed=embed_reply, view=view)
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
        ok, msg = await self._ensure_voice_presence(interaction.guild)
        await interaction.followup.send(f"{'✅' if ok else '⚠️'} {msg}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AISupportCog(bot))
