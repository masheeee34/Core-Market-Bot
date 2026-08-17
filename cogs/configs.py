import json
import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("cogs.configs")

CONFIG_PRESETS: dict[str, dict[str, Any]] = {
    "spectre": {
        "name": "TRINITY SPECTRE (BO7 / WARZONE)",
        "color": "#9B59B6",
        "legit": {
            "title": "🛡️ CONFIGURATION LEGIT / STREAMPROOF (RANKED & TOURNAMENTS)",
            "aim_fov": "3.5° (Cercle discret)",
            "aim_smooth": "18.0 (Lissage naturel ultra-humain)",
            "aim_bone": "Neck / Upper Chest (Évite le lock 100% tête suspect)",
            "recoil_control": "75% (Maintien de recul réaliste)",
            "esp_mode": "Corner Box + Player Health + Distance (< 150m)",
            "streamproof": "ENABLED (Totalement invisible sur OBS / Discord Screen)",
            "humanizer": "Dynamic Delay + Target Switching Safety (35ms)",
            "advice": "Idéal pour grind les Top 250 sans attirer l'attention des spectateurs ou rapports manuels.",
        },
        "semi_rage": {
            "title": "⚡ CONFIGURATION SEMI-RAGE (FAST FLICK & CLOSE RANGE)",
            "aim_fov": "7.0° (Large capture)",
            "aim_smooth": "7.5 (Visée vive et réactive)",
            "aim_bone": "Head / Neck Prioritized",
            "recoil_control": "95% (Laser beam)",
            "esp_mode": "Full 3D Box + Skeleton + 2D Radar + Armor info",
            "streamproof": "ENABLED",
            "humanizer": "Silent Aim assist + Instant Swap",
            "advice": "Permet de carry facilement vos parties en solo sans hésitation au corps à corps.",
        },
        "rage": {
            "title": "🔥 CONFIGURATION FULL RAGE (MAXIMUM LOCK & MULTI-KILL)",
            "aim_fov": "360° (Capture globale)",
            "aim_smooth": "1.0 (Instant Snap / No delay)",
            "aim_bone": "Head only (100% Headshots)",
            "recoil_control": "100% (No Recoil / No Spread)",
            "esp_mode": "Full ESP + Snaplines + Item Loot + Grenade Warning",
            "streamproof": "DISABLED",
            "humanizer": "OFF",
            "advice": "Domination totale de lobby. Utilisez de préférence sur des comptes secondaires ou avec Spoofer actif.",
        },
    },
    "mcore": {
        "name": "M-CORE EXTERNAL (BO7 / WARZONE)",
        "color": "#00FF66",
        "legit": {
            "title": "🛡️ CONFIGURATION LEGIT / STREAMPROOF (OVERLAY PUR)",
            "aim_fov": "4.0°",
            "aim_smooth": "15.0",
            "aim_bone": "Chest / Body Center",
            "recoil_control": "80%",
            "esp_mode": "2D Box + Skeleton + Distance (< 120m)",
            "streamproof": "ENABLED",
            "humanizer": "Bezier Curve smoothing",
            "advice": "Simulation parfaite du mouvement souris pour un rendu 100% legit en killcam.",
        },
        "semi_rage": {
            "title": "⚡ CONFIGURATION SEMI-RAGE (DOMINATION EQUILIBREE)",
            "aim_fov": "8.5°",
            "aim_smooth": "6.0",
            "aim_bone": "Upper Chest / Head",
            "recoil_control": "90%",
            "esp_mode": "Skeleton + Head Dot + Radar",
            "streamproof": "ENABLED",
            "humanizer": "Linear acceleration",
            "advice": "Maximise votre kill/death ratio tout en gardant une killcam propre.",
        },
        "rage": {
            "title": "🔥 CONFIGURATION FULL RAGE (LOCK TOTAL)",
            "aim_fov": "180°",
            "aim_smooth": "1.2",
            "aim_bone": "Head",
            "recoil_control": "100%",
            "esp_mode": "All Visuals Active + Distance 500m",
            "streamproof": "DISABLED",
            "humanizer": "OFF",
            "advice": "Puissance brute sans restriction.",
        },
    },
    "valorant_pulse": {
        "name": "TRINITY PULSE (VALORANT)",
        "color": "#FF4655",
        "legit": {
            "title": "🛡️ CONFIGURATION LEGIT / RADIANT RANKED (VANGUARD SAFE)",
            "aim_fov": "2.8° (Cercle ultra serré sur le viseur)",
            "aim_smooth": "22.0 (Lissage micro-mouvements)",
            "aim_bone": "Head (Micro-ajustement uniquement au tir)",
            "recoil_control": "Standalone RCS + Humanized Burst",
            "esp_mode": "Glow discret + Dormant Check (Invisible en killcam)",
            "streamproof": "ENABLED (Internal Hook Bypass)",
            "humanizer": "RCS Delay 80ms + No-Snap Lock",
            "advice": "Recommandé pour monter Radiant / Immortal sans aucun soupçon de Vanguard ou des coéquipiers.",
        },
        "semi_rage": {
            "title": "⚡ CONFIGURATION SEMI-RAGE (AGRESSIVE DUELIST)",
            "aim_fov": "5.5°",
            "aim_smooth": "10.0",
            "aim_bone": "Head",
            "recoil_control": "Full Auto Recoil Compensation",
            "esp_mode": "Chams + Skeleton + Health Bar",
            "streamproof": "ENABLED",
            "humanizer": "Micro-curve aim",
            "advice": "Excellente pour entry-frag et punir les peeks adverses instantanément.",
        },
        "rage": {
            "title": "🔥 CONFIGURATION RAGE / UNLOCK ALL",
            "aim_fov": "12.0°",
            "aim_smooth": "3.0",
            "aim_bone": "Head",
            "recoil_control": "100%",
            "esp_mode": "Full Chams + Snaplines + Radar + Weapon ESP",
            "streamproof": "DISABLED",
            "humanizer": "OFF",
            "advice": "Pour détruire des lobbies non-classés.",
        },
    },
}


