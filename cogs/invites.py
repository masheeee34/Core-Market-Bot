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
    """Tracks invite links to power weighted giveaway tickets and referrals."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # In-memory cache: guild_id -> { invite_code: uses_count }
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

        inviter_id: int | None = None
        for inv in current_invites:
            old_uses = old_cache.get(inv.code, 0)
            if (inv.uses or 0) > old_uses and inv.inviter:
                inviter_id = inv.inviter.id
                break

        # Update cache
        self._invite_cache[guild.id] = {inv.code: inv.uses or 0 for inv in current_invites}

        if inviter_id and inviter_id != member.id:
            data = load_invites_data()
            g_data = data.setdefault(str(guild.id), {})
            u_data = g_data.setdefault(str(inviter_id), {"joins": [], "leaves": []})

            if member.id not in u_data["joins"]:
                u_data["joins"].append(member.id)
                save_invites_data(data)
                log.info("Invite tracked: %s invited by %s", member, inviter_id)

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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InvitesCog(bot))
