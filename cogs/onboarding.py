import logging
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("cogs.onboarding")


class WelcomeTrialButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎁 Réclamer ma Clé Gratuite 1H",
        emoji="⚡",
        style=discord.ButtonStyle.success,
        custom_id="onboarding_claim_free_trial",
    )
    async def claim_trial(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        trial_cog = interaction.client.get_cog("Trial")
        if trial_cog and hasattr(trial_cog, "deliver_key_to_user"):
            await trial_cog.deliver_key_to_user(interaction, interaction.user)
        else:
            await interaction.response.send_message(
                "👉 Rendez-vous dans le salon <#🎁・free-trial> pour réclamer votre clé en 1 clic !",
                ephemeral=True,
            )


class OnboardingCog(commands.Cog):
    """Automated Customer Acquisition, Instant Free Trial Onboarding & Conversion Engine."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Sends a high-converting welcome DM with an instant Free Trial key & invite rewards."""
        if member.bot:
            return

        embed = discord.Embed(
            title="🎁  BIENVENUE SUR CORE MARKET — VOTRE ESSAI GRATUIT 1H",
            description=(
                f"> **Salut {member.mention} ! Bienvenue sur le serveur officiel Core Market.**\n\n"
                "Pour vous prouver la qualité et l'indétectabilité de nos logiciels, **nous vous offrons 1 Heure d'accès gratuit immédiat** !\n\n"
                "```ansi\n"
                "\u001b[1;32m[ ⚡ VOS AVANTAGES DE BIENVENUE ]\u001b[0m\n"
                "```\n"
                "▸ **1 Clé Free Trial (1H) :** Valable sur Trinity Spectre ou M-Core.\n"
                "▸ **Programme d'invitation :** Invitez 3 amis ➔ Gagnez **1 Clé 24H Complète** !\n"
                "▸ **Support 24/7 :** Posez n'importe quelle question en répondant directement à ce MP.\n\n"
                "──────────────────────────────────────────\n"
                "👇 *Cliquez sur le bouton ci-dessous pour générer votre clé d'essai instantanément !*"
            ),
            color=discord.Color.from_str("#00FF66"),
        )
        embed.set_footer(text="CORE MARKET • 100% Streamproof & Ring-0 Hypervisor • Test Gratuit")

        try:
            await member.send(embed=embed, view=WelcomeTrialButton())
            log.info("Sent onboarding welcome DM with free trial to %s", member.name)
        except Exception as e:
            log.debug("Could not DM new member %s: %s", member.name, e)

    @app_commands.command(name="partner", description="Apply for a Streamer / TikTok Creator Sponsorship & Free Weekly Keys")
    async def partner_cmd(self, interaction: discord.Interaction, tiktok_or_youtube_link: str, estimated_views: str) -> None:
        await interaction.response.defer(ephemeral=True)

        log_ch = discord.utils.get(interaction.guild.text_channels, name="📜・ʟᴏɢꜱ-ᴛɪᴄᴋᴇᴛꜱ") or discord.utils.get(
            interaction.guild.text_channels, name="logs-tickets"
        )

        if log_ch:
            embed = discord.Embed(
                title="🎬  NOUVELLE CANDIDATURE PARTENAIRE / CRÉATEUR",
                description=(
                    f"▸ **Créateur :** {interaction.user.mention} (`{interaction.user.name}`)\n"
                    f"▸ **Lien Chaîne / TikTok :** {tiktok_or_youtube_link}\n"
                    f"▸ **Vues estimées par vidéo :** `{estimated_views}`\n"
                ),
                color=discord.Color.gold(),
            )
            await log_ch.send(embed=embed)

        await interaction.followup.send(
            "✅ Votre candidature partenaire a été transmise aux administrateurs ! Vous recevrez votre clé sponsorisée après vérification.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OnboardingCog(bot))
