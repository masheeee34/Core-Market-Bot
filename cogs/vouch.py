"""Vouch system — posts review button in ticket or channel and routes
posted reviews to the matching EN or FR vouch channel (e.g. under "community [ EN ]" or "community [ FR ]").

Zero database: sequential Vouch ID is recovered from latest vouch footer in that channel.
"""

import re
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from cogs.tickets import decode_topic, is_staff

ID_PATTERN = re.compile(r"Vouch ID: #(\d+)")

HAS_LABEL = hasattr(discord.ui, "Label")
HAS_FILE_UPLOAD = hasattr(discord.ui, "FileUpload")


def find_vouch_channel(guild: discord.Guild, lang: str = "en") -> discord.TextChannel | None:
    """Finds the correct vouch channel based on language (FR vs EN).
    Priority:
    1. Channel containing 'vouch' inside category containing 'FR' or 'EN' (e.g., 'community [ FR ]')
    2. Channel named 'vouch-fr', 'vouch-en', 'vouches-fr', etc.
    3. Any channel named 'vouch' or 'vouches'
    """
    target_lang = lang.lower()
    target_category_keyword = "FR" if target_lang == "fr" else "EN"

    # 1. Look inside matching category (e.g. "community [ FR ]" or "community [ EN ]")
    for category in guild.categories:
        if target_category_keyword.lower() in category.name.lower():
            for channel in category.text_channels:
                if "vouch" in channel.name.lower():
                    return channel

    # 2. Look for text channel matching language explicitly
    for channel in guild.text_channels:
        name_lower = channel.name.lower()
        if "vouch" in name_lower and target_lang in name_lower:
            return channel

    # 3. Fallback to any channel containing 'vouch'
    for channel in guild.text_channels:
        if "vouch" in channel.name.lower():
            return channel

    return None


async def next_vouch_id(channel: discord.TextChannel) -> int:
    async for message in channel.history(limit=100):
        if message.author == channel.guild.me and message.embeds:
            footer = message.embeds[0].footer.text or ""
            match = ID_PATTERN.search(footer)
            if match:
                return int(match.group(1)) + 1
    return 1


async def post_vouch(
    interaction: discord.Interaction,
    rating: int,
    text: str | None,
    attachments: list[discord.Attachment],
    lang: str = "en",
) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("⚠️ Error: Guild not found.", ephemeral=True)
        return

    channel = find_vouch_channel(guild, lang)
    if channel is None:
        await interaction.response.send_message(
            f"⚠️ No vouch channel found for language `{lang.upper()}`. Please create a `#vouch` channel in your `community [ {lang.upper()} ]` category.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)
    vouch_id = await next_vouch_id(channel)

    is_fr = lang.lower() == "fr"
    embed = discord.Embed(color=discord.Color.gold(), description=text or None)
    
    rating_field_name = "Note" if is_fr else "Rating"
    user_field_name = "Avis de" if is_fr else "Vouched by"
    
    embed.add_field(name=rating_field_name, value=f"{'⭐' * rating} {rating}/5", inline=True)
    embed.add_field(name=user_field_name, value=interaction.user.mention, inline=True)
    embed.set_footer(
        text=f"Vouch ID: #{vouch_id} • {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}"
    )

    files: list[discord.File] = []
    for attachment in attachments[:3]:
        try:
            files.append(await attachment.to_file())
        except discord.HTTPException:
            continue
    for attachment, file in zip(attachments, files):
        if (attachment.content_type or "").startswith("image/"):
            embed.set_image(url=f"attachment://{file.filename}")
            break

    await channel.send(embed=embed, files=files)
    
    confirm_msg = (
        f"✅ Merci pour votre avis ! Publié dans {channel.mention}."
        if is_fr
        else f"✅ Thanks for your review! Posted in {channel.mention}."
    )
    await interaction.followup.send(confirm_msg, ephemeral=True)


if HAS_LABEL:

    class VouchModal(discord.ui.Modal):
        """Dynamic modal for reviews supporting FR & EN."""

        def __init__(self, lang: str = "en") -> None:
            self.lang = lang
            is_fr = lang.lower() == "fr"
            title = "Laisser un avis" if is_fr else "Leave a Review"
            super().__init__(title=title, timeout=None)

            self.rating = discord.ui.Select(
                placeholder="Sélectionnez une note" if is_fr else "Select a rating",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=f"{i}/5", value=str(i))
                    for i in range(5, 0, -1)
                ],
            )
            self.add_item(discord.ui.Label(text="Note" if is_fr else "Rating", component=self.rating))

            self.explanation = discord.ui.TextInput(
                style=discord.TextStyle.paragraph,
                required=False,
                max_length=1000,
                placeholder="Votre avis sur l'achat... (optionnel)" if is_fr else "What went well? (Optional details help a lot)",
            )
            self.add_item(
                discord.ui.Label(
                    text="Explication" if is_fr else "Explanation",
                    description="Optionnel" if is_fr else "Optional",
                    component=self.explanation,
                )
            )

            self.files = None
            if HAS_FILE_UPLOAD:
                self.files = discord.ui.FileUpload(required=False, max_values=3)
                self.add_item(
                    discord.ui.Label(
                        text="Preuves (Fichiers)" if is_fr else "Upload Files",
                        description="Jusqu'à 3 images/fichiers comme preuve" if is_fr else "Upload up to 3 files as proof",
                        component=self.files,
                    )
                )

        async def on_submit(self, interaction: discord.Interaction) -> None:
            attachments = list(self.files.values) if self.files is not None else []
            await post_vouch(
                interaction,
                rating=int(self.rating.values[0]),
                text=self.explanation.value or None,
                attachments=attachments,
                lang=self.lang,
            )

