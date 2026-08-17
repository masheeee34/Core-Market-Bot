"""Trial Cog — Free Trial Key distribution system for BO7 External.
Zero-database fallback with JSON persistence (data/trial_keys.json).
Provides instant key distribution, anti-duplicate protection (1 key per member),
account age and verification security checks, direct Mega loader link,
GitBook installation guide, and staff logs.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("ticketbot.trial")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
KEYS_FILE = os.path.join(DATA_DIR, "trial_keys.json")

LOADER_MEGA_URL = "https://mega.nz/folder/w7VjQS6I#wav1HBlD04Hj9w-N_2CVaQ"
GUIDE_GITBOOK_URL = "https://trinityshop.gitbook.io/untitled/etapes-obligatoire/1.-virtualisation"

MIN_ACCOUNT_AGE_DAYS = 3

DEFAULT_KEYS = [
    "BO7-EXTERNAL-COREMARKET-TRIAL-Z8J76K4RE4QSQV-7CLDW8LR5BTWP9M",
    "BO7-EXTERNAL-COREMARKET-TRIAL-VLNQNWSTJPA4L9-ZMCN4YH8N788B1J",
    "BO7-EXTERNAL-COREMARKET-TRIAL-ZBCFYUJKX9UYBB-1SKLYV4U284APG2",
    "BO7-EXTERNAL-COREMARKET-TRIAL-6X36RFZU7PL95C-JR39P8E36FN63Y1",
    "BO7-EXTERNAL-COREMARKET-TRIAL-PMWGN8G5KANNL1-E3A8MAVGYXPGUSS",
    "BO7-EXTERNAL-COREMARKET-TRIAL-P8GKS11RNG6H38-NG7L77N756KD85X",
    "BO7-EXTERNAL-COREMARKET-TRIAL-WPMUCNWL8AFUPH-CZS3ST6USGUZEPX",
    "BO7-EXTERNAL-COREMARKET-TRIAL-6R8DYSS43URLP3-QFJ2K4HHBC4WQTH",
    "BO7-EXTERNAL-COREMARKET-TRIAL-UMS6U7Q4AZ78FY-GBHSZ7GUB236964",
    "BO7-EXTERNAL-COREMARKET-TRIAL-WMT43WHYPNVPNV-PKGTGS2RM4F2FZ1",
    "BO7-EXTERNAL-COREMARKET-TRIAL-D1PXJ6RWQXWT2U-LZYFKT316AG73QC",
    "BO7-EXTERNAL-COREMARKET-TRIAL-GT3112CZ3P6XK7-W49TEVSHSQYEXDZ",
    "BO7-EXTERNAL-COREMARKET-TRIAL-765ZUDK4C5GDTB-YT3J6VLQM3H1J2X",
    "BO7-EXTERNAL-COREMARKET-TRIAL-B9LK752NL6MBZS-1W8W1PDTRHU8K88",
    "BO7-EXTERNAL-COREMARKET-TRIAL-JUS6U53ALU69E9-YPF8CPDZ2E4L1TD",
    "BO7-EXTERNAL-COREMARKET-TRIAL-8P9V897UEW3HKU-YUMBD4XCQMFZMAM",
    "BO7-EXTERNAL-COREMARKET-TRIAL-UFN6CG4WVSN2BP-DR2ZSU4D4GLWBAT",
    "BO7-EXTERNAL-COREMARKET-TRIAL-GJDDLMALM2NN88-4LKSF1J27MQEEP3",
    "BO7-EXTERNAL-COREMARKET-TRIAL-YKGFU7SZREC4KN-X4LURKKERFH4NUT",
    "BO7-EXTERNAL-COREMARKET-TRIAL-T6SVVJ1RGKW3XG-AXK4HTMTM5M2FZ2",
    "BO7-EXTERNAL-COREMARKET-TRIAL-WY7V1W44PMHPS9-JCWQWEUM982PLVX",
    "BO7-EXTERNAL-COREMARKET-TRIAL-26B6M7C9TDQUFY-YTC92YCR478DDLP",
    "BO7-EXTERNAL-COREMARKET-TRIAL-9NE9768DMFN6BC-RY4JQG7LMZWTS3G",
    "BO7-EXTERNAL-COREMARKET-TRIAL-PF5UUAMDNKN1ZU-AT2SM84DFA3GSQJ",
    "BO7-EXTERNAL-COREMARKET-TRIAL-Y5YMYPDWL6CYNP-UM3BBVFVXQ4M9CM",
    "BO7-EXTERNAL-COREMARKET-TRIAL-YFFYDDW5475BXT-X1N7AKV2GXVJKLC",
    "BO7-EXTERNAL-COREMARKET-TRIAL-HH1HYH9JV3BLXH-88SXZT8U5PLTT29",
    "BO7-EXTERNAL-COREMARKET-TRIAL-XDBHQ68MLW2YQY-QPUYG98ZUS52174",
    "BO7-EXTERNAL-COREMARKET-TRIAL-QMXF7GQ85GR9WE-LUKMD7NSAT31LXN",
    "BO7-EXTERNAL-COREMARKET-TRIAL-AFBYSDMBNXPU3X-PLNGYULDVC4VM6D",
    "BO7-EXTERNAL-COREMARKET-TRIAL-HRT5RUDVJPG6UT-H1W15B1QDEXJJSG",
    "BO7-EXTERNAL-COREMARKET-TRIAL-ZTQWGJPUF6Q7LB-LDUBYB4GJYDEYJS",
    "BO7-EXTERNAL-COREMARKET-TRIAL-7XVHF8TBZYCBTR-CKVAPNE98W4BH3P",
    "BO7-EXTERNAL-COREMARKET-TRIAL-QTW2BTVPNV3NR6-UMRRGMC9SKUZKTP",
    "BO7-EXTERNAL-COREMARKET-TRIAL-MEMKBVD3ALC65P-QALN5WEMR8HL3JT",
    "BO7-EXTERNAL-COREMARKET-TRIAL-836DBXTSNJ2QHQ-FQW2WGHA797VWWS",
    "BO7-EXTERNAL-COREMARKET-TRIAL-WLAFVL7Z27LHX8-DYPFSV3MEPCFNY2",
    "BO7-EXTERNAL-COREMARKET-TRIAL-UJ7Y29VRG1METF-TQ2Y59WEEMVTCDE",
    "BO7-EXTERNAL-COREMARKET-TRIAL-TJHX37X19A3KE1-EBE3AKHUAFPFC77",
    "BO7-EXTERNAL-COREMARKET-TRIAL-BVPWR1GQHUR9CQ-XJ4BBQ9QCZQTNCV",
    "BO7-EXTERNAL-COREMARKET-TRIAL-R17ZV7LC4VDQJN-BSA6CGJ29XVFGRU",
    "BO7-EXTERNAL-COREMARKET-TRIAL-PMCPK9PV3DRSGY-KQCX3PQD4SLXFYN",
    "BO7-EXTERNAL-COREMARKET-TRIAL-6ZH6Q5CNTFBCDZ-M75ADYVC74UFSKT",
    "BO7-EXTERNAL-COREMARKET-TRIAL-VZLQPRLACHU7AV-XYTQFP9RNLKRN5W",
    "BO7-EXTERNAL-COREMARKET-TRIAL-TVY8KUHQQSVZFN-UHKNJLZ5CYJT5Y3",
    "BO7-EXTERNAL-COREMARKET-TRIAL-FAQ11NCFJRZDMK-5B2XAEHQESXGNSA",
    "BO7-EXTERNAL-COREMARKET-TRIAL-DDZ8CYSY45TG4N-3X9P667AHU4EEPT",
    "BO7-EXTERNAL-COREMARKET-TRIAL-MP692YDD1NQ34N-GSVXA773AH2QVAD",
]

PURGED_KEYS = {
    "BO7-EXTERNAL-COREMARKET-TRIAL-MNWCXFWJRRK9KR-HJQXZDY3TGWW9PN",
    "BO7-EXTERNAL-COREMARKET-TRIAL-R3KYXPJ9GMWDNR-6NZLA4L49W3412R",
}

_CLAIM_LOCK = asyncio.Lock()


def load_keys_data() -> dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(KEYS_FILE):
        data = {
            "available_keys": [k for k in DEFAULT_KEYS if k not in PURGED_KEYS],
            "claimed_keys": {},
        }
        save_keys_data(data)
        return data

    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "available_keys" not in data:
                data["available_keys"] = list(DEFAULT_KEYS)
            if "claimed_keys" not in data:
                data["claimed_keys"] = {}

            # Auto-purge invalidated keys from available and claimed history
            data["available_keys"] = [k for k in data["available_keys"] if k not in PURGED_KEYS]
            for uid, c_info in list(data["claimed_keys"].items()):
                c_key = c_info.get("key") if isinstance(c_info, dict) else str(c_info)
                if c_key in PURGED_KEYS:
                    del data["claimed_keys"][uid]

            save_keys_data(data)
            return data
    except Exception as e:
        log.error("Error reading trial keys file: %s", e)
        return {"available_keys": [k for k in DEFAULT_KEYS if k not in PURGED_KEYS], "claimed_keys": {}}


def save_keys_data(data: dict[str, Any]) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error("Error saving trial keys file: %s", e)


def build_trial_embed(lang: str = "en") -> discord.Embed:
    embed = discord.Embed(
        title="🎁  CORE MARKET — BO7 EXTERNAL FREE TRIAL",
        description=(
            "> **Experience our premium BO7 / Warzone software for FREE (1-Hour Trial)!**\n"
            "> Claim your unique trial license key below and follow the official setup guide.\n\n"
            "```ansi\n"
            "\u001b[1;36m[ ⚡ INCLUDED TRIAL FEATURES ]\u001b[0m\n"
            "```\n"
            "▸ **Silent & Smooth Aimbot :** Full customization with dynamic FOV\n"
            "▸ **Player ESP & Wallhack :** Skeletons, distance, health bars & 2D/3D boxes\n"
            "▸ **Streamproof :** Completely invisible on OBS, Discord and screen share\n"
            "▸ **Fast Loader :** Instant injection without mandatory PC restart\n\n"
            "```ansi\n"
            "\u001b[1;34m[ 📋 QUICK START INSTRUCTIONS ]\u001b[0m\n"
            "```\n"
            "**` 1 `** Click the green **🎁 Claim Free Trial (1H)** button below\n"
            "**` 2 `** Download the loader package from **📥 Download Loader (Mega)**\n"
            "**` 3 `** Read the step-by-step **📖 Setup Guide (GitBook)** (Virtualization / Security)\n"
            "**` 4 `** Open the loader, paste your trial key, and dominate the game!"
        ),
        color=discord.Color.from_str("#0070FF"),
    )
    embed.add_field(
        name="🌐 System Compatibility",
        value=(
            "• **OS :** Windows 10 & 11 (All versions)\n"
            "• **Processors :** Intel & AMD CPUs supported\n"
            "• **Virtualization :** Enabled in BIOS (SVM / Intel VT-x)\n"
            "• **Anti-Cheat :** Ricochet (Undetected)"
        ),
        inline=False,
    )
    embed.set_footer(text="CORE MARKET • Limit: 1 trial key per member (1-Hour Trial)")

    if os.path.exists("banner.gif"):
        embed.set_image(url="attachment://banner.gif")

    return embed


class TrialClaimView(discord.ui.View):
    """Persistent view for Free Trial claiming and direct resource links in English."""

    def __init__(self, lang: str = "en") -> None:
        super().__init__(timeout=None)

        # Add Mega direct download link button
        self.add_item(
            discord.ui.Button(
                label="Download Loader (Mega)",
                url=LOADER_MEGA_URL,
                emoji="📥",
                style=discord.ButtonStyle.link,
                row=1,
            )
        )
        # Add GitBook guide link button
        self.add_item(
            discord.ui.Button(
                label="Setup Guide (GitBook)",
                url=GUIDE_GITBOOK_URL,
                emoji="📖",
                style=discord.ButtonStyle.link,
                row=1,
            )
        )

    @discord.ui.button(
        label="Claim Free Trial (1H)",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="trial_claim_button_v1",
        row=0,
    )
    async def claim_trial(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        trial_cog = interaction.client.get_cog("Trial")
        if trial_cog and hasattr(trial_cog, "deliver_key_to_user"):
            await trial_cog.deliver_key_to_user(interaction, interaction.user)
        else:
            await handle_trial_claim(interaction, interaction.user)

async def handle_trial_claim(interaction: discord.Interaction, user: discord.User | discord.Member) -> None:
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    user_id_str = str(user.id)

    # ----------------- SECURITY CHECK 1: Account Age -----------------
    now_dt = discord.utils.utcnow()
    account_age = now_dt - user.created_at
    if account_age < timedelta(days=MIN_ACCOUNT_AGE_DAYS):
        embed_sec = discord.Embed(
            title="⛔  ACCOUNT SECURITY VERIFICATION",
            description=(
                f"Sorry {user.mention}, your Discord account is too new.\n\n"
                f"▸ **Required Account Age :** At least `{MIN_ACCOUNT_AGE_DAYS} days old`\n"
                f"▸ **Your Account Age :** `{account_age.days} day(s)`\n\n"
                "🛡️ *This security measure prevents automated bot accounts and key farming. If you are a legitimate user, please contact staff in support.*"
            ),
            color=discord.Color.red(),
        )
        embed_sec.set_footer(text="CORE MARKET • Anti-Abuse Protection")
        await interaction.followup.send(embed=embed_sec, ephemeral=True)
        return

        # ----------------- CONCURRENCY LOCK -----------------
        async with _CLAIM_LOCK:
            data = load_keys_data()
            claimed_keys = data.get("claimed_keys", {})
            available_keys = data.get("available_keys", [])

            # 1. Check if member already claimed a key
            if user_id_str in claimed_keys:
                claimed_info = claimed_keys[user_id_str]
                key = claimed_info["key"] if isinstance(claimed_info, dict) else str(claimed_info)

                embed_already = discord.Embed(
                    title="ℹ️  YOU HAVE ALREADY CLAIMED YOUR TRIAL KEY",
                    description=(
                        f"Hello {user.mention}, you have already received your free 1-hour trial key.\n\n"
                        f"🔑 **Your BO7 Trial Key :**\n"
                        f"```{key}```\n"
                        f"📥 **Download Loader :** [Download Loader via Mega]({LOADER_MEGA_URL})\n"
                        f"📖 **Setup Guide :** [View Official Setup Guide (GitBook)]({GUIDE_GITBOOK_URL})\n\n"
                        f"💎 *Need help or want to purchase the full version? Open a ticket in support!*"
                    ),
                    color=discord.Color.from_str("#0070FF"),
                )
                embed_already.set_footer(text="CORE MARKET • 1-Hour Free Trial")
                await interaction.followup.send(embed=embed_already, ephemeral=True)
                return

            # 2. Check if stock is available
            if not available_keys:
                embed_empty = discord.Embed(
                    title="⚠️  FREE TRIAL STOCK DEPLETED",
                    description=(
                        "Sorry, all free trial keys have been claimed for now!\n\n"
                        "▸ Our staff will restock additional keys very soon.\n"
                        "▸ You can also open a ticket to purchase a full license (Day / Week / Month / Lifetime)."
                    ),
                    color=discord.Color.orange(),
                )
                embed_empty.set_footer(text="CORE MARKET • Support & Orders")
                await interaction.followup.send(embed=embed_empty, ephemeral=True)
                return

            # 3. Pop an available key and record claim atomically
            key_given = available_keys.pop(0)
            now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
            claimed_keys[user_id_str] = {
                "key": key_given,
                "user_name": str(user),
                "claimed_at": now_str,
            }
            data["available_keys"] = available_keys
            data["claimed_keys"] = claimed_keys
            save_keys_data(data)

        # 4. Deliver key in ephemeral response (in English)
        embed_success = discord.Embed(
            title="🎉  YOUR BO7 FREE TRIAL KEY IS READY!",
            description=(
                f"Congratulations {user.mention}! Here is your **BO7 External (1-Hour Trial)** license key.\n\n"
                "```ansi\n"
                "\u001b[1;32m[ 🔑 YOUR PERSONAL TRIAL LICENSE KEY ]\u001b[0m\n"
                "```\n"
                f"```{key_given}```\n"
                "```ansi\n"
                "\u001b[1;36m[ 📥 DOWNLOAD & QUICK INSTRUCTIONS ]\u001b[0m\n"
                "```\n"
                f"▸ **` 1 ` Download Loader :** [Click here to download via Mega]({LOADER_MEGA_URL})\n"
                f"▸ **` 2 ` Step-by-Step Guide :** [View Official Setup Guide (GitBook)]({GUIDE_GITBOOK_URL})\n"
                f"▸ **` 3 ` Activation :** Extract the archive, run the Loader as Administrator, and paste your key.\n\n"
                "──────────────────────────────────────────\n"
                "⚠️ **Important :** Make sure Virtualization (SVM / Intel VT-x) is enabled in your BIOS before launching."
            ),
            color=discord.Color.green(),
        )
        embed_success.set_footer(text="CORE MARKET • Enjoy your session! (1-Hour Trial)")
        await interaction.followup.send(embed=embed_success, ephemeral=True)

        # 5. Backup DM delivery
        try:
            embed_dm = discord.Embed(
                title="🎁  CORE MARKET — YOUR TRIAL LICENSE KEY",
                description=(
                    "> **Thank you for trying Core Market BO7 / Warzone software!**\n"
                    "> Here is your official trial license key and complete setup instructions.\n\n"
                    "```ansi\n"
                    "\u001b[1;32m[ 🔑 YOUR PERSONAL 1-HOUR LICENSE KEY ]\u001b[0m\n"
                    "```\n"
                    f"```{key_given}```\n"
                    "```ansi\n"
                    "\u001b[1;36m[ 📥 DOWNLOAD & QUICK START GUIDE ]\u001b[0m\n"
                    "```\n"
                    f"**` 1 ` Download Loader :** [Click to Download via Mega]({LOADER_MEGA_URL})\n"
                    f"**` 2 ` Setup Guide :** [View Step-by-Step GitBook Guide]({GUIDE_GITBOOK_URL})\n"
                    f"**` 3 ` Activation :** Run loader as Admin ➔ Paste your key ➔ Launch Game\n\n"
                    "🛡️ *Ensure Virtualization (SVM / Intel VT-x) is enabled in BIOS before launching.*"
                ),
                color=discord.Color.from_str("#0070FF"),
            )
            embed_dm.set_footer(text="CORE MARKET • 1-Hour Free Trial • Need help? Open a ticket!")
            await user.send(embed=embed_dm)
        except Exception:
            pass

        # 6. Log claim to staff logs channel
        if guild:
            logs_channel = (
                discord.utils.get(guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ")
                or discord.utils.get(guild.text_channels, name="📜・logs-tickets")
                or discord.utils.get(guild.text_channels, name="📜 ┃ 𝖑𝖔𝖌𝖘-𝖙𝖎𝖈𝖐𝖊𝖙𝖘")
                or discord.utils.get(guild.text_channels, name="logs")
            )
            if logs_channel:
                log_embed = discord.Embed(
                    title="🎁  Free Trial Claimed",
                    description=(
                        f"**Member :** {user.mention} (`{user.id}`)\n"
                        f"**Assigned Key :** `{key_given}`\n"
                        f"**Remaining Stock :** `{len(available_keys)} keys available`\n"
                        f"**Account Age :** `{account_age.days} days`\n"
                        f"**Date :** `{now_str}`"
                    ),
                    color=discord.Color.from_str("#0070FF"),
                    timestamp=discord.utils.utcnow(),
                )
                if user.display_avatar:
                    log_embed.set_thumbnail(url=user.display_avatar.url)
                await logs_channel.send(embed=log_embed)


async def send_trial_panel(
    channel: discord.TextChannel,
    lang: str = "en",
) -> None:
    """Utility to post the complete Trial Panel with banner and view."""
    embed = build_trial_embed(lang=lang)
    view = TrialClaimView(lang=lang)

    if os.path.exists("banner.gif"):
        try:
            banner_file = discord.File("banner.gif", filename="banner.gif")
            await channel.send(file=banner_file, embed=embed, view=view)
            return
        except Exception:
            pass

    await channel.send(embed=embed, view=view)


class Trial(commands.Cog):
    """Cog managing Free Trial keys, panel posting, and admin inventory."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def deliver_key_to_user(self, interaction: discord.Interaction, user: discord.User | discord.Member) -> None:
        await handle_trial_claim(interaction, user)

    async def cog_load(self) -> None:
        # Register persistent view so buttons work across restarts
        self.bot.add_view(TrialClaimView(lang="en"))
        # Ensure initial JSON keys exist
        load_keys_data()

    @app_commands.command(
        name="trial_panel",
        description="Post the interactive Free Trial distribution panel with buttons",
    )
    @app_commands.describe(
        salon="Channel where to post the panel (defaults to current channel)",
        langue="Panel language (English or Français)",
    )
    @app_commands.choices(
        langue=[
            app_commands.Choice(name="English 🇬🇧", value="en"),
            app_commands.Choice(name="Français 🇫🇷", value="fr"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def trial_panel(
        self,
        interaction: discord.Interaction,
        salon: discord.TextChannel | None = None,
        langue: app_commands.Choice[str] | None = None,
    ) -> None:
        target_channel = salon or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message("⚠️ Invalid channel.", ephemeral=True)
            return

        lang = langue.value if langue else "en"
        await send_trial_panel(target_channel, lang=lang)
        await interaction.response.send_message(
            f"✅ Free Trial panel successfully posted in {target_channel.mention}!",
            ephemeral=True,
        )

    @app_commands.command(
        name="trial_stock",
        description="View remaining trial keys stock and claim statistics",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def trial_stock(self, interaction: discord.Interaction) -> None:
        data = load_keys_data()
        available = data.get("available_keys", [])
        claimed = data.get("claimed_keys", {})

        embed = discord.Embed(
            title="📊  FREE TRIAL STOCK INVENTORY",
            color=discord.Color.from_str("#0070FF"),
            description=(
                f"**🟢 Keys Available in Stock :** `{len(available)}`\n"
                f"**🎁 Keys Claimed by Members :** `{len(claimed)}`\n"
                f"**📦 Total Managed :** `{len(available) + len(claimed)}`\n\n"
                f"📥 **Loader Link :** [Mega]({LOADER_MEGA_URL})\n"
                f"📖 **Setup Guide :** [GitBook]({GUIDE_GITBOOK_URL})"
            ),
        )

        # Show last 5 claims
        if claimed:
            recent_claims = list(claimed.items())[-5:]
            lines = []
            for uid, info in reversed(recent_claims):
                uname = info.get("user_name", uid) if isinstance(info, dict) else uid
                date = info.get("claimed_at", "") if isinstance(info, dict) else ""
                lines.append(f"• <@{uid}> (`{uname}`) — *{date}*")
            embed.add_field(name="Recent Key Deliveries", value="\n".join(lines), inline=False)

        embed.set_footer(text="Core Market • Stock Management")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="trial_add_keys",
        description="Add new trial license keys to the available stock",
    )
    @app_commands.describe(
        cles="Keys to add (separated by newlines, spaces, or commas)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def trial_add_keys(self, interaction: discord.Interaction, cles: str) -> None:
        import re
        raw_keys = re.split(r"[\n,\s]+", cles.strip())
        new_keys = [k.strip() for k in raw_keys if k.strip()]

        if not new_keys:
            await interaction.response.send_message("⚠️ No valid keys provided.", ephemeral=True)
            return

        data = load_keys_data()
        available = data.get("available_keys", [])
        added_count = 0

        for k in new_keys:
            if k not in available:
                available.append(k)
                added_count += 1

        data["available_keys"] = available
        save_keys_data(data)

        await interaction.response.send_message(
            f"✅ **{added_count}** new key(s) added to stock! (Total available: `{len(available)}`)",
            ephemeral=True,
        )

    @app_commands.command(
        name="trial_reset_user",
        description="Reset a member's trial claim status so they can claim another key",
    )
    @app_commands.describe(
        membre="Member to reset",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def trial_reset_user(self, interaction: discord.Interaction, membre: discord.Member) -> None:
        data = load_keys_data()
        claimed = data.get("claimed_keys", {})
        uid = str(membre.id)

        if uid in claimed:
            del claimed[uid]
            data["claimed_keys"] = claimed
            save_keys_data(data)
            await interaction.response.send_message(
                f"✅ Status reset for {membre.mention}! They can now claim a new trial key.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ {membre.mention} has no claim recorded in history.",
                ephemeral=True,
            )

    @app_commands.command(
        name="trial_reset_all",
        description="Reset ALL trial claim history for everyone so new keys can be claimed",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def trial_reset_all(self, interaction: discord.Interaction) -> None:
        data = load_keys_data()
        claimed_count = len(data.get("claimed_keys", {}))
        data["claimed_keys"] = {}
        save_keys_data(data)

        await interaction.response.send_message(
            f"🧹 **Historique réinitialisé !** `{claimed_count}` réclamation(s) effacée(s). Tous les membres peuvent maintenant réclamer une nouvelle clé fraîche !",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Trial(bot))
