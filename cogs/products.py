"""Products Cog — formatted sales embeds with persistent "Buy Here" / "Acheter ici" buttons.
Zero-database design: product key, staff role ID, and logs channel ID are encoded
in the button custom_id (e.g., buy_product:unlockall_fr:123456789:987654321).
"""

from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

PRODUCTS: dict[str, dict[str, Any]] = {
    "unlockall": {
        "raw_title": "UNLOCK ALL (SKIN CHANGER) [EN]",
        "title": "🟣 UNLOCK ALL (SKIN CHANGER) 🟣",
        "description": "*Weapon skin customizer*",
        "button_label": "Buy Here",
        "color": discord.Color.from_str("#8E44AD"),
        "fields": [
            (
                "🌐 System & Compatibility",
                "• **OS:** Windows 10 & 11 (All Versions)\n"
                "• **Client-Side Rendering:** Invisible to viewers/spectators\n"
                "• **Anti-Cheat:** Vanguard",
                False,
            ),
            (
                "⚙️ Unlocker & Cosmetics",
                "• **Unlock All Cosmetics:** Unlock weapon skins, buddies, cards visually\n"
                "• **Skin Changer:** Customize skins with auto-apply features\n"
                "• **Buddy Changer:** Customize buddies with auto-apply features\n"
                "• **Custom Buddy Selection:** Select any buddy from dropdown list\n"
                "• **Finisher Unlock:** Swap and trigger finisher animations",
                False,
            ),
            (
                "💳 Pricing Plan",
                "• **1 Day:** 7.50 €\n"
                "• **1 Week:** 20.00 €\n"
                "• **1 Month:** 40.00 €\n"
                "• **Lifetime:** 100.00 €",
                False,
            ),
        ],
    },
    "unlockall_fr": {
        "raw_title": "UNLOCK ALL (SKIN CHANGER) [FR]",
        "title": "🟣 UNLOCK ALL (SKIN CHANGER) 🟣",
        "description": "*Personnalisateur de skins d'armes*",
        "button_label": "Acheter ici",
        "color": discord.Color.from_str("#8E44AD"),
        "fields": [
            (
                "🌐 Système & Compatibilité",
                "• **OS :** Windows 10 & 11 (Toutes les versions)\n"
                "• **Rendu Côté Client :** Invisible pour les spectateurs et streamers\n"
                "• **Anti-Cheat :** Vanguard",
                False,
            ),
            (
                "⚙️ Déverrouillage & Cosmétiques",
                "• **Déverrouiller tous les cosmétiques :** Débloquez visuellement les skins d'armes, porte-bonheur et cartes\n"
                "• **Changer de skin :** Personnalisez vos skins avec application automatique\n"
                "• **Changer de porte-bonheur :** Personnalisez vos porte-bonheur avec application automatique\n"
                "• **Sélection personnalisée :** Choisissez n'importe quel porte-bonheur dans la liste déroulante\n"
                "• **Déverrouillage des Finishers :** Échangez et déclenchez les animations de finisher",
                False,
            ),
            (
                "💳 Tarifs",
                "• **1 Jour :** 7.50 €\n"
                "• **1 Semaine :** 20.00 €\n"
                "• **1 Mois :** 40.00 €\n"
                "• **À vie (Lifetime) :** 100.00 €",
                False,
            ),
        ],
    },
    "colorbot": {
        "raw_title": "COLORBOT PRIVATE [EN]",
        "title": "🟡 COLORBOT PRIVATE 🟡",
        "description": "*Private pipeline · Web-only access · Built for discretion*",
        "button_label": "Buy Here",
        "color": discord.Color.from_str("#F1C40F"),
        "fields": [
            (
                "🌐 SYSTEM & COMPATIBILITY",
                "• **OS:** Windows 10 & 11 (Home & Pro, All Versions)\n"
                "• **Hardware:** Supports all CPU & GPU components\n"
                "• **HVCI Mode:** Compatible with HVCI On/Off\n"
                "• **Anti-Cheat:** Vanguard",
                False,
            ),
            (
                "🎯 AIMBOT FEATURES",
                "• **Aim Bot & Aim Assist**\n"
                "• **Silent Aim & Flickbot**\n"
                "• **Trigger Bot (Auto-fire)**\n"
                "• **Target Colors:** Yellow, Purple",
                False,
            ),
            (
                "🛠️ ADJUSTABLE SETTINGS",
                "• **FOV:** (Field of View Size)\n"
                "• **Smoothness:** (Fluidity Speed)\n"
                "• **Speed**\n"
                "• **Offset**",
                False,
            ),
            (
                "📦 UTILITIES & DELIVERIES",
                "• **Config Save & Load**\n"
                "• **Custom Keybinds**\n"
                "• **Panic Key**\n"
                "• **Web-based session:** (nothing written to disk)\n"
                "• **Isolated private delivery channel**\n"
                "• **AI-assisted targeting & color logic**\n"
                "• **Minimal host footprint**\n"
                "• **Continuous integrity monitoring & updates**",
                False,
            ),
            (
                "💳 PRICING PLAN",
                "• **1 Day:** 7.00 €\n"
                "• **1 Week:** 20.00 €\n"
                "• **1 Month:** 40.00 €\n"
                "• **Lifetime:** 75.00 €",
                False,
            ),
        ],
    },
    "colorbot_fr": {
        "raw_title": "COLORBOT PRIVATE [FR]",
        "title": "🟡 COLORBOT PRIVATE 🟡",
        "description": "*Pipeline privé · Accès Web uniquement · Conçu pour la discrétion*",
        "button_label": "Acheter ici",
        "color": discord.Color.from_str("#F1C40F"),
        "fields": [
            (
                "🌐 SYSTÈME & COMPATIBILITÉ",
                "• **OS :** Windows 10 & 11 (Home & Pro, toutes versions)\n"
                "• **Composants :** Supporte tous les processeurs CPU & cartes GPU\n"
                "• **Mode HVCI :** Compatible avec HVCI Activé/Désactivé\n"
                "• **Anti-Cheat :** Vanguard",
                False,
            ),
            (
                "🎯 FONCTIONNALITÉS AIMBOT",
                "• **Aim Bot & Aim Assist**\n"
                "• **Silent Aim & Flickbot**\n"
                "• **Trigger Bot (Tir automatique)**\n"
                "• **Couleurs cibles :** Jaune, Violet",
                False,
            ),
            (
                "🛠️ RÉGLAGES AJUSTABLES",
                "• **FOV :** (Taille du champ de vision)\n"
                "• **Smoothness :** (Vitesse de fluidité)\n"
                "• **Vitesse (Speed)**\n"
                "• **Décalage (Offset)**",
                False,
            ),
            (
                "📦 UTILITAIRES & LIVRAISON",
                "• **Sauvegarde & Chargement de la configuration**\n"
                "• **Raccourcis personnalisés (Keybinds)**\n"
                "• **Touche d'urgence (Panic Key)**\n"
                "• **Session basée sur le Web :** (Rien n'est écrit sur le disque)\n"
                "• **Salon de livraison privé et isolé**\n"
                "• **Ciblage assisté par IA & logique des couleurs**\n"
                "• **Empreinte minimale sur le système**\n"
                "• **Surveillance continue de l'intégrité & mises à jour**",
                False,
            ),
            (
                "💳 TARIFS",
                "• **1 Jour :** 7.00 €\n"
                "• **1 Semaine :** 20.00 €\n"
                "• **1 Mois :** 40.00 €\n"
                "• **À vie (Lifetime) :** 75.00 €",
                False,
            ),
        ],
    },
    "mcore_fr": {
        "raw_title": "M-CORE EXTERNAL BO7 / WARZONE [FR]",
        "title": "🔴 M-CORE EXTERNAL BO7 / WARZONE 🔴",
        "description": "*Solution externe premium pour Black Ops 7 & Warzone*",
        "button_label": "Acheter ici",
        "color": discord.Color.from_str("#E74C3C"),
        "fields": [
            (
                "💻 INFORMATIONS & COMPATIBILITÉ",
                "• **OS :** Windows 10 & 11 (Toutes versions, compatible 25H2 ✅)\n"
                "• **Plateforme :** BattleNet, Steam, Activision, Xbox / PC GamePass\n"
                "• **Bypass OBS :** Oui (Streamproof)\n"
                "• **Manette :** 100% Compatible avec manette 🎮",
                False,
            ),
            (
                "🎯 AIMBOT",
                "• **Visée :** Activer/Désactiver le verrouillage de cible\n"
                "• **Os ciblés :** Casque, Tête, Cou, Poitrine, Bassin, Aléatoire\n"
                "• **Réglages :** Fluidité (Smooth), Contrôle du recul, Prédiction de trajectoire\n"
                "• **Filtres :** Ennemis uniquement, Vérification visuelle, Visée collante, Saut à terre / réanimation\n"
                "• **Ciblage Intelligent :** Sélection par distance, FOV ou Smart",
                False,
            ),
            (
                "👁 ESP & VISUELS",
                "• **Boîtes ESP :** 2D, 3D, Angles, Remplies\n"
                "• **Joueurs :** Squelette, Barre de santé, Distance, Noms, ID Équipe, Bulle ESP\n"
                "• **Radar & Drone :** Radar 2D, Drone avancé (Point / Directionnel), Boussole ESP\n"
                "• **Avertissements & Traçage :** Avertissement de visée ennemie, Traceurs de balles\n"
                "• **Butin & Items :** Munitions, Armes, Argent, Plaques de blindage, Caches d'approvisionnement",
                False,
            ),
            (
                "⚙️ PARAMÈTRES & MISC",
                "• **FOV :** FOV Changer & Dynamic FOV\n"
                "• **Configurations :** Sauvegarder, Charger et Créer des profils",
                False,
            ),
            (
                "💳 TARIFS",
                "• **24 Heures :** 5.99 €\n"
                "• **1 Semaine :** 15.99 €\n"
                "• **30 Jours :** 35.99 €",
                False,
            ),
        ],
    },
    "mcore": {
        "raw_title": "M-CORE EXTERNAL BO7 / WARZONE [EN]",
        "title": "🔴 M-CORE EXTERNAL BO7 / WARZONE 🔴",
        "description": "*Premium External Tool for Black Ops 7 & Warzone*",
        "button_label": "Buy Here",
        "color": discord.Color.from_str("#E74C3C"),
        "fields": [
            (
                "💻 INFORMATION & COMPATIBILITY",
                "• **OS:** Windows 10 & 11 (All versions, 25H2 ready ✅)\n"
                "• **Platform:** BattleNet, Steam, Activision, Xbox / PC GamePass\n"
                "• **OBS Bypass:** Yes (Streamproof)\n"
                "• **Controller:** 100% Controller Compatible 🎮",
                False,
            ),
            (
                "🎯 AIMBOT",
                "• **Aimbot:** Enable/Disable target lock\n"
                "• **Hitbox:** Head, Helmet, Neck, Chest, Pelvis, Any\n"
                "• **Settings:** Smoothness slider, Recoil control, Motion prediction\n"
                "• **Filters:** Enemies only, Visible check, Sticky aim, Downed/Reviving targets\n"
                "• **Smart Targeting:** Closest by Smart / FOV / Distance",
                False,
            ),
            (
                "👁 ESP & VISUALS",
                "• **ESP Boxes:** 2D, 3D, Corner, Filled 2D/3D\n"
                "• **Player ESP:** Skeleton, Health Bar, Distance, Names, Team ID, Snaplines\n"
                "• **Radar & UAV:** 2D Radar, Advanced UAV, Compass ESP\n"
                "• **Alerts & Tracers:** Aim warnings, Bullet tracers\n"
                "• **Loot ESP:** Ammo, Weapons, Cash, Armor plates, Supply boxes",
                False,
            ),
            (
                "⚙️ SETTINGS & MISC",
                "• **FOV:** FOV Changer & Dynamic FOV\n"
                "• **Configs:** Save, Load, and Create custom profiles",
                False,
            ),
            (
                "💳 PRICING PLAN",
                "• **24 Hours:** 5.99 €\n"
                "• **1 Week:** 15.99 €\n"
                "• **30 Days:** 35.99 €",
                False,
            ),
        ],
    },
    "spectre_fr": {
        "raw_title": "TRINITY SPECTRE BO7 / WARZONE [FR]",
        "title": "🔮 TRINITY SPECTRE BO7 / WARZONE 🔮",
        "description": "*Solution externe indétectable pour Call of Duty*",
        "button_label": "Acheter ici",
        "color": discord.Color.from_str("#9B59B6"),
        "fields": [
            (
                "💻 INFORMATIONS & COMPATIBILITÉ",
                "• **OS :** Windows 10 & 11 (Supporté jusqu'à 25H2)\n"
                "• **Processeur :** Intel & AMD\n"
                "• **Cartes Graphiques :** Tous composants\n"
                "• **Manette :** Compatible PS / Xbox / PC 🎮\n"
                "• **Type :** Externe (Indétectable)\n"
                "• **Bypass Stream :** Cachez le sur OBS, Medal, Discord, Streamlabs",
                False,
            ),
            (
                "🏆 FONCTIONNALITÉS",
                "• **Aimbot :** Prédiction de visée, Choix de l'os (Aim Bone), Visée humanisée\n"
                "• **ESP & Visuels :** ESP Joueurs, Zombies, Radar 2D & Boussole\n"
                "• **Stats :** Stats du lobby & plus encore",
                False,
            ),
            (
                "🎮 PLATEFORMES & ANTI-CHEAT",
                "• **Plateformes :** Steam (Conseillé), BattleNet, Xbox Gamepass\n"
                "• **Anti-Cheat :** Ricochet (Contourné / Externe au jeu)",
                False,
            ),
            (
                "💳 TARIFS",
                "• **24 Heures :** 7.99 €\n"
                "• **1 Semaine :** 21.99 €\n"
                "• **1 Mois :** 44.99 €\n"
                "• **À Vie (Lifetime) :** 119.99 €",
                False,
            ),
        ],
    },
    "spectre": {
        "raw_title": "TRINITY SPECTRE BO7 / WARZONE [EN]",
        "title": "🔮 TRINITY SPECTRE BO7 / WARZONE 🔮",
        "description": "*Undetectable external tool for Call of Duty*",
        "button_label": "Buy Here",
        "color": discord.Color.from_str("#9B59B6"),
        "fields": [
            (
                "💻 INFORMATION & COMPATIBILITY",
                "• **OS:** Windows 10 & 11 (Supported up to 25H2)\n"
                "• **CPU:** Intel & AMD Supported\n"
                "• **GPU:** All Components Supported\n"
                "• **Controller:** PS / Xbox / PC Compatible 🎮\n"
                "• **Type:** External (Undetectable)\n"
                "• **Streamproof:** Hide on OBS, Medal, Discord, Streamlabs",
                False,
            ),
            (
                "🏆 FEATURES",
                "• **Aimbot:** Aim prediction, Aim Bone selection, Humanized aim\n"
                "• **ESP & Visuals:** Player ESP, Zombies, 2D Radar & Compass\n"
                "• **Stats:** Lobby stats & more",
                False,
            ),
            (
                "🎮 PLATFORMS & ANTI-CHEAT",
                "• **Platforms:** Steam (Recommended), BattleNet, Xbox Gamepass\n"
                "• **Anti-Cheat:** Ricochet (Bypassed / External)",
                False,
            ),
            (
                "💳 PRICING PLAN",
                "• **24 Hours:** 7.99 €\n"
                "• **1 Week:** 21.99 €\n"
                "• **1 Month:** 44.99 €\n"
                "• **Lifetime:** 119.99 €",
                False,
            ),
        ],
    },
    "pulse_internal_fr": {
        "raw_title": "TRINITY PULSE VALORANT [FR]",
        "title": "⚡ TRINITY PULSE VALORANT ⚡",
        "description": "*Solution interne haute performance avec émulateur sans redémarrage*",
        "button_label": "Acheter ici",
        "color": discord.Color.from_str("#3498DB"),
        "fields": [
            (
                "💻 INFORMATIONS & COMPATIBILITÉ",
                "• **OS :** Windows 10 & 11 (Toutes versions)\n"
                "• **Processeur :** Intel & AMD\n"
                "• **Cartes Graphiques :** Tous composants\n"
                "• **Cartes Mères :** Compatible ASUS & Toutes cartes mères\n"
                "• **Émulateur :** Émulateur No-Restart intégré 🌌",
                False,
            ),
            (
                "🏆 FONCTIONNALITÉS",
                "• **Aimbot :** Visée automatique ultra fluide & FOV ajustable\n"
                "• **ESP & Chams :** ESP Joueurs, Squelette, Santé, Chams visuels\n"
                "• **Unlock All & Models :** Déblocage des cosmétiques, modèles & skins personnalisés\n"
                "• **Exploits & Anti-Aim :** Anti-Aim sur mesure & Exploits personnalisés\n"
                "• **Système de Config :** Sauvegarde & chargement de profils sur mesure",
                False,
            ),
            (
                "💳 TARIFS",
                "• **3 Jours :** 11.99 €\n"
                "• **7 Jours :** 24.99 €\n"
                "• **30 Jours :** 39.99 €\n"
                "• **À Vie (Lifetime) :** 109.99 €",
                False,
            ),
        ],
    },
    "pulse_internal": {
        "raw_title": "TRINITY PULSE VALORANT [EN]",
        "title": "⚡ TRINITY PULSE VALORANT ⚡",
        "description": "*High performance internal tool with built-in no-restart emulator*",
        "button_label": "Buy Here",
        "color": discord.Color.from_str("#3498DB"),
        "fields": [
            (
                "💻 INFORMATION & COMPATIBILITY",
                "• **OS:** Windows 10 & 11 (All versions)\n"
                "• **CPU:** Intel & AMD Supported\n"
                "• **GPU:** All Components Supported\n"
                "• **Motherboards:** Works on ASUS & All motherboards\n"
                "• **Emulator:** Built-in No-Restart Emulator included 🌌",
                False,
            ),
            (
                "🏆 FEATURES",
                "• **Aimbot:** Smooth aimbot & FOV adjustments\n"
                "• **ESP & Chams:** Player ESP, Skeleton, Health, Visual Chams\n"
                "• **Unlock All & Models:** Cosmetics unlock, Custom Models & Skins\n"
                "• **Exploits & Anti-Aim:** Custom Anti-Aim & Custom Exploits\n"
                "• **Config System:** Save & load custom profiles",
                False,
            ),
            (
                "💳 PRICING PLAN",
                "• **3 Days:** 11.99 €\n"
                "• **7 Days:** 24.99 €\n"
                "• **30 Days:** 39.99 €\n"
                "• **Lifetime:** 109.99 €",
                False,
            ),
        ],
    },
}


