import logging
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("cogs.downloads")

MEGA_LOADER_URL = "https://mega.nz/folder/w7VjQS6I#wav1HBID04Hj9w-N_2CVaQ"
GITBOOK_GUIDE_URL = "https://trinityshop.gitbook.io/untitled/etapes-obligatoire/1.-virtualisation"


def build_download_embed() -> discord.Embed:
    lines = [
        "> **Portail de téléchargement officiel et vérifié de Core Market.**\n\n"
        "```ansi\n"
        "\u001b[1;32m[ 📥 LIENS OFFICIELS & GUIDE ]\u001b[0m\n"
        "```\n"
        f"▸ **Télécharger le Loader (Mega) :** [Cliquez ici pour télécharger]({MEGA_LOADER_URL})\n"
        f"▸ **Guide d'installation étape par étape :** [Documentation GitBook]({GITBOOK_GUIDE_URL})\n\n"
        "```ansi\n"
        "\u001b[1;33m[ ⚙️ CHECKLIST OBLIGATOIRE AVANT INJECTION ]\u001b[0m\n"
        "```\n"
        "**` 1 ` Virtualisation BIOS :** Doit être activée (`SVM Mode` sur AMD, `Intel VT-x` sur Intel).\n"
        "**` 2 ` Exclusion Antivirus :** Créez un dossier d'exclusion dans Windows Defender (`C:\\Loader\\`).\n"
        "**` 3 ` Conflits Anti-Cheat :** Fermez Riot Vanguard (Valorant) et FaceIt avant de lancer CoD.\n"
        "**` 4 ` Lancement :** Clic droit sur le Loader ➔ *Exécuter en tant qu'administrateur*.\n\n"
        "──────────────────────────────────────────\n"
        "🔐 *Fichiers vérifiés par l'équipe technique Core Market • 100% Clean & Chiffrés.*"
    ]

    embed = discord.Embed(
        title="📥  CORE MARKET — TÉLÉCHARGEMENT OFFICIEL DU LOADER",
        description="\n".join(lines),
        color=discord.Color.from_str("#0070FF"),
    )
    embed.set_footer(text="CORE MARKET • Secure Loader Hub • Ring-0 Hypervisor")
    return embed


class DownloadButtonsView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="Télécharger le Loader (Mega)",
                url=MEGA_LOADER_URL,
                emoji="📥",
                style=discord.ButtonStyle.link,
            )
        )
        self.add_item(
            discord.ui.Button(
                label="Guide d'Installation (GitBook)",
                url=GITBOOK_GUIDE_URL,
                emoji="📖",
                style=discord.ButtonStyle.link,
            )
        )


class DownloadHubView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Accéder aux Téléchargements & Guides",
        emoji="📥",
        style=discord.ButtonStyle.primary,
        custom_id="coremarket_download_hub_btn",
    )
    async def get_download(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = build_download_embed()
        await interaction.response.send_message(embed=embed, view=DownloadButtonsView(), ephemeral=True)


class DownloadsCog(commands.Cog):
    """Secure Download Portal & Installation Assistant."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="download", description="Access the verified official Core Market loader download link and setup guide")
    async def download_cmd(self, interaction: discord.Interaction) -> None:
        embed = build_download_embed()
        await interaction.response.send_message(embed=embed, view=DownloadButtonsView(), ephemeral=True)

    @app_commands.command(name="setup_download_channel", description="Post the permanent download portal panel in the current channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_download_channel_cmd(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="📥  PORTAIL DE TÉLÉCHARGEMENT OFFICIEL",
            description=(
                "> **Téléchargez les versions officielles de nos logiciels et accédez aux guides complets.**\n"
                "> Cliquez sur le bouton ci-dessous pour ouvrir votre accès sécurisé personnel."
            ),
            color=discord.Color.from_str("#0070FF"),
        )
        await interaction.channel.send(embed=embed, view=DownloadHubView())
        await interaction.response.send_message("✅ Panneau de téléchargement posté avec succès !", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DownloadsCog(bot))