def build_config_embed(product_key: str, style_key: str) -> discord.Embed:
    prod = CONFIG_PRESETS.get(product_key, CONFIG_PRESETS["spectre"])
    style = prod.get(style_key, prod["legit"])

    lines = [
        f"> **Paramètres optimisés par l'équipe technique Core Market pour `{prod['name']}`.**\n\n"
        "```ansi\n"
        "\u001b[1;36m[ 🎯 PARAMÈTRES AIMBOT & RECOIL ]\u001b[0m\n"
        "```\n"
        f"▸ **Aimbot FOV :** `{style['aim_fov']}`\n"
        f"▸ **Smoothing (Lissage) :** `{style['aim_smooth']}`\n"
        f"▸ **Priorité d'Os (Target Bone) :** `{style['aim_bone']}`\n"
        f"▸ **Contrôle du Recul (RCS) :** `{style['recoil_control']}`\n\n"
        "```ansi\n"
        "\u001b[1;32m[ 👁️ VISUELS & ESP ]\u001b[0m\n"
        "```\n"
        f"▸ **Mode ESP :** `{style['esp_mode']}`\n"
        f"▸ **Mode Streamproof (OBS/Discord) :** `{style['streamproof']}`\n"
        f"▸ **Humanizer / Algorithme :** `{style['humanizer']}`\n\n"
        "```ansi\n"
        "\u001b[1;33m[ 💡 CONSEIL PRO DU STAFF ]\u001b[0m\n"
        "```\n"
        f"*{style['advice']}*"
    ]

    embed = discord.Embed(
        title=f"⚙️  {prod['name']} — {style['title']}",
        description="\n".join(lines),
        color=discord.Color.from_str(prod["color"]),
    )
    embed.set_footer(text="CORE MARKET • Configuration Assistant • Streamproof & Ring-0 Protection")
    return embed


class ConfigStyleSelect(discord.ui.Select):
    def __init__(self, product_key: str) -> None:
        self.product_key = product_key
        options = [
            discord.SelectOption(label="Config Legit / Streamproof", value="legit", emoji="🛡️", description="Idéal Ranked / Tournois / Indétectable"),
            discord.SelectOption(label="Config Semi-Rage", value="semi_rage", emoji="⚡", description="Visée vive / Carry Solo"),
            discord.SelectOption(label="Config Full Rage", value="rage", emoji="🔥", description="Lock total / Domination 100%"),
        ]
        super().__init__(placeholder="Choisissez votre style de jeu...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        style_key = self.values[0]
        embed = build_config_embed(self.product_key, style_key)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ConfigProductSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label="Trinity Spectre (BO7 / WZ)", value="spectre", emoji="🔮", description="External Ring-0"),
            discord.SelectOption(label="M-Core External (BO7 / WZ)", value="mcore", emoji="🎯", description="Kernel Overlay"),
            discord.SelectOption(label="Trinity Pulse (Valorant)", value="valorant_pulse", emoji="⚡", description="Internal Vanguard Bypass"),
        ]
        super().__init__(placeholder="Choisissez votre logiciel...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        product_key = self.values[0]
        prod_name = CONFIG_PRESETS[product_key]["name"]

        view = discord.ui.View(timeout=120)
        view.add_item(ConfigStyleSelect(product_key))

        embed = discord.Embed(
            title=f"🎯  SÉLECTION DU STYLE POUR {prod_name}",
            description="> **Sélectionnez le profil de jeu souhaité dans le menu ci-dessous pour afficher les réglages précis.**",
            color=discord.Color.from_str(CONFIG_PRESETS[product_key]["color"]),
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfigsCog(commands.Cog):
    """Aimbot & ESP Configuration Optimizer."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="config", description="Generate optimal Aimbot & ESP configuration presets for your software")
    @app_commands.choices(
        product=[
            app_commands.Choice(name="🔮 Trinity Spectre (BO7 / WZ)", value="spectre"),
            app_commands.Choice(name="🎯 M-Core External (BO7 / WZ)", value="mcore"),
            app_commands.Choice(name="⚡ Trinity Pulse (Valorant)", value="valorant_pulse"),
        ],
        style=[
            app_commands.Choice(name="🛡️ Legit / Streamproof (Ranked & Indétectable)", value="legit"),
            app_commands.Choice(name="⚡ Semi-Rage (Visée vive & Carry)", value="semi_rage"),
            app_commands.Choice(name="🔥 Full Rage (Lock total)", value="rage"),
        ],
    )
    async def config_cmd(self, interaction: discord.Interaction, product: str | None = None, style: str | None = None) -> None:
        if product and style:
            embed = build_config_embed(product, style)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Interactive selection
        view = discord.ui.View(timeout=180)
        view.add_item(ConfigProductSelect())

        embed = discord.Embed(
            title="🎯  GÉNÉRATEUR DE CONFIGURATIONS AIMBOT & ESP",
            description=(
                "> **Bienvenue dans l'assistant de configuration Core Market.**\n"
                "> Choisissez votre logiciel pour obtenir les réglages précis FOV, Smooth, Recoil et Visuels."
            ),
            color=discord.Color.from_str("#0070FF"),
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConfigsCog(bot))
