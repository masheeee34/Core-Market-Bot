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
        "Member",
        discord.Colour.from_str("#3498DB"),
        discord.Permissions(
            read_messages=True, send_messages=True, add_reactions=True, read_message_history=True
        ),
    ),
    (
        "Customer",
        discord.Colour.gold(),
        discord.Permissions.none(),
    ),
]


class VerifyRulesView(discord.ui.View):
    """Persistent Verification View for #rules."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Accept Rules & Unlock Server",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="verify_rules_button",
    )
    async def verify(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            return

        member_role = (
            discord.utils.get(guild.roles, name="Member")
            or discord.utils.get(guild.roles, name="Membre")
        )
        if member_role is None:
            try:
                member_role = await guild.create_role(
                    name="Member",
                    colour=discord.Colour.from_str("#3498DB"),
                    reason="Auto create Member role for verification",
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"⚠️ Error creating Member role: {e}", ephemeral=True
                )
                return

        if member_role in interaction.user.roles:
            await interaction.response.send_message(
                "ℹ️ You have already accepted the rules and unlocked the server!", ephemeral=True
            )
            return

        try:
            await interaction.user.add_roles(member_role, reason="Accepted server rules in #rules")
            await interaction.response.send_message(
                "✅ **Rules Accepted!** All server channels are now unlocked for you. Welcome to **Core Market**! 🎉",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"⚠️ Error assigning role: {e}", ephemeral=True
            )


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(VerifyRulesView())

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

        # 0. Clean old channels and categories if requested (safe & fast deletion)
        if supprimer_anciens_salons:
            report.append("🧹 **Nettoyage des anciens salons et catégories effectué.**")
            text_chs = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
            cats = [c for c in guild.channels if isinstance(c, discord.CategoryChannel)]
            for ch in text_chs:
                try:
                    await ch.delete(reason="/setup_core_market — auto clean")
                    await asyncio.sleep(0.1)
                except Exception:
                    pass
            for cat in cats:
                try:
                    await cat.delete(reason="/setup_core_market — auto clean")
                    await asyncio.sleep(0.1)
                except Exception:
                    pass

        # 1. Roles setup
        for name, colour, permissions in ROLE_SPECS:
            r = discord.utils.get(guild.roles, name=name)
            if r is None:
                r = await guild.create_role(
                    name=name,
                    colour=colour,
                    permissions=permissions,
                    hoist=True,
                    mentionable=True,
                    reason="/setup_core_market — role creation",
                )
                report.append(f"👑 Rôle créé : **{name}**")
            else:
                try:
                    await r.edit(permissions=permissions, colour=colour, hoist=True)
                except Exception:
                    pass
                report.append(f"ℹ️ Rôle mis à jour : **{name}**")

        staff_role = discord.utils.get(guild.roles, name="Staff")
        admin_role = discord.utils.get(guild.roles, name="Owner")
        member_role = discord.utils.get(guild.roles, name="Member")
        customer_role = discord.utils.get(guild.roles, name="Customer")

        # Lock down @everyone base permissions on the server (disable expressions / emojis / soundboard)
        default_permissions = discord.Permissions(
            read_messages=True,
            read_message_history=True,
            send_messages=False,
            add_reactions=True,
            use_application_commands=True,
            create_expressions=False,
            manage_expressions=False,
            create_public_threads=False,
            create_private_threads=False,
            send_tts_messages=False,
            embed_links=False,
            attach_files=False,
            mention_everyone=False,
        )
        try:
            await guild.default_role.edit(permissions=default_permissions, reason="/setup_core_market — lockdown @everyone permissions")
            report.append("🔒 Permissions **@everyone** restreintes (désactivation émojis / soundboard).")
        except Exception:
            pass

        # Auto assign Owner role to administrator running setup
        if admin_role and isinstance(interaction.user, discord.Member) and admin_role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(admin_role, reason="/setup_core_market — auto owner role assignment")
                report.append(f"👑 Rôle **Owner** attribué à {interaction.user.mention}")
            except Exception:
                pass

        # Public Overwrites: Welcome & Rules (Visible to @everyone without Member role)
        public_overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False, add_reactions=True, view_channel=True),
            guild.me: discord.PermissionOverwrite(send_messages=True, manage_channels=True, view_channel=True),
        }
        if staff_role:
            public_overwrites[staff_role] = discord.PermissionOverwrite(send_messages=True, manage_messages=True, view_channel=True)

        # Member / Customer Only Overwrites (All other channels: hidden from unverified @everyone, unlocked with Member or Customer role)
        member_only_overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(send_messages=True, manage_channels=True, view_channel=True),
        }
        if member_role:
            member_only_overwrites[member_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        if customer_role:
            member_only_overwrites[customer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        if staff_role:
            member_only_overwrites[staff_role] = discord.PermissionOverwrite(send_messages=True, manage_messages=True, view_channel=True)
        if admin_role:
            member_only_overwrites[admin_role] = discord.PermissionOverwrite(send_messages=True, manage_messages=True, view_channel=True)

        staff_only_overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if staff_role:
            staff_only_overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        if admin_role:
            staff_only_overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)

        if selected_style == "gothic":
            structure = [
                (
                    "🔷 ────── MAIN ────── 🔷",
                    [
                        ("👋 ┃ 𝕭𝖎𝖊𝖓𝖛𝖊𝖓𝖚𝖊", "Bienvenue sur Core Market !", public_overwrites, "welcome"),
                        ("📌 ┃ 𝕬𝖓𝖓𝖔𝖓𝖈𝖊𝖘", "Annonces officielles", member_only_overwrites, None),
                        ("🚨 ┃ 𝕬𝖛𝖊𝖗𝖙𝖎𝖘𝖘𝖊𝖒𝖊𝖓𝖙", "Règles et avertissements", public_overwrites, "rules"),
                        ("💫 ┃ 𝕬𝖛𝖎𝖘-𝖈𝖑𝖎𝖊𝖓𝖙", "Laissez votre avis après un achat", member_only_overwrites, "vouch"),
                        ("🎁 ┃ 𝕲𝖎𝖛𝖊𝖆𝖜𝖆𝖞", "Concours et giveaways", member_only_overwrites, None),
                        ("🌐 ┃ 𝖂𝖊𝖇𝖘𝖎𝖙𝖊", "Liens officiels et site web", member_only_overwrites, None),
                        ("📹 ┃ 𝕸𝖊𝖉𝖎𝖆", "Vidéos et démonstrations", member_only_overwrites, None),
                    ],
                ),
                (
                    "🔷 ────── CALL OF DUTY ────── 🔷",
                    [
                        ("🌌 ┃ 𝕾𝖕𝖔𝖔𝖋-𝕽𝖆𝖓𝖐𝖊𝖉", "Produit Spoof Ranked", member_only_overwrites, None),
                        ("🌌 ┃ 𝕸𝕮𝖔𝖗𝖊", "Produit MCore External", member_only_overwrites, None),
                        ("🌌 ┃ 𝕾𝖕𝖊𝖈𝖙𝖗𝖊", "Produit Spectre", member_only_overwrites, None),
                        ("🌌 ┃ 𝕲𝖊𝖓-𝖈𝖔𝖒𝖕𝖙𝖊-𝖘𝖙𝖊𝖆𝖒", "Générateur de comptes Steam", member_only_overwrites, None),
                        ("🔑 ┃ 𝕰𝖘𝖘𝖆𝖎-𝖌𝖗𝖆𝖙𝖚𝖎𝖙", "Demandes d'essai gratuit", member_only_overwrites, None),
                    ],
                ),
                (
                    "🔷 ────── TICKETS & SUPPORT ────── 🔷",
                    [
                        ("🎫 ┃ 𝖈𝖗𝖊𝖆𝖙𝖊-𝖙𝖎𝖈𝖐𝖊𝖙", "Ouvrir un ticket de support ou de commande", member_only_overwrites, "ticket"),
                    ],
                ),
                (
                    "🔒 ────── STAFF ONLY ────── 🔒",
                    [
                        ("💬 ┃ 𝖘𝖙𝖆𝖋𝖋-𝖈𝖍𝖆𝖙", "Discussion réservée à l'équipe", staff_only_overwrites, None),
                        ("📜 ┃ 𝖑𝖔𝖌𝖘-𝖙𝖎𝖈𝖐𝖊𝖙𝖘", "Logs automatiques des tickets", staff_only_overwrites, None),
                    ],
                ),
            ]
        elif selected_style == "clean":
            structure = [
                (
                    "🏆 ─── INFORMATION ─── 🏆",
                    [
                        ("👋・bienvenue", "Bienvenue !", public_overwrites, "welcome"),
                        ("📢・annonces", "Annonces officielles", member_only_overwrites, None),
                        ("🚨・reglement", "Règles du serveur", public_overwrites, "rules"),
                        ("⭐・avis-clients", "Avis et vouches", member_only_overwrites, "vouch"),
                        ("🎁・giveaways", "Concours", member_only_overwrites, None),
                        ("🌐・website", "Site internet", member_only_overwrites, None),
                        ("🎬・media", "Vidéos et démonstrations", member_only_overwrites, None),
                    ],
                ),
                (
                    "🎮 ─── CALL OF DUTY ─── 🎮",
                    [
                        ("⚡・spoof-ranked", "Produit Spoof Ranked", member_only_overwrites, None),
                        ("🔥・mcore", "Produit MCore", member_only_overwrites, None),
                        ("🔮・spectre", "Produit Spectre", member_only_overwrites, None),
                        ("⚙️・gen-compte-steam", "Générateur Steam", member_only_overwrites, None),
                        ("🔑・essai-gratuit", "Essais gratuits", member_only_overwrites, None),
                    ],
                ),
                (
                    "🎯 ─── VALORANT ─── 🎯",
                    [
                        ("⚡・pulse-internal", "Produit Pulse Internal", member_only_overwrites, None),
                    ],
                ),
                (
                    "🛒 ─── SUPPORT & TICKETS ─── 🛒",
                    [
                        ("🎫・creer-un-ticket", "Ouvrir un ticket", member_only_overwrites, "ticket"),
                    ],
                ),
                (
                    "🔒 ─── STAFF ONLY ─── 🔒",
                    [
                        ("💬・staff-chat", "Chat d'équipe", staff_only_overwrites, None),
                        ("📜・logs-tickets", "Logs des tickets", staff_only_overwrites, None),
                    ],
                ),
            ]
        else: # small_caps (default ultra clean)
            structure = [
                (
                    "🔒 ─── STAFF ONLY ─── 🔒",
                    [
                        ("💬・ꜱᴛᴀꜰꜰ-ᴄʜᴀᴛ", "Staff team lounge", staff_only_overwrites, None),
                        ("📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ", "Automatic ticket transcripts & logs", staff_only_overwrites, None),
                    ],
                ),
                (
                    "✦ ─── INFORMATION ─── ✦",
                    [
                        ("👋・ᴡᴇʟᴄᴏᴍᴇ", "Welcome to Core Market !", public_overwrites, "welcome"),
                        ("📢・ᴀɴɴᴏᴜɴᴄᴇᴍᴇɴᴛꜱ", "Official announcements", member_only_overwrites, None),
                        ("🚨・ʀᴜʟᴇꜱ", "Server rules and guidelines", public_overwrites, "rules"),
                        ("⭐・ʀᴇᴠɪᴇᴡꜱ-ᴠᴏᴜᴄʜᴇꜱ", "Customer reviews and vouches", member_only_overwrites, "vouch"),
                        ("🎁・ɢɪᴠᴇᴀᴡᴀYꜱ", "Giveaways and contests", member_only_overwrites, None),
                        ("🌐・ᴏꜰꜰɪᴄɪᴀʟ-ᴡᴇʙꜱɪᴛᴇ", "Official links and website", member_only_overwrites, None),
                        ("🎬・ᴍᴇᴅɪᴀ-ꜱʜᴏᴡᴄᴀꜱᴇ", "Demonstrations and showcase", member_only_overwrites, None),
                    ],
                ),
                (
                    "✦ ─── CALL OF DUTY ─── ✦",
                    [
                        ("🔴・ᴍᴄᴏʀᴇ-ᴇxᴛᴇʀɴᴀʟ", "M-CORE External BO7 / Warzone", member_only_overwrites, "mcore"),
                        ("🔮・ꜱᴘᴇᴄᴛʀᴇ-ᴇxᴛᴇʀɴᴀʟ", "TRINITY SPECTRE BO7 / Warzone", member_only_overwrites, "spectre"),
                        ("🔑・ꜰʀᴇᴇ-ᴛʀɪᴀʟ", "Free trial requests", member_only_overwrites, "soon"),
                    ],
                ),
                (
                    "✦ ─── VALORANT ─── ✦",
                    [
                        ("⚡・ᴘᴜʟꜱᴇ-ɪɴᴛᴇʀɴᴀʟ", "Pulse Internal Valorant", member_only_overwrites, "pulse"),
                    ],
                ),
                (
                    "✦ ─── SUPPORT & TICKETS ─── ✦",
                    [
                        ("🎫・ᴄʀᴇᴀᴛᴇ-ᴛɪᴄᴋᴇᴛ", "Open a ticket for purchase or support", member_only_overwrites, "ticket"),
                    ],
                ),
            ]

        # Re-fetch staff_role after roles are guaranteed to exist
        staff_role = discord.utils.get(guild.roles, name="Staff") or discord.utils.get(guild.roles, name="Owner") or guild.default_role

        for cat_name, channels in structure:
            category = discord.utils.get(guild.categories, name=cat_name)

            # Define category level overwrites for strict lockdown
            is_staff_cat = "STAFF" in cat_name
            is_info_cat = "INFORMATION" in cat_name or "MAIN" in cat_name

            if is_staff_cat:
                cat_ow = staff_only_overwrites
            elif is_info_cat:
                cat_ow = public_overwrites
            else:
                cat_ow = member_only_overwrites

            if category is None:
                category = await guild.create_category(cat_name, overwrites=cat_ow)
                report.append(f"📁 Category created: **{cat_name}**")
            else:
                try:
                    await category.edit(overwrites=cat_ow)
                except Exception:
                    pass

            for ch_name, topic, ow, action in channels:
                # Flexible channel lookup matching exact name or keyword
                existing = discord.utils.get(category.text_channels, name=ch_name)
                if existing is None and action:
                    for tc in category.text_channels:
                        tc_lower = tc.name.lower()
                        if (
                            (action == "welcome" and ("welcome" in tc_lower or "bienvenue" in tc_lower))
                            or (action == "rules" and ("rule" in tc_lower or "reglement" in tc_lower))
                            or (action == "vouch" and ("vouch" in tc_lower or "avis" in tc_lower))
                            or (action == "ticket" and ("ticket" in tc_lower))
                            or (action == "mcore" and ("mcore" in tc_lower))
                            or (action == "spectre" and ("spectre" in tc_lower))
                            or (action == "pulse" and ("pulse" in tc_lower))
                        ):
                            existing = tc
                            break

                ch = existing
                if ch is None:
                    ch = await category.create_text_channel(name=ch_name, topic=topic, overwrites=ow)
                    report.append(f"  └─ 💬 Channel created: {ch.mention}")
                else:
                    # Enforce overwrites on existing channels
                    try:
                        await ch.edit(overwrites=ow, name=ch_name, topic=topic)
                    except Exception:
                        pass
                    report.append(f"  └─ ℹ️ Channel updated: {ch.mention}")

                # Purge old bot messages before posting fresh embeds
                if action and ch:
                    try:
                        def is_bot_msg(m: discord.Message) -> bool:
                            return m.author.id == self.bot.user.id
                        await ch.purge(limit=10, check=is_bot_msg)
                    except Exception:
                        pass

                # Auto post Welcome Presentation
                if action == "welcome":
                    ticket_ch = discord.utils.get(guild.text_channels, name="🎫・ᴄʀᴇᴀᴛᴇ-ᴛɪᴄᴋᴇᴛ") or ch
                    vouch_ch = discord.utils.get(guild.text_channels, name="⭐・ʀᴇᴠɪᴇᴡꜱ-ᴠᴏᴜᴄʜᴇꜱ") or ch
                    embed = discord.Embed(
                        title="👋 Welcome to Core Market!",
                        description=(
                            "Welcome to **Core Market** — Your #1 Provider for Black Ops 7, Warzone & Valorant Tools!\n\n"
                            f"📌 **Quick Guide:**\n"
                            f"• Browse our products in the **Call of Duty** & **Valorant** categories!\n"
                            f"• Ready to buy? Open a ticket in {ticket_ch.mention}!\n"
                            f"• Leave feedback after your purchase in {vouch_ch.mention}!\n\n"
                            "*Enjoy your stay and feel free to open a ticket for any questions!*"
                        ),
                        color=discord.Color.from_str("#0070FF"),
                    )
                    embed.set_footer(text="Core Market • Premium Tools & Resell")
                    await ch.send(embed=embed)

                # Auto post Rules & Verification Panel
                elif action == "rules":
                    embed = discord.Embed(
                        title="🚨 Core Market — Server Rules & Verification",
                        description=(
                            "Welcome to **Core Market**! Please read and accept our server rules to unlock full access to all channels.\n\n"
                            "📜 **Server Rules:**\n"
                            "1️⃣ **Respect Everyone:** No toxicity, harassment, hate speech, or offensive behavior.\n"
                            "2️⃣ **No Advertising / Spam:** Do not DM members, post invite links, or self-promote.\n"
                            "3️⃣ **Use Appropriate Channels:** Keep discussions relevant to each channel.\n"
                            "4️⃣ **Staff Decisions are Final:** Follow instructions from staff and admins.\n"
                            "5️⃣ **No Scamming / Fraud:** Any attempt to scam will result in an instant permanent ban.\n\n"
                            "✅ **Click the button below to accept the rules and unlock the server!**"
                        ),
                        color=discord.Color.from_str("#0070FF"),
                    )
                    embed.set_footer(text="Core Market • Rules & Verification")
                    await ch.send(embed=embed, view=VerifyRulesView())

                # Auto post Vouch button
                elif action == "vouch":
                    from cogs.vouch import VouchButtonView
                    await ch.send(content="**⭐ Leave a review after your purchase!**", view=VouchButtonView())

                # Auto post Ticket panel
                elif action == "ticket":
                    logs_ch = (
                        discord.utils.get(guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ")
                        or discord.utils.get(guild.text_channels, name="📜・logs-tickets")
                        or ch
                    )
                    await ch.send(
                        content="**Create a Ticket**",
                        view=build_panel_view(staff_role.id, logs_ch.id, lang="en"),
                    )

                # Auto post product sales embeds
                elif action in ("mcore", "spectre", "pulse"):
                    from cogs.products import build_product_embed, build_product_view
                    pkey = "mcore" if action == "mcore" else ("spectre" if action == "spectre" else "pulse_internal")
                    embed = build_product_embed(pkey)
                    if embed:
                        logs_ch = discord.utils.get(guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ") or ch
                        view = build_product_view(pkey, staff_role.id, logs_ch.id)
                        await ch.send(embed=embed, view=view)

                # Auto post SOON GIF
                elif action == "soon":
                    embed_soon = discord.Embed(
                        title="⏳ COMING SOON",
                        description="*Free trials will be available very soon! Stay tuned.*",
                        color=discord.Color.from_str("#0070FF"),
                    )
                    embed_soon.set_image(url="https://media.giphy.com/media/l1J9u3TZfzYTEpqaQ/giphy.gif")
                    await ch.send(embed=embed_soon)

        embed = discord.Embed(
            title="⚡ Configuration Core Market terminée !",
            color=discord.Color.blue(),
            description="\n".join(report[:30]) + ("\n..." if len(report) > 30 else ""),
        )
        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception:
            if interaction.channel:
                await interaction.channel.send(embed=embed)

    @app_commands.command(
        name="setup_soon",
        description="Poster un message 'COMING SOON' avec un GIF animé",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_soon(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="⏳ COMING SOON",
            description="*This feature/trial will be available very soon! Stay tuned.*",
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_image(url="https://media.giphy.com/media/l1J9u3TZfzYTEpqaQ/giphy.gif")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Message COMING SOON publié !", ephemeral=True)

    @app_commands.command(
        name="setup_welcome",
        description="Poster le message de bienvenue principal de Core Market",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_welcome(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        ch = interaction.channel
        ticket_ch = discord.utils.get(guild.text_channels, name="🎫・ᴄʀᴇᴀᴛᴇ-ᴛɪᴄᴋᴇᴛ") or ch
        vouch_ch = discord.utils.get(guild.text_channels, name="⭐・ʀᴇᴠɪᴇᴡꜱ-ᴠᴏᴜᴄʜᴇꜱ") or ch
        embed = discord.Embed(
            title="👋 Welcome to Core Market!",
            description=(
                "Welcome to **Core Market** — Your #1 Provider for Black Ops 7, Warzone & Valorant Tools!\n\n"
                f"📌 **Quick Guide:**\n"
                f"• Browse our products in the **Call of Duty** & **Valorant** categories!\n"
                f"• Ready to buy? Open a ticket in {ticket_ch.mention}!\n"
                f"• Leave feedback after your purchase in {vouch_ch.mention}!\n\n"
                "*Enjoy your stay and feel free to open a ticket for any questions!*"
            ),
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text="Core Market • Premium Tools & Resell")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Message de bienvenue publié !", ephemeral=True)

    @app_commands.command(
        name="setup_rules",
        description="Poster le panneau de règlement et de vérification avec le bouton d'acceptation",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_rules(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="🚨 Core Market — Server Rules & Verification",
            description=(
                "Welcome to **Core Market**! Please read and accept our server rules to unlock full access to all channels.\n\n"
                "📜 **Server Rules:**\n"
                "1️⃣ **Respect Everyone:** No toxicity, harassment, hate speech, or offensive behavior.\n"
                "2️⃣ **No Advertising / Spam:** Do not DM members, post invite links, or self-promote.\n"
                "3️⃣ **Use Appropriate Channels:** Keep discussions relevant to each channel.\n"
                "4️⃣ **Staff Decisions are Final:** Follow instructions from staff and admins.\n"
                "5️⃣ **No Scamming / Fraud:** Any attempt to scam will result in an instant permanent ban.\n\n"
                "✅ **Click the button below to accept the rules and unlock the server!**"
            ),
            color=discord.Color.from_str("#0070FF"),
        )
        embed.set_footer(text="Core Market • Rules & Verification")
        await interaction.channel.send(embed=embed, view=VerifyRulesView())
        await interaction.response.send_message("✅ Panneau de règlement & vérification publié !", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Auto welcome new members when they join the server."""
        guild = member.guild
        ch = (
            discord.utils.get(guild.text_channels, name="👋・ᴡᴇʟᴄᴏᴍᴇ")
            or discord.utils.get(guild.text_channels, name="👋・bienvenue")
            or discord.utils.get(guild.text_channels, name="welcome")
        )
        if ch is not None:
            ticket_ch = discord.utils.get(guild.text_channels, name="🎫・ᴄʀᴇᴀᴛᴇ-ᴛɪᴄᴋᴇᴛ") or ch
            embed = discord.Embed(
                title=f"👋 Welcome to Core Market, {member.name}!",
                description=f"Hey {member.mention}, welcome to **Core Market**!\nOpen a ticket in {ticket_ch.mention} if you need help or want to buy.",
                color=discord.Color.from_str("#0070FF"),
            )
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            await ch.send(content=f"👋 {member.mention}", embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Ping listener: Mention @bot with any product text to turn it into a formatted embed with Buy button."""
        if message.author.bot or not message.guild or not isinstance(message.channel, discord.TextChannel):
            return

        if self.bot.user in message.mentions:
            is_admin = message.author.guild_permissions.administrator
            staff_role = discord.utils.get(message.guild.roles, name="Staff")
            owner_role = discord.utils.get(message.guild.roles, name="Owner")
            has_role = any(r in message.author.roles for r in (staff_role, owner_role) if r)

            if not (is_admin or has_role):
                return

            clean_text = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()

            # Clean raw custom emoji IDs from external server copies (e.g. :123456789:)
            import re
            clean_text = re.sub(r":\d+:", "• ", clean_text)

            if clean_text:
                lines = [l.strip() for l in clean_text.split("\n") if l.strip()]
                title = lines[0]
                desc = "\n".join(lines[1:]) if len(lines) > 1 else ""

                embed = discord.Embed(
                    title=f"⚡ {title}",
                    description=desc if desc else None,
                    color=discord.Color.from_str("#0070FF"),
                )
                embed.set_footer(text="Core Market • Click the button below to purchase")

                logs_ch = (
                    discord.utils.get(message.guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ")
                    or message.channel
                )
                staff_r = staff_role or owner_role or message.guild.default_role

                view = build_panel_view(staff_r.id, logs_ch.id, lang="en")
                await message.channel.send(embed=embed, view=view)
                try:
                    await message.delete()
                except Exception:
                    pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
