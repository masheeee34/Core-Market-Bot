"""Vouch system — a red "Vouch" button opens a Discord form (modal):
rating select, optional explanation, optional file upload (proof).
The bot then posts a clean review embed in #vouches.

No database: the sequential Vouch ID is recovered by reading the footer of the
latest vouch posted by the bot in the channel.
"""

import re

import discord
from discord import app_commands
from discord.ext import commands

VOUCH_CHANNEL_NAME = "vouches"
ID_PATTERN = re.compile(r"Vouch ID: #(\d+)")

# Les selects/file-upload dans les modals demandent discord.py >= 2.6.
HAS_LABEL = hasattr(discord.ui, "Label")
HAS_FILE_UPLOAD = hasattr(discord.ui, "FileUpload")


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
) -> None:
    channel = discord.utils.get(interaction.guild.text_channels, name=VOUCH_CHANNEL_NAME)
    if channel is None:
        await interaction.response.send_message(
            "⚠️ No #vouches channel found — ask an admin to run /setup.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    vouch_id = await next_vouch_id(channel)

    embed = discord.Embed(color=discord.Color.gold(), description=text or None)
    embed.add_field(name="Rating", value=f"{'⭐' * rating} {rating}/5", inline=True)
    embed.add_field(name="Vouched by", value=interaction.user.mention, inline=True)
    embed.set_footer(
        text=f"Vouch ID: #{vouch_id} • {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}"
    )

    # Ré-upload des preuves pour des liens permanents ; la 1re image illustre l'embed.
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
    await interaction.followup.send(
        f"✅ Thanks for your review! Posted in {channel.mention}.", ephemeral=True
    )


if HAS_LABEL:

    class VouchModal(discord.ui.Modal, title="Leave a Review"):
        """Formulaire complet : select de note, texte optionnel, upload de preuves."""

        def __init__(self) -> None:
            super().__init__(timeout=None)

            self.rating = discord.ui.Select(
                placeholder="Select a rating",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=f"{i}/5", value=str(i))
                    for i in range(5, 0, -1)
                ],
            )
            self.add_item(discord.ui.Label(text="Rating", component=self.rating))

            self.explanation = discord.ui.TextInput(
                style=discord.TextStyle.paragraph,
                required=False,
                max_length=1000,
                placeholder="What went well? (Optional details help a lot)",
            )
            self.add_item(
                discord.ui.Label(
                    text="Explanation",
                    description="Optional — tell us what went well",
                    component=self.explanation,
                )
            )

            self.files = None
            if HAS_FILE_UPLOAD:
                self.files = discord.ui.FileUpload(required=False, max_values=3)
                self.add_item(
                    discord.ui.Label(
                        text="Upload Files",
                        description="Upload up to 3 files as proof",
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
            )

else:

    class VouchModal(discord.ui.Modal, title="Leave a Review"):
        """Fallback minimal si la lib ne supporte pas les selects en modal."""

        rating = discord.ui.TextInput(label="Rating (1-5)", max_length=1, placeholder="5")
        explanation = discord.ui.TextInput(
            label="Explanation",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            placeholder="What went well? (Optional details help a lot)",
        )

        async def on_submit(self, interaction: discord.Interaction) -> None:
            try:
                rating = max(1, min(5, int(self.rating.value)))
            except ValueError:
                await interaction.response.send_message(
                    "⚠️ Rating must be a number between 1 and 5.", ephemeral=True
                )
                return
            await post_vouch(
                interaction, rating=rating, text=self.explanation.value or None, attachments=[]
            )


class VouchButtonView(discord.ui.View):
    """Bouton rouge persistant qui ouvre le formulaire."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Vouch", style=discord.ButtonStyle.danger, custom_id="vouch:open")
    async def open_form(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(VouchModal())


class Vouch(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(VouchButtonView())

    @app_commands.command(
        name="vouchpanel",
        description="Poster le bouton Vouch dans ce salon",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def vouchpanel(self, interaction: discord.Interaction) -> None:
        await interaction.channel.send(
            content="**Leave a review after your purchase!**",
            view=VouchButtonView(),
        )
        await interaction.response.send_message("✅ Vouch panel posted.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Vouch(bot))
