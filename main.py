"""
Point d'entrée du bot de tickets — version SANS base de données.
Toutes les données vivent dans Discord : config dans le footer du panel,
propriétaire du ticket dans le topic du salon. Rien à persister.
- Serveur web aiohttp (keep-alive pour Render/HF, port via $PORT).
"""

import asyncio
import logging
import os

import discord
from aiohttp import web
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
WEB_PORT = int(os.environ.get("PORT", 7860))

COGS = [
    "cogs.tickets",
    "cogs.products",
    "cogs.admin",
    "cogs.vouch",
    "cogs.security",
    "cogs.language",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ticketbot")


class TicketBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # requis pour les transcripts
        intents.members = True          # requis pour les permissions de salon
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        self._synced = False
        for cog in COGS:
            await self.load_extension(cog)
            log.info("Cog chargé : %s", cog)

        await self.tree.sync()
        log.info("Commandes slash synchronisées (global).")

    async def on_ready(self) -> None:
        log.info("Connecté en tant que %s (id=%s)", self.user, self.user.id)
        # Sync par serveur : les nouvelles commandes apparaissent immédiatement
        # (la propagation globale peut prendre jusqu'à 1 h chez Discord).
        if not self._synced:
            self._synced = True
            for guild in self.guilds:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            log.info("Commandes synchronisées sur %d serveur(s).", len(self.guilds))


async def keep_alive() -> None:
    """Auto-ping toutes les 10 min : empêche Render (free) d'endormir le service
    après 15 min sans trafic. RENDER_EXTERNAL_URL est fournie par Render."""
    import aiohttp

    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        log.info("Keep-alive désactivé (pas de RENDER_EXTERNAL_URL).")
        return
    log.info("Keep-alive actif : ping de %s toutes les 10 min.", url)
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await session.get(url, timeout=aiohttp.ClientTimeout(total=30))
            except Exception:
                pass
            await asyncio.sleep(600)


async def run_webserver() -> None:
    """Mini serveur HTTP : répond aux pings d'UptimeRobot pour garder le service éveillé."""
    async def health(_: web.Request) -> web.Response:
        return web.Response(text="Bot is alive")

    app = web.Application()
    app.router.add_get("/", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=WEB_PORT)
    await site.start()
    log.info("Serveur web démarré sur le port %s", WEB_PORT)


async def main() -> None:
    bot = TicketBot()
    await run_webserver()
    asyncio.create_task(keep_alive())
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
