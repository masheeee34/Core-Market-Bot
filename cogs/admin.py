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
    async def panel(
        self,
        interaction: discord.Interaction,
        role_staff: discord.Role,
        salon_logs: discord.TextChannel,
        langue: app_commands.Choice[str] | None = None,
    ) -> None:
        lang = langue.value if langue else "en"
        if langue is None and isinstance(interaction.channel, discord.TextChannel):
            ch = interaction.channel
            cat_name = ch.category.name.lower() if ch.category else ""
            if "fr" in cat_name or "fr" in ch.name.lower():
                lang = "fr"

        content = "**Créer un ticket**" if lang == "fr" else "**Create a ticket**"

        await interaction.channel.send(
            content=content,
            view=build_panel_view(role_staff.id, salon_logs.id, lang=lang),
        )
        await interaction.response.send_message(
            f"✅ Panel posté ({lang.upper()}) — staff {role_staff.mention}, logs dans {salon_logs.mention}.",
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

    @app_commands.command(
        name="setup_core_market",
        description="Générer automatiquement la structure du serveur (design propre et moderne)",
    )
    @app_commands.describe(
        style="Style typographique des salons (Small Caps moderne par défaut ou Simple)",
        supprimer_anciens_salons="Supprimer automatiquement tous les anciens salons et catégories avant de refaire le serveur (Par défaut: Oui)",
    )
    @app_commands.choices(
        style=[
            app_commands.Choice(name="Moderne Small Caps (⚡・ꜱᴘᴏᴏꜰ-ʀᴀɴᴋᴇᴅ)", value="small_caps"),
            app_commands.Choice(name="Clean Simple (⚡・spoof-ranked)", value="clean"),
            app_commands.Choice(name="Gothique (🌌 ┃ 𝕾𝖕𝖔𝖔𝖋-𝕽𝖆𝖓𝖐𝖊𝖉)", value="gothic"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_core_market(
        self,
        interaction: discord.Interaction,
        style: app_commands.Choice[str] | None = None,
        supprimer_anciens_salons: bool = True,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return

        selected_style = style.value if style else "small_caps"
        report: list[str] = []

        # 0. Clean old channels and categories if requested
        if supprimer_anciens_salons:
            report.append("🧹 **Nettoyage des anciens salons et catégories effectué.**")
            for ch in list(guild.channels):
                try:
                    await ch.delete(reason="/setup_core_market — auto clean")
                except Exception:
                    pass

        # 1. Roles setup
        for name, colour, permissions in ROLE_SPECS:
            if discord.utils.get(guild.roles, name=name) is None:
                await guild.create_role(
                    name=name,
                    colour=colour,
                    permissions=permissions,
                    hoist=True,
                    mentionable=True,
                    reason="/setup_core_market — role creation",
                )
                report.append(f"👑 Rôle créé : **{name}**")
            else:
                report.append(f"ℹ️ Rôle existant : **{name}**")

        staff_role = discord.utils.get(guild.roles, name="Staff")
        admin_role = discord.utils.get(guild.roles, name="Owner")

        # Overwrites
        read_only_overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False, add_reactions=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(send_messages=True, manage_channels=True, view_channel=True),
        }
        if staff_role:
            read_only_overwrites[staff_role] = discord.PermissionOverwrite(send_messages=True, manage_messages=True, view_channel=True)

        staff_only_overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if staff_role:
            staff_only_overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)
        if admin_role:
            staff_only_overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

        if selected_style == "gothic":
            structure = [
                (
                    "🔷 ────── MAIN ────── 🔷",
                    [
                        ("👋 ┃ 𝕭𝖎𝖊𝖓𝖛𝖊𝖓𝖚𝖊", "Bienvenue sur Core Market !", read_only_overwrites),
                        ("📌 ┃ 𝕬𝖓𝖓𝖔𝖓𝖈𝖊𝖘", "Annonces officielles", read_only_overwrites),
                        ("🚨 ┃ 𝕬𝖛𝖊𝖗𝖙𝖎𝖘𝖘𝖊𝖒𝖊𝖓𝖙", "Règles et avertissements", read_only_overwrites),
                        ("💫 ┃ 𝕬𝖛𝖎𝖘-𝖈𝖑𝖎𝖊𝖓𝖙", "Laissez votre avis après un achat", read_only_overwrites),
                        ("🎁 ┃ 𝕲𝖎𝖛𝖊𝖆𝖜𝖆𝖞", "Concours et giveaways", read_only_overwrites),
                        ("🌐 ┃ 𝖂𝖊𝖇𝖘𝖎𝖙𝖊", "Liens officiels et site web", read_only_overwrites),
                        ("📹 ┃ 𝕸𝖊𝖉𝖎𝖆", "Vidéos et démonstrations", read_only_overwrites),
                    ],
                ),
                (
                    "🔷 ────── CALL OF DUTY ────── 🔷",
                    [
                        ("🌌 ┃ 𝕾𝖕𝖔𝖔𝖋-𝕽𝖆𝖓𝖐𝖊𝖉", "Produit Spoof Ranked", read_only_overwrites),
                        ("🌌 ┃ 𝕸𝕮𝖔𝖗𝖊", "Produit MCore External", read_only_overwrites),
                        ("🌌 ┃ 𝕾𝖕𝖊𝖈𝖙𝖗𝖊", "Produit Spectre", read_only_overwrites),
                        ("🌌 ┃ 𝕲𝖊𝖓-𝖈𝖔𝖒𝖕𝖙𝖊-𝖘𝖙𝖊𝖆𝖒", "Générateur de comptes Steam", read_only_overwrites),
                        ("🔑 ┃ 𝕰𝖘𝖘𝖆𝖎-𝖌𝖗𝖆𝖙𝖚𝖎𝖙", "Demandes d'essai gratuit", read_only_overwrites),
                    ],
                ),
                (
                    "🔷 ────── TICKETS & SUPPORT ────── 🔷",
                    [
                        ("🎫 ┃ 𝖈𝖗𝖊𝖆𝖙𝖊-𝖙𝖎𝖈𝖐𝖊𝖙", "Ouvrir un ticket de support ou de commande", read_only_overwrites),
                    ],
                ),
                (
                    "🔒 ────── STAFF ONLY ────── 🔒",
                    [
                        ("💬 ┃ 𝖘𝖙𝖆𝖋𝖋-𝖈𝖍𝖆𝖙", "Discussion réservée à l'équipe", staff_only_overwrites),
                        ("📜 ┃ 𝖑𝖔𝖌𝖘-𝖙𝖎𝖈𝖐𝖊𝖙𝖘", "Logs automatiques des tickets", staff_only_overwrites),
                    ],
                ),
            ]
        elif selected_style == "clean":
            structure = [
                (
                    "🏆 ─── INFORMATION ─── 🏆",
                    [
                        ("👋・bienvenue", "Bienvenue !", read_only_overwrites),
                        ("📢・annonces", "Annonces officielles", read_only_overwrites),
                        ("🚨・reglement", "Règles du serveur", read_only_overwrites),
                        ("⭐・avis-clients", "Avis et vouches", read_only_overwrites),
                        ("🎁・giveaways", "Concours", read_only_overwrites),
                        ("🌐・website", "Site internet", read_only_overwrites),
                        ("🎬・media", "Vidéos et démonstrations", read_only_overwrites),
                    ],
                ),
                (
                    "🎮 ─── CALL OF DUTY ─── 🎮",
                    [
                        ("⚡・spoof-ranked", "Produit Spoof Ranked", read_only_overwrites),
                        ("🔥・mcore", "Produit MCore", read_only_overwrites),
                        ("🔮・spectre", "Produit Spectre", read_only_overwrites),
                        ("⚙️・gen-compte-steam", "Générateur Steam", read_only_overwrites),
                        ("🔑・essai-gratuit", "Essais gratuits", read_only_overwrites),
                    ],
                ),
                (
                    "🛒 ─── SUPPORT & TICKETS ─── 🛒",
                    [
                        ("🎫・creer-un-ticket", "Ouvrir un ticket", read_only_overwrites),
                    ],
                ),
                (
                    "🔒 ─── STAFF ONLY ─── 🔒",
                    [
                        ("💬・staff-chat", "Chat d'équipe", staff_only_overwrites),
                        ("📜・logs-tickets", "Logs des tickets", staff_only_overwrites),
                    ],
                ),
            ]
        else: # small_caps (default ultra clean)
            structure = [
                (
                    "✦ ─── INFORMATION ─── ✦",
                    [
                        ("👋・ʙɪᴇɴᴠᴇɴᴜᴇ", "Bienvenue sur Core Market !", read_only_overwrites),
                        ("📢・ᴀɴɴᴏɴᴄᴇꜱ", "Annonces officielles", read_only_overwrites),
                        ("🚨・ʀᴇɢʟᴇᴍᴇɴᴛ", "Règles et consignes", read_only_overwrites),
                        ("⭐・ᴀᴠɪꜱ-ᴄʟɪᴇɴᴛꜱ", "Avis clients et retours", read_only_overwrites),
                        ("🎁・ɢɪᴠᴇᴀᴡᴀʏꜱ", "Concours et cadeaux", read_only_overwrites),
                        ("🌐・ꜱɪᴛᴇ-ᴏꜰꜰɪᴄɪᴇʟ", "Liens officiels", read_only_overwrites),
                        ("🎬・ᴅᴇᴍᴏɴꜱᴛʀᴀᴛɪᴏɴꜱ", "Vidéos et présentations", read_only_overwrites),
                    ],
                ),
                (
                    "✦ ─── CALL OF DUTY ─── ✦",
                    [
                        ("⚡・ꜱᴘᴏᴏꜰ-ʀᴀɴᴋᴇᴅ", "Offres Spoof Ranked", read_only_overwrites),
                        ("🔥・ᴍᴄᴏʀᴇ", "Offres MCore External", read_only_overwrites),
                        ("🔮・ꜱᴘᴇᴄᴛʀᴇ", "Offres Spectre", read_only_overwrites),
                        ("⚙️・ɢᴇɴ-ᴄᴏᴍᴘᴛᴇ-ꜱᴛᴇᴀᴍ", "Comptes Steam", read_only_overwrites),
                        ("🔑・ᴇꜱꜱᴀɪ-ɢʀᴀᴛᴜɪᴛ", "Obtenir un test gratuit", read_only_overwrites),
                    ],
                ),
                (
                    "✦ ─── SUPPORT & TICKETS ─── ✦",
                    [
                        ("🎫・ᴄʀᴇᴇʀ-ᴜɴ-ᴛɪᴄᴋᴇᴛ", "Ouvrir un ticket pour acheter ou obtenir du support", read_only_overwrites),
                    ],
                ),
                (
                    "🔒 ─── STAFF ONLY ─── 🔒",
                    [
                        ("💬・ꜱᴛᴀꜰꜰ-ᴄʜᴀᴛ", "Salon réservé à l'équipe", staff_only_overwrites),
                        ("📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ", "Transcripts et historique", staff_only_overwrites),
                    ],
                ),
            ]

        for cat_name, channels in structure:
            category = discord.utils.get(guild.categories, name=cat_name)
            if category is None:
                category = await guild.create_category(cat_name)
                report.append(f"📁 Catégorie créée : **{cat_name}**")

            for ch_name, topic, ow in channels:
                existing = discord.utils.get(category.text_channels, name=ch_name)
                if existing is None:
                    ch = await category.create_text_channel(name=ch_name, topic=topic, overwrites=ow)
                    report.append(f"  └─ 💬 Salon créé : {ch.mention}")

                    # Auto post Vouch button in Avis-client
                    if "avis" in ch_name.lower():
                        from cogs.vouch import VouchButtonView
                        await ch.send(content="**⭐ Laissez un avis sur votre achat / Leave a review after purchase!**", view=VouchButtonView())

                    # Auto post Ticket panel in create-ticket
                    if "ticket" in ch_name.lower() and staff_role and "logs" not in ch_name.lower():
                        logs_ch = discord.utils.get(guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ") or discord.utils.get(guild.text_channels, name="📜 ┃ 𝖑𝖔𝖌𝖘-𝖙𝖎𝖈𝖐𝖊𝖙𝖘") or ch
                        await ch.send(content="**Créer un ticket / Create a ticket**", view=build_panel_view(staff_role.id, logs_ch.id, lang="fr"))
                else:
                    report.append(f"  └─ ℹ️ Salon existant : {existing.mention}")

        embed = discord.Embed(
            title="⚡ Configuration Core Market terminée !",
            color=discord.Color.blue(),
            description="\n".join(report[:30]) + ("\n..." if len(report) > 30 else ""),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
