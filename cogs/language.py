"""Language module — bilingual server via display roles.

/setuplanguage creates the `English` and `Français` roles (no permissions,
display only), the #🌍-language channel and posts the picker embed with two
buttons. Members click to swap roles; server admins then hide/show channels
per language using those roles.
"""

import discord
from discord import app_commands
from discord.ext import commands

LANG_CHANNEL_NAME = "🌍-language"

# custom_id -> (role to give, role to remove)
LANG_BUTTONS = {
    "lang_en": ("English", "Français"),
    "lang_fr": ("Français", "English"),
}


async def swap_language_role(interaction: discord.Interaction, custom_id: str) -> None:
    give_name, remove_name = LANG_BUTTONS[custom_id]
    guild = interaction.guild
    member = interaction.user

    give = discord.utils.get(guild.roles, name=give_name)
    remove = discord.utils.get(guild.roles, name=remove_name)
    if give is None:
        await interaction.response.send_message(
            "⚠️ Language roles are missing — ask an admin to run /setuplanguage.",
            ephemeral=True,
        )
        return

    try:
        if remove is not None and remove in member.roles:
            await member.remove_roles(remove, reason="Language switch")
        if give not in member.roles:
            await member.add_roles(give, reason="Language switch")
    except discord.Forbidden:
        await interaction.response.send_message(
            "⚠️ I can't manage these roles — my role must be above them.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        "Language updated! / Langue mise à jour !", ephemeral=True
    )


class LanguageView(discord.ui.View):
    """Persistent view — the two language buttons keep working after restarts."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="English", emoji="🇬🇧", style=discord.ButtonStyle.primary, custom_id="lang_en")
    async def english(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await swap_language_role(interaction, "lang_en")

    @discord.ui.button(label="Français", emoji="🇫🇷", style=discord.ButtonStyle.primary, custom_id="lang_fr")
    async def francais(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await swap_language_role(interaction, "lang_fr")


async def clone_category_for_role(
    source: discord.CategoryChannel,
    suffix: str,
    lang_role: discord.Role,
    staff_roles: list[discord.Role],
) -> discord.CategoryChannel:
    """Crée une copie de `source` visible uniquement par `lang_role` (+ staff),
    et y recrée les salons texte/vocaux de l'original."""
    guild = source.guild

    overwrites: dict = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        lang_role: discord.PermissionOverwrite(view_channel=True),
    }
    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    new_category = await guild.create_category(
        f"{source.name} [{suffix}]", overwrites=overwrites, reason="Bilingual duplicate"
    )

    # Recrée chaque salon en héritant des permissions de la catégorie (sync).
    for channel in source.channels:
        if isinstance(channel, discord.TextChannel):
            await guild.create_text_channel(
                channel.name, category=new_category, topic=channel.topic,
                reason="Bilingual duplicate",
            )
        elif isinstance(channel, discord.VoiceChannel):
            await guild.create_voice_channel(
                channel.name, category=new_category, reason="Bilingual duplicate",
            )
    return new_category


