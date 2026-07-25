"""Ticket system — no database.

Where the data lives:
- Panel config (staff role, logs channel) → encoded in the select's custom_id (invisible).
- Ticket owner / staff / logs → encoded in the ticket channel topic.
- Claim state → visible in the ticket embed field.
Each ticket type is routed to its own category (created on the fly if missing).
"""

import discord
from discord.ext import commands

from utils.transcript import generate_transcript

TICKET_TYPES = {
    "buy": {
        "label": "Buy",
        "description": "Purchase a product",
        "category": "Order",
        "color": discord.Color.dark_grey(),
    },
    "support": {
        "label": "Support",
        "description": "Get help with an issue",
        "category": "Support",
        "color": discord.Color.blurple(),
    },
    "media": {
        "label": "Media",
        "description": "Content creator / media request",
        "category": "Media",
        "color": discord.Color.green(),
    },
    "hwid": {
        "label": "HWID Reset",
        "description": "Request a HWID reset",
        "category": "Support",
        "color": discord.Color.red(),
    },
    "reseller": {
        "label": "Reseller",
        "description": "Reseller application",
        "category": "Reseller",
        "color": discord.Color.dark_grey(),
    },
}

UNCLAIMED = "*Nobody yet*"


def encode_topic(owner_id: int, staff_role_id: int, logs_channel_id: int, ticket_type: str, lang: str = "en") -> str:
    return f"ticket|owner:{owner_id}|staff:{staff_role_id}|logs:{logs_channel_id}|type:{ticket_type}|lang:{lang}"


def decode_topic(topic: str | None) -> dict | None:
    if not topic or not topic.startswith("ticket|"):
        return None
    try:
        data = dict(part.split(":", 1) for part in topic.split("|")[1:])
        return {
            "owner_id": int(data["owner"]),
            "staff_role_id": int(data["staff"]),
            "logs_channel_id": int(data["logs"]),
            "type": data["type"],
            "lang": data.get("lang", "en"),
        }
    except (KeyError, ValueError):
        return None


# Ces rôles (créés par /setup) ont accès à tous les tickets, en plus du rôle
# passé à /panel et des administrateurs.
STAFF_ROLE_NAMES = ("Owner", "Staff", "Helper")


def is_staff(member: discord.Member, staff_role_id: int) -> bool:
    return member.guild_permissions.administrator or any(
        r.id == staff_role_id or r.name in STAFF_ROLE_NAMES for r in member.roles
    )


class PanelSelect(
    discord.ui.DynamicItem[discord.ui.Select],
    template=r"panel:(?P<staff>\d+):(?P<logs>\d+)(:(?P<lang>[a-z]+))?",
):
    """Panel select. Config (staff role, logs channel, lang) lives in the custom_id —
    invisible to members, survives restarts, no database."""

    def __init__(self, staff_role_id: int, logs_channel_id: int, lang: str = "en") -> None:
        super().__init__(
            discord.ui.Select(
                custom_id=f"panel:{staff_role_id}:{logs_channel_id}:{lang}",
                placeholder="Sélectionnez une catégorie..." if lang == "fr" else "Select a ticket category...",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label=info["label"],
                        value=key,
                        description=info["description"],
                    )
                    for key, info in TICKET_TYPES.items()
                ],
            )
        )
        self.staff_role_id = staff_role_id
        self.logs_channel_id = logs_channel_id
        self.lang = lang

    @classmethod
    async def from_custom_id(cls, interaction, item, match, /):
        return cls(int(match["staff"]), int(match["logs"]), match["lang"] or "en")

    async def callback(self, interaction: discord.Interaction) -> None:
        ticket_type = self.item.values[0]
        await create_ticket(interaction, ticket_type, self.staff_role_id, self.logs_channel_id, forced_lang=self.lang)
        # Reset the menu for the next member (otherwise the selection stays displayed).
        try:
            await interaction.message.edit(
                view=build_panel_view(self.staff_role_id, self.logs_channel_id, lang=self.lang)
            )
        except discord.HTTPException:
            pass


def build_panel_view(staff_role_id: int, logs_channel_id: int, lang: str = "en") -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(PanelSelect(staff_role_id, logs_channel_id, lang=lang))
    return view


