"""Products Cog — formatted sales embeds with persistent "Buy Here" buttons.
Zero-database design: product key, staff role ID, and logs channel ID are encoded
in the button custom_id (e.g., buy_product:unlockall:123456789:987654321).
"""

from typing import Any

discord = None  # Will be imported
import discord
from discord import app_commands
from discord.ext import commands

PRODUCTS: dict[str, dict[str, Any]] = {
    "unlockall": {
        "raw_title": "UNLOCK ALL (SKIN CHANGER)",
        "title": "🟣 UNLOCK ALL (SKIN CHANGER) 🟣",
        "description": "*Weapon skin customizer*",
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
                "• **1 Day:** $7.5\n"
                "• **1 Week:** $20.00\n"
                "• **1 Month:** $40.00\n"
                "• **Lifetime:** $100",
                False,
            ),
        ],
    },
    "colorbot": {
        "raw_title": "COLORBOT PRIVATE",
        "title": "🟡 COLORBOT PRIVATE 🟡",
        "description": "*Private pipeline · Web-only access · Built for discretion*",
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
                "• **1 Day:** $7.00\n"
                "• **1 Week:** $20.00\n"
                "• **1 Month:** $40.00\n"
                "• **Lifetime:** $75.00",
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
        button_label: str = "Buy Here",
    ) -> None:
        super().__init__(
            discord.ui.Button(
                label=button_label,
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
            or discord.utils.get(guild.text_channels, name="logs")
            or discord.utils.get(guild.text_channels, name="ticket-logs")
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
        description="Poster le message de vente UNLOCK ALL avec bouton Buy Here",
    )
    @app_commands.describe(
        role_staff="Rôle staff ayant accès au ticket (optionnel)",
        salon_logs="Salon des logs/transcripts (optionnel)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_unlockall(
        self,
        interaction: discord.Interaction,
        role_staff: discord.Role | None = None,
        salon_logs: discord.TextChannel | None = None,
    ) -> None:
        await self._send_product_panel(interaction, "unlockall", role_staff, salon_logs)

    @app_commands.command(
        name="setup_colorbot",
        description="Poster le message de vente COLORBOT avec bouton Buy Here",
    )
    @app_commands.describe(
        role_staff="Rôle staff ayant accès au ticket (optionnel)",
        salon_logs="Salon des logs/transcripts (optionnel)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_colorbot(
        self,
        interaction: discord.Interaction,
        role_staff: discord.Role | None = None,
        salon_logs: discord.TextChannel | None = None,
    ) -> None:
        await self._send_product_panel(interaction, "colorbot", role_staff, salon_logs)

    @app_commands.command(
        name="setup_product",
        description="Poster le message de vente d'un produit spécifique",
    )
    @app_commands.describe(
        produit="Identifiant du produit à afficher",
        role_staff="Rôle staff ayant accès au ticket (optionnel)",
        salon_logs="Salon des logs/transcripts (optionnel)",
    )
    @app_commands.choices(
        produit=[
            app_commands.Choice(name="🟣 UNLOCK ALL (SKIN CHANGER)", value="unlockall"),
            app_commands.Choice(name="🟡 COLORBOT PRIVATE", value="colorbot"),
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
