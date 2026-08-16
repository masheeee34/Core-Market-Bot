import json
import logging
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("cogs.invites")
INVITES_FILE = Path("data/invites.json")


def load_invites_data() -> dict[str, Any]:
    if not INVITES_FILE.exists():
        return {}
    try:
        with open(INVITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_invites_data(data: dict[str, Any]) -> None:
    INVITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INVITES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_user_valid_invites(guild_id: int, user_id: int) -> int:
    """Returns the total number of currently active/valid invites for a user."""
    data = load_invites_data()
    g_data = data.get(str(guild_id), {})
    u_data = g_data.get(str(user_id), {})
    joins = len(u_data.get("joins", []))
    leaves = len(u_data.get("leaves", []))
    return max(0, joins - leaves)


class InvitesCog(commands.Cog):
    """Tracks invite links to power weighted giveaway tickets, notifications, and referrals."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._invite_cache: dict[int, dict[str, int]] = {}

    async def _cache_guild_invites(self, guild: discord.Guild) -> None:
        try:
            invites = await guild.invites()
            self._invite_cache[guild.id] = {inv.code: inv.uses or 0 for inv in invites}
        except discord.Forbidden:
            log.warning("Bot lacks 'Manage Server' permission to fetch invites in %s", guild.name)
        except Exception as e:
            log.error("Error caching invites for %s: %s", guild.name, e)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            await self._cache_guild_invites(guild)
        log.info("Invite caches initialized for %d guilds.", len(self._invite_cache))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        guild = member.guild
        old_cache = self._invite_cache.get(guild.id, {})

        try:
            current_invites = await guild.invites()
        except Exception:
            return

        inviter: discord.Member | discord.User | None = None
        used_code: str | None = None

        for inv in current_invites:
            old_uses = old_cache.get(inv.code, 0)
            if (inv.uses or 0) > old_uses:
                inviter = inv.inviter
                used_code = inv.code
                break

        # Update cache
        self._invite_cache[guild.id] = {inv.code: inv.uses or 0 for inv in current_invites}

        if inviter and inviter.id != member.id:
            data = load_invites_data()
            g_data = data.setdefault(str(guild.id), {})
            u_data = g_data.setdefault(str(inviter.id), {"joins": [], "leaves": []})

            if member.id not in u_data["joins"]:
                u_data["joins"].append(member.id)
                save_invites_data(data)

            total_valid = max(0, len(u_data["joins"]) - len(u_data.get("leaves", [])))

            # 1. Staff Logs Notification
            log_ch = discord.utils.get(guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ") or discord.utils.get(
                guild.text_channels, name="📜・logs-tickets"
            ) or next((ch for ch in guild.text_channels if "log" in ch.name.lower()), None)

            if log_ch:
                embed_log = discord.Embed(
                    title="🔗  NEW REFERRAL JOINED",
                    description=(
                        f"▸ **New Member :** {member.mention} (`{member.id}`)\n"
                        f"▸ **Invited By :** {inviter.mention} (`{inviter.id}`)\n"
                        f"▸ **Invite Code :** `discord.gg/{used_code}`\n"
                        f"▸ **Inviter Total Invites :** **`{total_valid}`**\n"
                        f"▸ **Giveaway Tickets :** **`{total_valid + 1}`**"
                    ),
                    color=discord.Color.green(),
                )
                embed_log.set_footer(text="CORE MARKET • Referral Tracker")
                await log_ch.send(embed=embed_log)

            # 2. Direct DM Notification to the Inviter
            try:
                embed_dm = discord.Embed(
                    title="🎉  NEW MEMBER JOINED WITH YOUR LINK!",
                    description=(
                        f"Hey {inviter.mention}! **{member.name}** just joined Core Market using your invite link!\n\n"
                        f"▸ **Your Valid Active Invites :** **`{total_valid}`**\n"
                        f"▸ **Your Giveaway Bonus :** **`+{total_valid} Extra Tickets`** on all active giveaways!\n\n"
                        "🚀 *Keep sharing your link to maximize your chances of winning!*"
                    ),
                    color=discord.Color.from_str("#0070FF"),
                )
                embed_dm.set_footer(text="CORE MARKET • Invite Rewards")
                await inviter.send(embed=embed_dm)
            except Exception as e:
                log.warning("Could not send DM to inviter %s: %s", inviter, e)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        guild = member.guild
        data = load_invites_data()
        g_data = data.get(str(guild.id), {})

        for inviter_id_str, u_data in g_data.items():
            if member.id in u_data.get("joins", []):
                if member.id not in u_data.setdefault("leaves", []):
                    u_data["leaves"].append(member.id)
                    save_invites_data(data)
                    log.info("Member left: %s (Inviter: %s)", member, inviter_id_str)
                break

    @app_commands.command(name="invites", description="Check your or another member's valid invite count")
    async def check_invites(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        valid = get_user_valid_invites(interaction.guild_id or 0, target.id)

        embed = discord.Embed(
            title="🔗  INVITE TRACKER STATS",
            description=(
                f"▸ **Member :** {target.mention}\n"
                f"▸ **Valid Active Invites :** **`{valid}`**\n"
                f"▸ **Giveaway Tickets Bonus :** **`+{valid} Extra Ticket(s)`**\n\n"
                "💡 *Every valid invite grants you +1 additional ticket on all giveaways!*"
            ),
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text="CORE MARKET • Referral System")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="invites_leaderboard", description="Display the top inviters on the server")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id or 0
        data = load_invites_data().get(str(guild_id), {})

        scores = []
        for uid_str, u_data in data.items():
            valid = max(0, len(u_data.get("joins", [])) - len(u_data.get("leaves", [])))
            if valid > 0:
                scores.append((int(uid_str), valid))

        scores.sort(key=lambda x: x[1], reverse=True)
        top10 = scores[:10]

        if not top10:
            await interaction.response.send_message("ℹ️ No invites recorded yet.", ephemeral=True)
            return

        lines = [f"`#{i+1}` <@{uid}> — **{pts} invites** (`+{pts} giveaway tickets`)" for i, (uid, pts) in enumerate(top10)]

        embed = discord.Embed(
            title="🏆  TOP INVITERS LEADERBOARD",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="CORE MARKET • Referral Leaderboard")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="test_invite_notif", description="Simulate a member join notification for testing")
    @app_commands.default_permissions(administrator=True)
    async def test_invite_cmd(self, interaction: discord.Interaction, inviter: discord.Member | None = None) -> None:
        target = inviter or interaction.user
        guild = interaction.guild
        if not guild:
            return

        # 1. Staff Logs
        log_ch = discord.utils.get(guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ") or discord.utils.get(
            guild.text_channels, name="📜・logs-tickets"
        ) or next((ch for ch in guild.text_channels if "log" in ch.name.lower()), interaction.channel)

        if log_ch and isinstance(log_ch, discord.TextChannel):
            embed_log = discord.Embed(
                title="🔗  [TEST] NEW REFERRAL JOINED",
                description=(
                    f"▸ **New Member :** {interaction.user.mention}\n"
                    f"▸ **Invited By :** {target.mention}\n"
                    f"▸ **Invite Code :** `discord.gg/test-link`\n"
                    f"▸ **Inviter Total Invites :** `5`\n"
                    f"▸ **Giveaway Tickets :** `6 Tickets`"
                ),
                color=discord.Color.green(),
            )
            embed_log.set_footer(text="CORE MARKET • Referral Tracker (Test Simulation)")
            await log_ch.send(embed=embed_log)

        # 2. DM
        try:
            embed_dm = discord.Embed(
                title="🎉  [TEST] NEW MEMBER JOINED WITH YOUR LINK!",
                description=(
                    f"Hey {target.mention}! A new member just joined Core Market using your invite link!\n\n"
                    f"▸ **Your Valid Active Invites :** `5`\n"
                    f"▸ **Your Giveaway Bonus :** `+5 Extra Tickets` on all active giveaways!\n\n"
                    "🚀 *Keep sharing your link to maximize your chances of winning!*"
                ),
                color=discord.Color.from_str("#0070FF"),
            )
            embed_dm.set_footer(text="CORE MARKET • Invite Rewards (Test Simulation)")
            await target.send(embed=embed_dm)
            dm_status = "✅ DM envoyé avec succès !"
        except Exception as e:
            dm_status = f"⚠️ Impossible d'envoyer le DM (DMs fermés par l'utilisateur) : {e}"

        await interaction.response.send_message(
            f"✅ Test exécuté ! Log envoyé dans {getattr(log_ch, 'mention', '#logs')} • {dm_status}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InvitesCog(bot))
