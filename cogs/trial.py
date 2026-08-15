"""Trial Cog — Free Trial Key distribution system for BO7 External.
Zero-database fallback with JSON persistence (data/trial_keys.json).
Provides instant key distribution, anti-duplicate protection (1 key per member),
direct Mega loader link, GitBook installation guide, and staff logs.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("ticketbot.trial")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
KEYS_FILE = os.path.join(DATA_DIR, "trial_keys.json")

LOADER_MEGA_URL = "https://mega.nz/folder/w7VjQS6I#wav1HBlD04Hj9w-N_2CVaQ"
GUIDE_GITBOOK_URL = "https://trinityshop.gitbook.io/untitled/etapes-obligatoire/1.-virtualisation"

DEFAULT_KEYS = [
    "BO7-EXTERNAL-COREMARKET-TRIAL-Z8J76K4RE4QSQV-7CLDW8LR5BTWP9M",
    "BO7-EXTERNAL-COREMARKET-TRIAL-MNWCXFWJRRK9KR-HJQXZDY3TGWW9PN",
    "BO7-EXTERNAL-COREMARKET-TRIAL-VLNQNWSTJPA4L9-ZMCN4YH8N788B1J",
    "BO7-EXTERNAL-COREMARKET-TRIAL-ZBCFYUJKX9UYBB-1SKLYV4U284APG2",
    "BO7-EXTERNAL-COREMARKET-TRIAL-6X36RFZU7PL95C-JR39P8E36FN63Y1",
    "BO7-EXTERNAL-COREMARKET-TRIAL-R3KYXPJ9GMWDNR-6NZLA4L49W3412R",
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


def load_keys_data() -> dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(KEYS_FILE):
        data = {
            "available_keys": list(DEFAULT_KEYS),
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
            return data
    except Exception as e:
        log.error("Error reading trial keys file: %s", e)
        return {"available_keys": list(DEFAULT_KEYS), "claimed_keys": {}}


def save_keys_data(data: dict[str, Any]) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error("Error saving trial keys file: %s", e)


def build_trial_embed(lang: str = "fr") -> discord.Embed:
    is_fr = lang.lower() == "fr"

    if is_fr:
        embed = discord.Embed(
            title="🎁  CORE MARKET — ESSAI GRATUIT BO7 EXTERNAL",
            description=(
                "> **Testez gratuitement notre logiciel BO7 / Warzone pendant 24 Heures !**\n"
                "> Récupérez votre clé d'essai instantanément et suivez le guide d'installation.\n\n"
                "```ansi\n"
                "\u001b[1;36m[ ⚡ INFORMATIONS & FONCTIONNALITÉS ]\u001b[0m\n"
                "```\n"
                "▸ **Aimbot Silencieux & Smooth :** Précision chirurgicale entièrement paramétrable\n"
                "▸ **Player ESP & Wallhack :** Squelette, distance, armure et box 2D/3D\n"
                "▸ **Streamproof / Invisible :** Indétectable sur OBS / Discord / Spectateurs\n"
                "▸ **No-Restart Loader :** Injection ultra rapide sans redémarrage requis\n\n"
                "```ansi\n"
                "\u001b[1;34m[ 📋 ÉTAPES D'ACTIVATION ]\u001b[0m\n"
                "```\n"
                "**` 1 `** Cliquez sur le bouton vert **🎁 Réclamer mon Essai Gratuit**\n"
                "**` 2 `** Téléchargez le Loader via le bouton **📥 Télécharger le Loader (Mega)**\n"
                "**` 3 `** Consultez le **📖 Guide d'Installation (GitBook)** pour configurer la virtualisation\n"
                "**` 4 `** Lancez le loader, collez votre clé d'essai et profitez de votre session !"
            ),
            color=discord.Color.from_str("#0070FF"),
        )
        embed.add_field(
            name="🌐 Compatibilité Système",
            value=(
                "• **OS :** Windows 10 & 11 (Toutes versions)\n"
                "• **Processeur :** Intel & AMD supportés\n"
                "• **Virtualisation :** Activée dans le BIOS (SVM / Intel VT-x)\n"
                "• **Anti-Cheat :** Ricochet (Undetected)"
            ),
            inline=False,
        )
        embed.set_footer(text="CORE MARKET • 1 clé d'essai gratuite par membre")
    else:
        embed = discord.Embed(
            title="🎁  CORE MARKET — BO7 EXTERNAL FREE TRIAL",
            description=(
                "> **Experience our premium BO7 / Warzone software for FREE (24H Trial)!**\n"
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
                "**` 1 `** Click the green **🎁 Claim Free Trial (24H)** button below\n"
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
        embed.set_footer(text="CORE MARKET • Limit: 1 trial key per member")

    if os.path.exists("banner.gif"):
        embed.set_image(url="attachment://banner.gif")

    return embed


class TrialClaimView(discord.ui.View):
    """Persistent view for Free Trial claiming and direct resource links."""

    def __init__(self) -> None:
        super().__init__(timeout=None)
        # Add Mega direct download link button
        self.add_item(
            discord.ui.Button(
                label="Télécharger le Loader (Mega)",
                url=LOADER_MEGA_URL,
                emoji="📥",
                style=discord.ButtonStyle.link,
                row=1,
            )
        )
        # Add GitBook guide link button
        self.add_item(
            discord.ui.Button(
                label="Guide d'Installation (GitBook)",
                url=GUIDE_GITBOOK_URL,
                emoji="📖",
                style=discord.ButtonStyle.link,
                row=1,
            )
        )

    @discord.ui.button(
        label="Réclamer mon Essai Gratuit (24H)",
        emoji="🎁",
        style=discord.ButtonStyle.success,
        custom_id="trial_claim_button_v1",
        row=0,
    )
    async def claim_trial(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        guild = interaction.guild
        user_id_str = str(user.id)

        data = load_keys_data()
        claimed_keys = data.get("claimed_keys", {})
        available_keys = data.get("available_keys", [])

        # 1. Check if member already claimed a key
        if user_id_str in claimed_keys:
            claimed_info = claimed_keys[user_id_str]
            key = claimed_info["key"] if isinstance(claimed_info, dict) else str(claimed_info)
            claimed_date = claimed_info.get("claimed_at", "Précédemment") if isinstance(claimed_info, dict) else ""

            embed_already = discord.Embed(
                title="ℹ️  VOUS AVEZ DÉJÀ RÉCLAMÉ VOTRE CLÉ D'ESSAI",
                description=(
                    f"Bonjour {user.mention}, vous avez déjà obtenu votre clé d'essai gratuite.\n\n"
                    f"🔑 **Votre Clé d'Essai BO7 :**\n"
                    f"```{key}```\n"
                    f"📥 **Lien de Téléchargement :** [Télécharger le Loader via Mega]({LOADER_MEGA_URL})\n"
                    f"📖 **Guide d'Installation :** [Consulter le Guide GitBook]({GUIDE_GITBOOK_URL})\n\n"
                    f"💡 *Besoin d'aide ou de la version complète ? Ouvrez un ticket dans le salon support !*"
                ),
                color=discord.Color.from_str("#0070FF"),
            )
            embed_already.set_footer(text="CORE MARKET • Essai Gratuit 24H")
            await interaction.followup.send(embed=embed_already, ephemeral=True)
            return

        # 2. Check if stock is available
        if not available_keys:
            embed_empty = discord.Embed(
                title="⚠️  STOCK D'ESSAI GRATUIT ÉPUISÉ",
                description=(
                    "Désolé, toutes les clés d'essai ont été réclamées pour le moment !\n\n"
                    "▸ Le stock sera réapprovisionné très prochainement par l'équipe.\n"
                    "▸ Vous pouvez également ouvrir un ticket pour commander une licence complète (Jour / Semaine / Mois / Lifetime)."
                ),
                color=discord.Color.orange(),
            )
            embed_empty.set_footer(text="CORE MARKET • Support & Commandes")
            await interaction.followup.send(embed=embed_empty, ephemeral=True)
            return

        # 3. Pop an available key and record claim
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

        # 4. Deliver key in ephemeral response
        embed_success = discord.Embed(
            title="🎉  VOTRE CLÉ D'ESSAI BO7 EST PRÊTE !",
            description=(
                f"Félicitations {user.mention} ! Voici votre clé d'essai gratuit **BO7 External (24H)**.\n\n"
                "```ansi\n"
                "\u001b[1;32m[ 🔑 VOTRE CLÉ D'ESSAI PERSONNELLE ]\u001b[0m\n"
                "```\n"
                f"```{key_given}```\n"
                "```ansi\n"
                "\u001b[1;36m[ 📥 TÉLÉCHARGEMENT & INSTRUCTIONS ]\u001b[0m\n"
                "```\n"
                f"▸ **` 1 ` Télécharger le Loader :** [Cliquez ici pour télécharger sur Mega]({LOADER_MEGA_URL})\n"
                f"▸ **` 2 ` Guide d'Installation :** [Consultez le Guide GitBook Obligatoire]({GUIDE_GITBOOK_URL})\n"
                f"▸ **` 3 ` Activation :** Extrayez l'archive, lancez le loader en Administrateur, et collez votre clé.\n\n"
                "──────────────────────────────────────────\n"
                "⚠️ **Important :** Assurez-vous que la virtualisation est activée dans votre BIOS avant de lancer."
            ),
            color=discord.Color.green(),
        )
        embed_success.set_footer(text="CORE MARKET • Bon jeu à vous !")
        await interaction.followup.send(embed=embed_success, ephemeral=True)

        # 5. Backup DM delivery
        try:
            embed_dm = discord.Embed(
                title="🎁  CORE MARKET — VOTRE CLÉ D'ESSAI BO7",
                description=(
                    f"Voici une copie de votre clé d'essai pour **{guild.name if guild else 'Core Market'}** :\n\n"
                    f"🔑 **Clé :** `{key_given}`\n\n"
                    f"📥 **Loader Mega :** {LOADER_MEGA_URL}\n"
                    f"📖 **Guide GitBook :** {GUIDE_GITBOOK_URL}\n\n"
                    f"Bon jeu !"
                ),
                color=discord.Color.from_str("#0070FF"),
            )
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
                    title="🎁  Essai Gratuit Réclamé",
                    description=(
                        f"**Membre :** {user.mention} (`{user.id}`)\n"
                        f"**Clé attribuée :** `{key_given}`\n"
                        f"**Stock restant :** `{len(available_keys)} clés disponibles`\n"
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
    lang: str = "fr",
) -> None:
    """Utility to post the complete Trial Panel with banner and view."""
    embed = build_trial_embed(lang=lang)
    view = TrialClaimView()

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

    async def cog_load(self) -> None:
        # Register persistent view so buttons work across restarts
        self.bot.add_view(TrialClaimView())
        # Ensure initial JSON keys exist
        load_keys_data()

    @app_commands.command(
        name="trial_panel",
        description="Poster le panel interactif de distribution d'essais gratuits (Free Trial)",
    )
    @app_commands.describe(
        salon="Salon où poster le panel (par défaut le salon actuel)",
        langue="Langue du panel (Français ou Anglais)",
    )
    @app_commands.choices(
        langue=[
            app_commands.Choice(name="Français 🇫🇷", value="fr"),
            app_commands.Choice(name="English 🇬🇧", value="en"),
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
            await interaction.response.send_message("⚠️ Salon invalide.", ephemeral=True)
            return

        lang = langue.value if langue else "fr"
        await send_trial_panel(target_channel, lang=lang)
        await interaction.response.send_message(
            f"✅ Panel Free Trial posté avec succès dans {target_channel.mention} !",
            ephemeral=True,
        )

    @app_commands.command(
        name="trial_stock",
        description="Afficher l'état du stock de clés d'essai et le nombre de clés données",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def trial_stock(self, interaction: discord.Interaction) -> None:
        data = load_keys_data()
        available = data.get("available_keys", [])
        claimed = data.get("claimed_keys", {})

        embed = discord.Embed(
            title="📊  INVENTAIRE DES CLÉS D'ESSAI (TRIAL STOCK)",
            color=discord.Color.from_str("#0070FF"),
            description=(
                f"**🟢 Clés disponibles en stock :** `{len(available)}`\n"
                f"**🎁 Clés réclamées par les membres :** `{len(claimed)}`\n"
                f"**📦 Total géré :** `{len(available) + len(claimed)}`\n\n"
                f"📥 **Lien Loader :** [Mega]({LOADER_MEGA_URL})\n"
                f"📖 **Guide :** [GitBook]({GUIDE_GITBOOK_URL})"
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
            embed.add_field(name="Dernières clés distribuées", value="\n".join(lines), inline=False)

        embed.set_footer(text="Core Market • Gestion des stocks")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="trial_add_keys",
        description="Ajouter de nouvelles clés d'essai au stock disponible",
    )
    @app_commands.describe(
        cles="Clés à ajouter (séparées par des retours à la ligne ou des espaces/virgules)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def trial_add_keys(self, interaction: discord.Interaction, cles: str) -> None:
        # Split by newlines, spaces, or commas
        import re
        raw_keys = re.split(r"[\n,\s]+", cles.strip())
        new_keys = [k.strip() for k in raw_keys if k.strip()]

        if not new_keys:
            await interaction.response.send_message("⚠️ Aucune clé valide fournie.", ephemeral=True)
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
            f"✅ **{added_count}** nouvelle(s) clé(s) ajoutée(s) au stock ! (Total disponible : `{len(available)}`)",
            ephemeral=True,
        )

    @app_commands.command(
        name="trial_reset_user",
        description="Réinitialiser le statut d'un membre pour lui permettre de réclamer une clé à nouveau",
    )
    @app_commands.describe(
        membre="Membre à réinitialiser",
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
                f"✅ Statut réinitialisé pour {membre.mention} ! Le membre peut réclamer une nouvelle clé.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ {membre.mention} n'a aucune clé enregistrée dans l'historique.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Trial(bot))
