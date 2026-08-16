import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

log = logging.getLogger("cogs.giveaway")

DATA_PATH = Path("data/giveaways.json")


def load_giveaways() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_giveaways(data: dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_duration(text: str) -> timedelta | None:
    """Parses duration strings like 10m, 2h, 1d, 3d, 30s."""
    match = re.fullmatch(r"(\d+)\s*([smhd])", text.strip().lower())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
    return timedelta(**{units[unit]: val})


class GiveawayModal(discord.ui.Modal, title="🎁 Create a Giveaway"):
    prize = discord.ui.TextInput(
        label="Prize / Key to Win",
        placeholder="e.g. TRINITY SPECTRE — 7 Days Key",
        required=True,
        max_length=100,
    )
    duration = discord.ui.TextInput(
        label="Duration (e.g. 30m, 2h, 1d, 3d)",
        placeholder="e.g. 24h",
        required=True,
        max_length=10,
    )
    winners_count = discord.ui.TextInput(
        label="Number of Winners",
        placeholder="1",
        default="1",
        required=True,
        max_length=2,
    )
    secret_key = discord.ui.TextInput(
        label="License Key to Auto-DM (Optional)",
        placeholder="e.g. SPECTRE-XXXX-XXXX (Delivered in DM to winner)",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500,
    )
    notes = discord.ui.TextInput(
        label="Requirements / Notes (Optional)",
        placeholder="e.g. Must be verified in #rules • Good luck!",
        required=False,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        delta = parse_duration(str(self.duration))
        if not delta:
            await interaction.response.send_message("❌ Invalid duration format. Use e.g. `30m`, `2h`, `1d`, `3d`.", ephemeral=True)
            return

        try:
            winners_num = max(1, int(str(self.winners_count).strip()))
        except ValueError:
            await interaction.response.send_message("❌ Winners count must be a number.", ephemeral=True)
            return

        end_dt = datetime.now(timezone.utc) + delta
        end_timestamp = int(end_dt.timestamp())

        embed = discord.Embed(
            title=f"🎁  SPECIAL COMMUNITY GIVEAWAY — {str(self.prize).upper()}",
            description=(
                "> **React now to win exclusive premium access on Core Market!**\n"
                "> Click the green **🎉 Enter Giveaway** button below to record your participation.\n\n"
                "```ansi\n"
                "\u001b[1;33m[ 🏆 PRIZE & REWARD ]\u001b[0m\n"
                "```\n"
                f"▸ **Prize :** **`{self.prize}`**\n"
                f"▸ **Total Winners :** **`{winners_num} lucky winner(s)`**\n\n"
                "```ansi\n"
                "\u001b[1;36m[ ⏳ EVENT DETAILS & TIMELINE ]\u001b[0m\n"
                "```\n"
                f"▸ **Ends In :** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)\n"
                f"▸ **Hosted by :** {interaction.user.mention}\n"
                + (f"▸ **Requirements :** *{self.notes}*\n\n" if str(self.notes).strip() else "\n")
                + "```ansi\n"
                "\u001b[1;32m[ ⚡ HOW TO PARTICIPATE ]\u001b[0m\n"
                "```\n"
                "**` 1 `** Click the **🎉 Enter Giveaway** button below.\n"
                "**` 2 `** When the timer ends, our bot will automatically draw the winner(s)!\n"
                "**` 3 `** If a license key is attached, it will be delivered straight to your DMs."
            ),
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text="CORE MARKET • Automated Giveaway Engine • Limit: 1 entry per member")

        if os.path.exists("banner.gif"):
            embed.set_image(url="attachment://banner.gif")

        await interaction.response.send_message("✅ Giveaway created successfully!", ephemeral=True)

        view = GiveawayEntryView()
        msg = await interaction.channel.send(embed=embed, view=view)

        data = load_giveaways()
        data[str(msg.id)] = {
            "channel_id": interaction.channel_id,
            "guild_id": interaction.guild_id,
            "prize": str(self.prize),
            "winners_count": winners_num,
            "end_timestamp": end_timestamp,
            "host_id": interaction.user.id,
            "secret_key": str(self.secret_key).strip(),
            "entries": [],
            "ended": False,
        }
        save_giveaways(data)


class GiveawayEntryView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Enter Giveaway (0)",
        emoji="🎉",
        style=discord.ButtonStyle.success,
        custom_id="giveaway_entry_btn",
    )
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        msg_id = str(interaction.message.id)
        data = load_giveaways()
        gw = data.get(msg_id)

        if not gw or gw.get("ended"):
            await interaction.response.send_message("❌ This giveaway has already ended.", ephemeral=True)
            return

        user_id = interaction.user.id
        entries = gw.setdefault("entries", [])

        if user_id in entries:
            entries.remove(user_id)
            msg = "👋 You left the giveaway."
        else:
            entries.append(user_id)
            msg = "🎉 **You entered the giveaway!** Good luck!"

        save_giveaways(data)

        button.label = f"Enter Giveaway ({len(entries)})"
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        await interaction.response.send_message(msg, ephemeral=True)


class GiveawayCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.check_giveaways.start()

    def cog_unload(self) -> None:
        self.check_giveaways.cancel()

    @tasks.loop(seconds=15)
    async def check_giveaways(self) -> None:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        data = load_giveaways()
        updated = False

        for msg_id, gw in list(data.items()):
            if gw.get("ended") or now_ts < gw.get("end_timestamp", 0):
                continue

            gw["ended"] = True
            updated = True
            await self._finish_giveaway(msg_id, gw)

        if updated:
            save_giveaways(data)

    async def _finish_giveaway(self, msg_id: str, gw: dict[str, Any]) -> None:
        channel = self.bot.get_channel(gw["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            msg = await channel.fetch_message(int(msg_id))
        except Exception:
            return

        entries = gw.get("entries", [])
        winners_count = gw.get("winners_count", 1)
        prize = gw.get("prize", "Prize")
        secret_key = gw.get("secret_key", "")

        if not entries:
            embed = msg.embeds[0] if msg.embeds else discord.Embed(title="🎉 GIVEAWAY ENDED")
            embed.color = discord.Color.red()
            embed.description = f"**🏆 Prize :** `{prize}`\n\n❌ **No entries.** No winner could be drawn."
            await msg.edit(embed=embed, view=None)
            await channel.send(f"⚠️ Giveaway for **{prize}** ended with 0 participants.")
            return

        picked_ids = random.sample(entries, min(len(entries), winners_count))
        winners_mentions = ", ".join(f"<@{uid}>" for uid in picked_ids)

        embed = msg.embeds[0] if msg.embeds else discord.Embed(title="🎉 GIVEAWAY ENDED")
        embed.color = discord.Color.from_str("#FFD700")
        embed.title = f"👑  GIVEAWAY CONCLUDED — {prize.upper()}"
        embed.description = (
            "```ansi\n"
            "\u001b[1;33m[ 🏆 OFFICIAL WINNER(S) ]\u001b[0m\n"
            "```\n"
            f"▸ **Prize :** **`{prize}`**\n"
            f"▸ **Winner(s) :** {winners_mentions}\n"
            f"▸ **Total Participants :** **`{len(entries)} members`**\n\n"
            "🛡️ *Rewards have been sent via DM or can be claimed inside support tickets.*"
        )
        embed.set_footer(text="CORE MARKET • Giveaway Concluded")
        await msg.edit(embed=embed, view=None)

        congrats_embed = discord.Embed(
            title="🎉  CONGRATULATIONS TO THE WINNER(S)!",
            description=(
                f"GG {winners_mentions}! You won the **`{prize}`** giveaway!\n\n"
                "```ansi\n"
                "\u001b[1;32m[ 🎁 HOW TO CLAIM YOUR PRIZE ]\u001b[0m\n"
                "```\n"
                "▸ Check your direct messages (DM) from Core Market.\n"
                "▸ Or open a ticket in <#🎫・creer-un-ticket> to claim your license."
            ),
            color=discord.Color.green(),
        )
        congrats_embed.set_footer(text="CORE MARKET • Official Winner Announcement")
        await channel.send(content=f"👑 {winners_mentions}", embed=congrats_embed)

        # Optional Auto-DM secret key to winners
        if secret_key:
            for uid in picked_ids:
                user = self.bot.get_user(uid)
                if user:
                    try:
                        dm_embed = discord.Embed(
                            title="🎁  YOUR CORE MARKET GIVEAWAY REWARD!",
                            description=(
                                f"Congratulations {user.mention}! You won **`{prize}`**!\n\n"
                                "```ansi\n"
                                "\u001b[1;32m[ 🔑 YOUR PERSONAL LICENSE KEY ]\u001b[0m\n"
                                "```\n"
                                f"```{secret_key}```\n\n"
                                "▸ **Setup Guide :** https://trinityshop.gitbook.io/untitled/etapes-obligatoire/1.-virtualisation\n"
                                "▸ **Support :** Need assistance? Open a ticket on our Discord server."
                            ),
                            color=discord.Color.green(),
                        )
                        dm_embed.set_footer(text="CORE MARKET • Enjoy your prize!")
                        await user.send(embed=dm_embed)
                    except Exception:
                        pass

    @app_commands.command(name="giveaway", description="Create a new interactive Giveaway with modal setup")
    @app_commands.default_permissions(administrator=True)
    async def giveaway_cmd(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(GiveawayModal())

    @app_commands.command(name="giveaway_reroll", description="Reroll winners for an ended giveaway")
    @app_commands.default_permissions(administrator=True)
    async def reroll_cmd(self, interaction: discord.Interaction, message_id: str) -> None:
        data = load_giveaways()
        gw = data.get(message_id)
        if not gw or not gw.get("entries"):
            await interaction.response.send_message("❌ Giveaway not found or no entries available.", ephemeral=True)
            return

        entries = gw["entries"]
        new_winner_id = random.choice(entries)
        await interaction.response.send_message(
            f"🎉 **Reroll Winner :** <@{new_winner_id}> won **{gw.get('prize')}**!"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GiveawayCog(bot))
    bot.add_view(GiveawayEntryView())
