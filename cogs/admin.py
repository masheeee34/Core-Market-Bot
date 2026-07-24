"""Admin commands: /setup (roles + channels) and /panel (ticket panel)."""

import discord
from discord import app_commands
from discord.ext import commands

from cogs.tickets import build_panel_view

# Roles created by /setup — names STRICTLY in English, do not translate.
# One spec per role, iterated in a loop: (name, colour, permissions).
ROLE_SPECS: list[tuple[str, discord.Colour, discord.Permissions]] = [
    (
        "Owner",
        discord.Colour.dark_red(),
        discord.Permissions(administrator=True),
    ),
    (
        "Staff",
        discord.Colour.from_str("#0070FF"),  # bleu électrique
        discord.Permissions(
            manage_messages=True, kick_members=True, ban_members=True, manage_channels=True
        ),
    ),
    (
        "Helper",
        discord.Colour.from_str("#2ECC71"),  # vert émeraude
        discord.Permissions(manage_messages=True, kick_members=True),
    ),
    (
        "Content Creator",
        discord.Colour.purple(),
        discord.Permissions.none(),
    ),
    (
        "Customer",
        discord.Colour.gold(),
        discord.Permissions.none(),
    ),
]


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="setup",
        description="Créer automatiquement les rôles, #vouches et #rules",
    )
    @app_commands.describe(categorie_rules="Catégorie où placer le salon #rules")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_server(
        self,
        interaction: discord.Interaction,
        categorie_rules: discord.CategoryChannel,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        report: list[str] = []

        # 1) Roles (only created if missing) — one loop, colour + permissions per spec.
        for name, colour, permissions in ROLE_SPECS:
            if discord.utils.get(guild.roles, name=name) is None:
                await guild.create_role(
                    name=name,
                    colour=colour,
                    permissions=permissions,
                    hoist=True,
                    mentionable=True,
                    reason="/setup — base role",
                )
                report.append(f"Rôle créé : **{name}**")
            else:
                report.append(f"Rôle déjà présent : **{name}**")

        # 2) #vouches: read-only for members — vouches are posted by the bot via /vouch.
        vouches = discord.utils.get(guild.text_channels, name="vouches")
        if vouches is None:
            staff = discord.utils.get(guild.roles, name="Staff")
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(send_messages=False),
                staff: discord.PermissionOverwrite(manage_messages=True),
                guild.me: discord.PermissionOverwrite(send_messages=True),
            }
            vouches = await guild.create_text_channel(
                "vouches",
                overwrites=overwrites,
                topic="Click the Vouch button to leave a review after your purchase.",
                reason="/setup",
            )
            from cogs.vouch import VouchButtonView

            await vouches.send(
                content="**Leave a review after your purchase!**",
                view=VouchButtonView(),
            )
            report.append(f"Salon créé : {vouches.mention} (bouton Vouch posté)")
        else:
            report.append(f"Salon déjà présent : {vouches.mention}")

        # 3) #rules in the given category, read-only, left empty (write your own rules).
        rules = discord.utils.get(guild.text_channels, name="rules")
        if rules is None:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    send_messages=False, add_reactions=False
                ),
                guild.me: discord.PermissionOverwrite(send_messages=True),
            }
            rules = await categorie_rules.create_text_channel(
                "rules", overwrites=overwrites, reason="/setup"
            )
            report.append(f"Salon créé : {rules.mention} (vide, à toi d'y écrire tes règles)")
        else:
            report.append(f"Salon déjà présent : {rules.mention}")

        embed = discord.Embed(
            title="Setup terminé",
            color=discord.Color.green(),
            description="\n".join(report),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="panel",
        description="Poster le panel de tickets (menu déroulant) dans ce salon",
    )
    @app_commands.describe(
        role_staff="Rôle ayant accès aux tickets",
        salon_logs="Salon où les transcripts seront envoyés",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def panel(
        self,
        interaction: discord.Interaction,
        role_staff: discord.Role,
        salon_logs: discord.TextChannel,
    ) -> None:
        # Minimal panel: one line + the select menu. Config lives in the select's
        # custom_id (invisible) — no database. Tickets are routed per category.
        await interaction.channel.send(
            content="**Create a ticket**",
            view=build_panel_view(role_staff.id, salon_logs.id),
        )
        await interaction.response.send_message(
            f"✅ Panel posté — staff {role_staff.mention}, logs dans {salon_logs.mention}. "
            f"Les tickets sont rangés automatiquement par catégorie (Order, Support, Media, Reseller).",
            ephemeral=True,
        )


    @app_commands.command(
        name="delete",
        description="Supprimer une catégorie entière (avec tous ses salons) ou un salon précis",
    )
    @app_commands.describe(
        categorie="Catégorie à supprimer entièrement (salons inclus)",
        salon="Salon individuel à supprimer",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def delete_cmd(
        self,
        interaction: discord.Interaction,
        categorie: discord.CategoryChannel | None = None,
        salon: discord.abc.GuildChannel | None = None,
    ) -> None:
        if categorie is None and salon is None:
            await interaction.response.send_message(
                "⚠️ Précise au moins une **categorie** ou un **salon** à supprimer.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted: list[str] = []

        if categorie is not None:
            for ch in list(categorie.channels):
                await ch.delete(reason=f"/delete by {interaction.user}")
                deleted.append(f"#{ch.name}")
            await categorie.delete(reason=f"/delete by {interaction.user}")
            deleted.insert(0, f"📁 **{categorie.name}** (catégorie)")

        if salon is not None:
            await salon.delete(reason=f"/delete by {interaction.user}")
            deleted.append(f"#{salon.name}")

        await interaction.followup.send(
            f"🗑️ Supprimé :\n" + "\n".join(f"- {d}" for d in deleted),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