else:

    class VouchModal(discord.ui.Modal):
        """Fallback minimal modal for reviews."""

        def __init__(self, lang: str = "en") -> None:
            self.lang = lang
            is_fr = lang.lower() == "fr"
            title = "Laisser un avis" if is_fr else "Leave a Review"
            super().__init__(title=title, timeout=None)
            self.rating_input = discord.ui.TextInput(label="Note (1-5)", max_length=1, placeholder="5")
            self.explanation_input = discord.ui.TextInput(
                label="Explication / Avis" if is_fr else "Explanation",
                style=discord.TextStyle.paragraph,
                required=False,
                max_length=1000,
            )
            self.add_item(self.rating_input)
            self.add_item(self.explanation_input)

        async def on_submit(self, interaction: discord.Interaction) -> None:
            try:
                rating = max(1, min(5, int(self.rating_input.value)))
            except ValueError:
                await interaction.response.send_message(
                    "⚠️ La note doit être un chiffre entre 1 et 5.", ephemeral=True
                )
                return
            await post_vouch(
                interaction,
                rating=rating,
                text=self.explanation_input.value or None,
                attachments=[],
                lang=self.lang,
            )


class VouchButtonView(discord.ui.View):
    """Persistent view with Vouch button."""

    def __init__(self, lang: str = "en") -> None:
        super().__init__(timeout=None)
        self.lang = lang

    @discord.ui.button(label="⭐ Vouch", style=discord.ButtonStyle.danger, custom_id="vouch:open")
    async def open_form(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        # Detect language from channel topic if available (e.g. inside a ticket)
        lang = self.lang
        if isinstance(interaction.channel, discord.TextChannel) and interaction.channel.topic:
            ticket_data = decode_topic(interaction.channel.topic)
            if ticket_data and "lang" in ticket_data:
                lang = ticket_data["lang"]

        await interaction.response.send_modal(VouchModal(lang=lang))


class Vouch(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(VouchButtonView())

    @app_commands.command(
        name="vouch",
        description="Poster le bouton d'avis/vouch dans ce salon ou ticket",
    )
    @app_commands.describe(
        langue="Langue du bouton et du salon cible (FR ou EN)",
    )
    @app_commands.choices(
        langue=[
            app_commands.Choice(name="Français 🇫🇷", value="fr"),
            app_commands.Choice(name="English 🇬🇧", value="en"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def vouch_cmd(
        self,
        interaction: discord.Interaction,
        langue: app_commands.Choice[str] | None = None,
    ) -> None:
        # Auto-detect language from ticket topic if not specified
        lang = langue.value if langue else "en"
        if langue is None and isinstance(interaction.channel, discord.TextChannel) and interaction.channel.topic:
            ticket_data = decode_topic(interaction.channel.topic)
            if ticket_data and "lang" in ticket_data:
                lang = ticket_data["lang"]

        is_fr = lang == "fr"
        content = (
            "**⭐ Laissez un avis sur votre achat !**\n"
            "Merci pour votre confiance. Cliquez sur le bouton ci-dessous pour publier votre avis."
            if is_fr
            else "**⭐ Leave a review after your purchase!**\n"
            "Thank you for your purchase. Click the button below to publish your review."
        )
        button_label = "⭐ Laisser un avis" if is_fr else "⭐ Leave a Review"

        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(
            label=button_label,
            style=discord.ButtonStyle.danger,
            custom_id="vouch:open",
        )

        async def button_callback(b_interaction: discord.Interaction) -> None:
            # Re-read ticket topic dynamically
            b_lang = lang
            if isinstance(b_interaction.channel, discord.TextChannel) and b_interaction.channel.topic:
                t_data = decode_topic(b_interaction.channel.topic)
                if t_data and "lang" in t_data:
                    b_lang = t_data["lang"]
            await b_interaction.response.send_modal(VouchModal(lang=b_lang))

        button.callback = button_callback
        view.add_item(button)

        await interaction.channel.send(content=content, view=view)
        await interaction.response.send_message(
            f"✅ Bouton Vouch posté (Langue: {lang.upper()}).", ephemeral=True
        )

    @app_commands.command(
        name="vouchpanel",
        description="Poster le bouton Vouch par défaut dans ce salon",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def vouchpanel(self, interaction: discord.Interaction) -> None:
        await self.vouch_cmd(interaction)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Vouch(bot))