def build_product_embed(product_key: str) -> discord.Embed | None:
    data = PRODUCTS.get(product_key)
    if not data:
        return None

    embed = discord.Embed(
        title=data["title"],
        description=data["description"],
        color=data["color"],
    )
    for name, value, inline in data["fields"]:
        embed.add_field(name=name, value=value, inline=inline)

    return embed


class BuyProductButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"buy_product:(?P<product>[^:]+):(?P<staff>\d+):(?P<logs>\d+)",
):
    """Dynamic button attached to product embeds.
    Clicking it opens a ticket configured for that specific product.
    """

    def __init__(
        self,
        product_key: str,
        staff_role_id: int,
        logs_channel_id: int,
        button_label: str | None = None,
    ) -> None:
        label = button_label or PRODUCTS.get(product_key, {}).get("button_label", "Buy Here / Acheter ici")
        super().__init__(
            discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary,
                emoji="🛒",
                custom_id=f"buy_product:{product_key}:{staff_role_id}:{logs_channel_id}",
            )
        )
        self.product_key = product_key
        self.staff_role_id = staff_role_id
        self.logs_channel_id = logs_channel_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: Any, /):
        return cls(match["product"], int(match["staff"]), int(match["logs"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        from cogs.tickets import create_ticket

        await create_ticket(
            interaction,
            ticket_type="buy",
            staff_role_id=self.staff_role_id,
            logs_channel_id=self.logs_channel_id,
            product_key=self.product_key,
        )


def build_product_view(
    product_key: str, staff_role_id: int, logs_channel_id: int
) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(BuyProductButton(product_key, staff_role_id, logs_channel_id))
    return view


class Products(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(BuyProductButton)

    async def _send_product_panel(
        self,
        interaction: discord.Interaction,
        product_key: str,
        role_staff: discord.Role | None,
        salon_logs: discord.TextChannel | None,
    ) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "⚠️ Cette commande doit être exécutée dans un salon de serveur.", ephemeral=True
            )
            return

        staff_role = (
            role_staff
            or discord.utils.get(guild.roles, name="Staff")
            or discord.utils.get(guild.roles, name="Owner")
            or guild.default_role
        )
        logs_channel = (
            salon_logs
            or discord.utils.get(guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ")
            or discord.utils.get(guild.text_channels, name="📜・logs-tickets")
            or discord.utils.get(guild.text_channels, name="📜 ┃ 𝖑𝖔𝖌𝖘-𝖙𝖎𝖈𝖐𝖊𝖙𝖘")
            or discord.utils.get(guild.text_channels, name="logs")
            or interaction.channel
        )

        embed = build_product_embed(product_key)
        if embed is None:
            await interaction.response.send_message(
                f"⚠️ Produit `{product_key}` introuvable.", ephemeral=True
            )
            return

        view = build_product_view(product_key, staff_role.id, logs_channel.id)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ Panel **{PRODUCTS[product_key]['raw_title']}** posté ! (Staff: {staff_role.mention}, Logs: {logs_channel.mention})",
            ephemeral=True,
        )

    @app_commands.command(
        name="setup_unlockall",
        description="Poster le message de vente UNLOCK ALL avec bouton d'achat",
    )
    @app_commands.describe(
        langue="Langue de l'embed (français ou anglais)",
        role_staff="Rôle staff ayant accès au ticket (optionnel)",
        salon_logs="Salon des logs/transcripts (optionnel)",
    )
    @app_commands.choices(
        langue=[
            app_commands.Choice(name="Français 🇫🇷", value="fr"),
            app_commands.Choice(name="English 🇬🇧", value="en"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_unlockall(
        self,
        interaction: discord.Interaction,
        langue: app_commands.Choice[str] | None = None,
        role_staff: discord.Role | None = None,
        salon_logs: discord.TextChannel | None = None,
    ) -> None:
        lang = langue.value if langue else "fr"
        key = "unlockall_fr" if lang == "fr" else "unlockall"
        await self._send_product_panel(interaction, key, role_staff, salon_logs)

    @app_commands.command(
        name="setup_colorbot",
        description="Poster le message de vente COLORBOT avec bouton d'achat",
    )
    @app_commands.describe(
        langue="Langue de l'embed (français ou anglais)",
        role_staff="Rôle staff ayant accès au ticket (optionnel)",
        salon_logs="Salon des logs/transcripts (optionnel)",
    )
    @app_commands.choices(
        langue=[
            app_commands.Choice(name="Français 🇫🇷", value="fr"),
            app_commands.Choice(name="English 🇬🇧", value="en"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_colorbot(
        self,
        interaction: discord.Interaction,
        langue: app_commands.Choice[str] | None = None,
        role_staff: discord.Role | None = None,
        salon_logs: discord.TextChannel | None = None,
    ) -> None:
        lang = langue.value if langue else "fr"
        key = "colorbot_fr" if lang == "fr" else "colorbot"
        await self._send_product_panel(interaction, key, role_staff, salon_logs)

    @app_commands.command(
        name="setup_mcore",
        description="Poster le message de vente M-CORE BO7 / WARZONE avec bouton d'achat",
    )
    @app_commands.describe(
        langue="Langue de l'embed (français ou anglais)",
        role_staff="Rôle staff ayant accès au ticket (optionnel)",
        salon_logs="Salon des logs/transcripts (optionnel)",
    )
    @app_commands.choices(
        langue=[
            app_commands.Choice(name="Français 🇫🇷", value="fr"),
            app_commands.Choice(name="English 🇬🇧", value="en"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_mcore(
        self,
        interaction: discord.Interaction,
        langue: app_commands.Choice[str] | None = None,
        role_staff: discord.Role | None = None,
        salon_logs: discord.TextChannel | None = None,
    ) -> None:
        lang = langue.value if langue else "fr"
        key = "mcore_fr" if lang == "fr" else "mcore"
        await self._send_product_panel(interaction, key, role_staff, salon_logs)

    @app_commands.command(
        name="setup_spectre",
        description="Poster le message de vente TRINITY SPECTRE BO7 / WARZONE avec bouton d'achat",
    )
    @app_commands.describe(
        langue="Langue de l'embed (français ou anglais)",
        role_staff="Rôle staff ayant accès au ticket (optionnel)",
        salon_logs="Salon des logs/transcripts (optionnel)",
    )
    @app_commands.choices(
        langue=[
            app_commands.Choice(name="Français 🇫🇷", value="fr"),
            app_commands.Choice(name="English 🇬🇧", value="en"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_spectre(
        self,
        interaction: discord.Interaction,
        langue: app_commands.Choice[str] | None = None,
        role_staff: discord.Role | None = None,
        salon_logs: discord.TextChannel | None = None,
    ) -> None:
        lang = langue.value if langue else "fr"
        key = "spectre_fr" if lang == "fr" else "spectre"
        await self._send_product_panel(interaction, key, role_staff, salon_logs)

    @app_commands.command(
        name="setup_product",
        description="Poster le message de vente d'un produit spécifique",
    )
    @app_commands.describe(
        produit="Identifiant et langue du produit à afficher",
        role_staff="Rôle staff ayant accès au ticket (optionnel)",
        salon_logs="Salon des logs/transcripts (optionnel)",
    )
    @app_commands.choices(
        produit=[
            app_commands.Choice(name="🟣 UNLOCK ALL (FR 🇫🇷)", value="unlockall_fr"),
            app_commands.Choice(name="🟣 UNLOCK ALL (EN 🇬🇧)", value="unlockall"),
            app_commands.Choice(name="🟡 COLORBOT PRIVATE (FR 🇫🇷)", value="colorbot_fr"),
            app_commands.Choice(name="🟡 COLORBOT PRIVATE (EN 🇬🇧)", value="colorbot"),
            app_commands.Choice(name="🔴 M-CORE BO7/WARZONE (FR 🇫🇷)", value="mcore_fr"),
            app_commands.Choice(name="🔴 M-CORE BO7/WARZONE (EN 🇬🇧)", value="mcore"),
            app_commands.Choice(name="🔮 TRINITY SPECTRE BO7/WARZONE (FR 🇫🇷)", value="spectre_fr"),
            app_commands.Choice(name="🔮 TRINITY SPECTRE BO7/WARZONE (EN 🇬🇧)", value="spectre"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_product(
        self,
        interaction: discord.Interaction,
        produit: app_commands.Choice[str],
        role_staff: discord.Role | None = None,
        salon_logs: discord.TextChannel | None = None,
    ) -> None:
        await self._send_product_panel(interaction, produit.value, role_staff, salon_logs)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Products(bot))