async def create_ticket(
    interaction: discord.Interaction,
    ticket_type: str,
    staff_role_id: int,
    logs_channel_id: int,
    product_key: str | None = None,
    forced_lang: str | None = None,
) -> None:
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    user = interaction.user

    staff_role = guild.get_role(staff_role_id)
    if staff_role is None:
        await interaction.followup.send(
            "⚠️ Staff role not found — ask an admin to repost the panel.", ephemeral=True
        )
        return

    # One open ticket per member (scan ticket topics across the whole server).
    marker = f"owner:{user.id}|"
    for channel in guild.text_channels:
        if channel.topic and channel.topic.startswith("ticket|") and marker in channel.topic:
            await interaction.followup.send(
                f"⚠️ You already have an open ticket: {channel.mention}", ephemeral=True
            )
            return

    info = TICKET_TYPES.get(ticket_type, {
        "label": "Ticket",
        "category": "Order",
        "color": discord.Color.dark_grey(),
    })

    # Determine language priority:
    # 1. product_key (if ends with _fr)
    # 2. forced_lang (if specified on panel)
    # 3. Channel category name or channel name (e.g. if panel is in a channel under "community [ FR ]")
    lang = "en"
    if product_key and product_key.endswith("_fr"):
        lang = "fr"
    elif forced_lang:
        lang = forced_lang
    elif isinstance(interaction.channel, discord.TextChannel):
        ch = interaction.channel
        cat_name = ch.category.name.lower() if ch.category else ""
        ch_name = ch.name.lower()
        if "fr" in cat_name or "fr" in ch_name:
            lang = "fr"

    # Route to matching category (e.g. Order [ FR ] vs Order)
    cat_name = f"{info['category']} [ {lang.upper()} ]" if lang == "fr" else info["category"]
    category = discord.utils.get(guild.categories, name=cat_name)
    if category is None:
        category = discord.utils.get(guild.categories, name=info["category"])
    if category is None:
        category = await guild.create_category(
            cat_name, reason="Ticket category (auto-created)"
        )

    staff_overwrite = discord.PermissionOverwrite(
        view_channel=True, send_messages=True, attach_files=True,
        read_message_history=True, manage_messages=True,
    )
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, attach_files=True, read_message_history=True
        ),
        staff_role: staff_overwrite,
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True, read_message_history=True
        ),
    }
    # Owner, Staff et Helper voient tous les tickets.
    for role_name in STAFF_ROLE_NAMES:
        role = discord.utils.get(guild.roles, name=role_name)
        if role is not None and role != staff_role:
            overwrites[role] = staff_overwrite

    prefix = f"buy-{product_key}" if product_key else ticket_type
    channel_name = f"{prefix}-{user.name}"[:100]

    channel = await category.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        topic=encode_topic(user.id, staff_role_id, logs_channel_id, ticket_type, lang=lang),
    )

    desc_product = f"\n🛒 **Selected Item:** `{product_key.upper()}`" if product_key else ""

    embed = discord.Embed(
        title=f"{info['label']} ticket",
        color=info["color"],
        description=(
            f"Welcome {user.mention}!{desc_product}\n"
            f"A {staff_role.mention} member will assist you shortly with your purchase.\n\n"
            f"🔒 **Close** — closes the ticket (transcript sent to logs)\n"
            f"✋ **Claim** — a staff member takes over the ticket\n"
            f"📝 **Transcript** — export the conversation"
        ),
    )
    embed.add_field(name="Claimed by", value=UNCLAIMED)
    await channel.send(content=f"{user.mention} {staff_role.mention}", embed=embed, view=TicketView())
    await interaction.followup.send(f"✅ Your ticket is open: {channel.mention}", ephemeral=True)


class TicketView(discord.ui.View):
    """Buttons inside each ticket. Persistent — everything is re-read from the channel."""

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", emoji="✋", style=discord.ButtonStyle.primary, custom_id="ticket:claim")
    async def claim(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        ticket = decode_topic(interaction.channel.topic)
        if ticket is None:
            await interaction.response.send_message("⚠️ Invalid ticket.", ephemeral=True)
            return
        if not is_staff(interaction.user, ticket["staff_role_id"]):
            await interaction.response.send_message("⛔ Staff only.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]
        if embed.fields and embed.fields[0].value != UNCLAIMED:
            await interaction.response.send_message(
                f"⚠️ Already claimed by {embed.fields[0].value}.", ephemeral=True
            )
            return

        embed.set_field_at(0, name="Claimed by", value=interaction.user.mention)
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(
            f"✋ {interaction.user.mention} claimed this ticket."
        )

    @discord.ui.button(label="Transcript", emoji="📝", style=discord.ButtonStyle.secondary, custom_id="ticket:transcript")
    async def transcript(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        ticket = decode_topic(interaction.channel.topic)
        if ticket is None or not is_staff(interaction.user, ticket["staff_role_id"]):
            await interaction.response.send_message("⛔ Staff only.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        file = await generate_transcript(interaction.channel)
        await interaction.followup.send("📝 Ticket transcript:", file=file, ephemeral=True)

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        ticket = decode_topic(interaction.channel.topic)
        if ticket is None:
            await interaction.response.send_message("⚠️ Invalid ticket.", ephemeral=True)
            return
        if interaction.user.id != ticket["owner_id"] and not is_staff(interaction.user, ticket["staff_role_id"]):
            await interaction.response.send_message("⛔ You can't close this ticket.", ephemeral=True)
            return
        await interaction.response.send_message(
            "⚠️ Close this ticket?", view=ConfirmCloseView(ticket), ephemeral=True
        )


class ConfirmCloseView(discord.ui.View):
    """Ephemeral confirmation before closing (60s, no need to persist)."""

    def __init__(self, ticket: dict) -> None:
        super().__init__(timeout=60)
        self.ticket = ticket

    @discord.ui.button(label="Yes, close", emoji="🔒", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="🔒 Closing…", view=None)
        channel = interaction.channel
        guild = interaction.guild

        file = await generate_transcript(channel)
        logs_channel = guild.get_channel(self.ticket["logs_channel_id"])
        if logs_channel is not None:
            owner = guild.get_member(self.ticket["owner_id"])
            embed = discord.Embed(
                title=f"🔒 Ticket closed — {channel.name}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow(),
                description=(
                    f"**Owner:** {owner.mention if owner else self.ticket['owner_id']}\n"
                    f"**Closed by:** {interaction.user.mention}\n"
                    f"**Type:** {TICKET_TYPES[self.ticket['type']]['label']}"
                ),
            )
            await logs_channel.send(embed=embed, file=file)

        await channel.delete(reason=f"Ticket closed by {interaction.user}")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Close cancelled.", view=None)


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        # Re-register persistent components on startup: panel selects and ticket
        # buttons keep working after every redeploy.
        self.bot.add_dynamic_items(PanelSelect)
        self.bot.add_view(TicketView())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