class Language(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(LanguageView())

    @app_commands.command(
        name="duplicatelang",
        description="Dupliquer une catégorie en deux versions [EN] et [FR] verrouillées par rôle",
    )
    @app_commands.describe(categorie="La catégorie à dupliquer en anglais et français")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def duplicatelang(
        self, interaction: discord.Interaction, categorie: discord.CategoryChannel
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        english = discord.utils.get(guild.roles, name="English")
        francais = discord.utils.get(guild.roles, name="Français")
        if english is None or francais is None:
            await interaction.followup.send(
                "⚠️ Rôles de langue manquants — lance d'abord `/setuplanguage`.", ephemeral=True
            )
            return

        # Le staff garde accès aux deux versions.
        staff_roles = [
            r for name in ("Owner", "Staff", "Helper")
            if (r := discord.utils.get(guild.roles, name=name)) is not None
        ]

        try:
            en = await clone_category_for_role(categorie, "EN", english, staff_roles)
            fr = await clone_category_for_role(categorie, "FR", francais, staff_roles)
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ Permissions insuffisantes (Gérer les salons + rôle du bot au-dessus des rôles de langue).",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            embed=discord.Embed(
                title="Catégorie dupliquée",
                color=discord.Color.green(),
                description=(
                    f"**Source :** {categorie.name}\n"
                    f"**Créée :** {en.name} (visible: rôle English)\n"
                    f"**Créée :** {fr.name} (visible: rôle Français)\n\n"
                    f"Tu peux maintenant supprimer la catégorie originale **{categorie.name}** "
                    f"si tu veux, et déplacer/renommer les salons dans chaque version."
                ),
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="setuplanguage",
        description="Créer les rôles English/Français et le salon de choix de langue",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setuplanguage(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        report: list[str] = []

        # 1) Display roles, no special permissions.
        for name in ("English", "Français"):
            if discord.utils.get(guild.roles, name=name) is None:
                await guild.create_role(
                    name=name,
                    permissions=discord.Permissions.none(),
                    reason="/setuplanguage — display role",
                )
                report.append(f"Rôle créé : **{name}**")
            else:
                report.append(f"Rôle déjà présent : **{name}**")

        # 2) Picker channel: visible by everyone, read-only (buttons only).
        channel = discord.utils.get(guild.text_channels, name=LANG_CHANNEL_NAME)
        if channel is None:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=True, send_messages=False, add_reactions=False
                ),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            channel = await guild.create_text_channel(
                LANG_CHANNEL_NAME, overwrites=overwrites, reason="/setuplanguage"
            )
            report.append(f"Salon créé : {channel.mention}")
        else:
            report.append(f"Salon déjà présent : {channel.mention}")

        # 3) Picker embed + buttons.
        embed = discord.Embed(
            title="🌍 Choose your Language / Choisissez votre langue",
            color=discord.Color.blurple(),
            description=(
                "Click the button below to access the server in your language.\n"
                "Cliquez sur le bouton ci-dessous pour accéder au serveur dans votre langue."
            ),
        )
        await channel.send(embed=embed, view=LanguageView())
        report.append("Panel de langue posté.")

        await interaction.followup.send(
            embed=discord.Embed(
                title="Language setup terminé",
                color=discord.Color.green(),
                description="\n".join(report),
            ),
            ephemeral=True,
        )

    @app_commands.command(
        name="setup_onboarding",
        description="Configurer automatiquement l'écran d'accueil Discord Onboarding multilingue",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_onboarding(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        if "COMMUNITY" not in guild.features:
            await interaction.followup.send(
                "⚠️ **La fonctionnalité Communauté n'est pas activée sur ce serveur.**\n\n"
                "1. Allez dans **Paramètres du serveur** ➔ **Activer la communauté** (1 clic).\n"
                "2. Relancez ensuite **/setup_onboarding**.",
                ephemeral=True,
            )
            return

        lang_configs = [
            ("English", "🇬🇧", "English community & announcements"),
            ("Français", "🇫🇷", "Communauté et annonces en français"),
            ("Español", "🇪🇸", "Comunidad y anuncios en español"),
            ("Deutsch", "🇩🇪", "Deutsche Community & Ankündigungen"),
            ("Korean", "🇰🇷", "한국어 커뮤니티 및 공지사항"),
            ("Arabic", "🇸🇦", "المجتمع والإعلانات باللغة العربية"),
            ("Chinese", "🇨🇳", "中文社区与公告"),
        ]

        created_roles: dict[str, discord.Role] = {}
        for name, emoji, _ in lang_configs:
            role = discord.utils.get(guild.roles, name=name)
            if not role:
                role = await guild.create_role(name=name, reason="Onboarding Multi-Language Setup")
            created_roles[name] = role

        options = []
        for name, emoji, desc in lang_configs:
            role = created_roles[name]
            options.append(
                discord.OnboardingPromptOption(
                    title=name,
                    emoji=emoji,
                    description=desc,
                    roles=[role],
                )
            )

        prompt = discord.OnboardingPrompt(
            type=discord.OnboardingPromptType.multiple_choice,
            title="What is your primary language? / Choisissez votre langue",
            options=options,
            single_select=True,
            required=True,
            in_onboarding=True,
        )

        # Select 5+ public text channels (excluding private staff/tickets/logs)
        candidate_channels = [
            ch for ch in guild.text_channels
            if not any(w in ch.name.lower() for w in ("log", "staff", "admin", "ticket", "bot-", "private"))
        ]

        default_channels: list[discord.TextChannel] = []
        for ch in candidate_channels:
            try:
                # Ensure @everyone can view the channel as required by Discord Onboarding
                if not ch.permissions_for(guild.default_role).view_channel:
                    await ch.set_permissions(guild.default_role, view_channel=True, reason="Discord Onboarding requirement")
                default_channels.append(ch)
            except Exception:
                pass
            if len(default_channels) >= 5:
                break

        # If less than 5 channels exist, create missing public channels
        missing_names = ["📢・announcements", "🎁・giveaways", "⭐・vouches", "💬・general-chat", "📜・rules-info"]
        idx = 0
        while len(default_channels) < 5 and idx < len(missing_names):
            name = missing_names[idx]
            idx += 1
            if not discord.utils.get(guild.text_channels, name=name):
                try:
                    new_ch = await guild.create_text_channel(name, reason="Discord Onboarding 5-channels requirement")
                    default_channels.append(new_ch)
                except Exception:
                    pass

        try:
            await guild.edit_onboarding(
                prompts=[prompt],
                default_channels=default_channels,
                enabled=True,
                mode=discord.OnboardingMode.default,
                reason="Auto multi-language onboarding setup",
            )
            await interaction.followup.send(
                embed=discord.Embed(
                    title="🎉  DISCORD ONBOARDING ACTIVÉ À 100% !",
                    description=(
                        "L'écran d'accueil Discord Onboarding multilingue est désormais **pleinement configuré et actif** !\n\n"
                        "▸ **7 Langues intégrées :** 🇬🇧 English, 🇫🇷 Français, 🇪🇸 Español, 🇩🇪 Deutsch, 🇰🇷 Korean, 🇸🇦 Arabic, 🇨🇳 Chinese\n"
                        "▸ **Salons par défaut :** " + ", ".join(ch.mention for ch in default_channels) + "\n"
                        "▸ **Affichage :** Tout nouveau membre verra désormais la page de sélection plein écran dès son arrivée.\n"
                        "▸ **Rôles :** Le rôle de langue est automatiquement distribué sans aucune intervention."
                    ),
                    color=discord.Color.green(),
                ),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ **Permissions insuffisantes** : Veuillez placer le rôle du bot tout en haut de la liste des rôles dans *Paramètres du serveur ➔ Rôles*.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Notification Discord : `{e}`\n\n"
                "💡 Les 7 rôles de langue sont déjà créés. Vous pouvez également cliquer sur **Activer l'accueil** dans *Paramètres du serveur ➔ Accueil*.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Language(bot))
