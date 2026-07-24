"""Security cog — honeypot trap against compromised/hacked spam accounts.

Principle: a public channel named #do-not-post-or-get-banned that legitimate
members will never use. Hacked accounts spam every channel they can see — the
moment one posts there, it gets banned for 7 days and its recent messages are
purged server-wide.

No database: the unban date is encoded in the ban reason
("Honeypot trap | unban_at:<unix timestamp>"), and a background loop unbans
expired entries.
"""

import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.tickets import STAFF_ROLE_NAMES

TRAP_CHANNEL_NAME = "do-not-post-or-get-banned"
BAN_DAYS = 7
REASON_PREFIX = "Honeypot trap"

TRAP_EMBED_TITLE = "⚠️ DO NOT SEND ANY MESSAGES HERE"
TRAP_EMBED_DESCRIPTION = (
    "This channel is a security trap to catch compromised/hacked accounts.\n\n"
    "Hacked accounts often spam fake giveaway or scam links across every channel "
    "they can access.\n\n"
    "Any message sent here will result in an automatic 7-day ban.\n\n"
    "If you were banned from this channel, your account was likely hacked. "
    "Please change your password and enable 2FA."
)


def is_protected(member: discord.Member) -> bool:
    """Bots, admins et rôles staff ne déclenchent jamais le piège."""
    return (
        member.bot
        or member.guild_permissions.administrator
        or member.guild_permissions.manage_messages
        or any(r.name in STAFF_ROLE_NAMES for r in member.roles)
    )


class Security(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.unban_expired.start()

    async def cog_unload(self) -> None:
        self.unban_expired.cancel()

    # ------------------------------------------------------------------ setup
    @app_commands.command(
        name="setuptrap",
        description="Créer le salon honeypot anti-comptes hackés",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setuptrap(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        channel = discord.utils.get(guild.text_channels, name=TRAP_CHANNEL_NAME)
        if channel is None:
            # Tout le monde doit pouvoir écrire (c'est le piège) ; le bot doit
            # pouvoir supprimer/épingler.
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_messages=True
                ),
            }
            channel = await guild.create_text_channel(
                TRAP_CHANNEL_NAME, overwrites=overwrites, reason="/setuptrap — honeypot"
            )

        embed = discord.Embed(
            title=TRAP_EMBED_TITLE,
            description=TRAP_EMBED_DESCRIPTION,
            color=discord.Color.red(),
        )
        message = await channel.send(embed=embed)
        try:
            await message.pin(reason="Honeypot warning")
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            f"✅ Honeypot en place : {channel.mention} — tout message d'un non-staff "
            f"y déclenche un ban automatique de {BAN_DAYS} jours.",
            ephemeral=True,
        )

    # ------------------------------------------------------------------ piège
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or not isinstance(message.author, discord.Member):
            return
        if message.channel.name != TRAP_CHANNEL_NAME:
            return
        if is_protected(message.author):
            return

        member = message.author

        try:
            await message.delete()
        except discord.HTTPException:
            pass

        # Prévenir en DM AVANT le ban (impossible après).
        try:
            await member.send(
                f"You have been banned from **{message.guild.name}** for {BAN_DAYS} days: "
                f"you posted in the security trap channel.\n"
                f"Your account was likely hacked — please change your password and enable 2FA. "
                f"You will be automatically unbanned after {BAN_DAYS} days."
            )
        except discord.HTTPException:
            pass

        unban_at = discord.utils.utcnow() + datetime.timedelta(days=BAN_DAYS)
        try:
            await member.ban(
                reason=f"{REASON_PREFIX} | unban_at:{int(unban_at.timestamp())}",
                delete_message_seconds=7 * 24 * 3600,  # purge son spam des 7 derniers jours
            )
        except discord.Forbidden:
            # Le bot n'a pas la permission Ban Members ou le rôle est trop bas.
            try:
                await message.channel.send(
                    "⚠️ Trap triggered but I lack the **Ban Members** permission!",
                    delete_after=30,
                )
            except discord.HTTPException:
                pass

    # ------------------------------------------------------- unban automatique
    @tasks.loop(minutes=30)
    async def unban_expired(self) -> None:
        now = discord.utils.utcnow().timestamp()
        for guild in self.bot.guilds:
            try:
                async for entry in guild.bans(limit=None):
                    reason = entry.reason or ""
                    if not reason.startswith(REASON_PREFIX) or "unban_at:" not in reason:
                        continue
                    try:
                        expires = int(reason.split("unban_at:", 1)[1].split()[0])
                    except ValueError:
                        continue
                    if now >= expires:
                        await guild.unban(entry.user, reason="Honeypot 7-day ban expired")
            except discord.Forbidden:
                continue

    @unban_expired.before_loop
    async def before_unban_expired(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Security(bot))
