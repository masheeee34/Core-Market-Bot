"""
Master Daemon Supervisor for Core Market Bot.
Launches and supervises all 6 background autonomous workers:
1. Clip Miner (Autonomous Gameplay Harvester)
2. Studio Pipeline Worker (9:16 Video Factory)
3. Auto Publisher (Social Distribution)
4. Livestream Relay (24/7 RTMP Kick/YouTube Engine)
5. Google Indexing Sentinel (SEO Radar)
6. Discord Closer Engine (Sales & Conversion)
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [master_daemon]: %(message)s",
)
log = logging.getLogger("master_daemon")

BASE_DIR = Path(__file__).resolve().parent.parent
DAEMONS_DIR = BASE_DIR / "daemons"

WORKERS = [
    {"name": "clip_miner", "script": DAEMONS_DIR / "clip_miner_daemon.py"},
    {"name": "studio_worker", "script": DAEMONS_DIR / "studio_pipeline_worker.py"},
    {"name": "auto_publisher", "script": DAEMONS_DIR / "auto_publisher_daemon.py"},
    {"name": "livestream_relay", "script": DAEMONS_DIR / "livestream_relay_daemon.py"},
    {"name": "seo_sentinel", "script": DAEMONS_DIR / "google_indexing_sentinel.py"},
    {"name": "discord_closer", "script": DAEMONS_DIR / "discord_closer_engine.py"},
]


async def run_supervised_worker(worker: dict) -> None:
    """Runs a single worker process and automatically restarts it if it exits."""
    name = worker["name"]
    script = str(worker["script"])

    while True:
        log.info("🚀 [START] Launching %s (%s)...", name, script)
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Stream output
            async def read_stream(stream, prefix):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    log.info("[%s] %s", prefix, line.decode().strip())

            await asyncio.gather(
                read_stream(proc.stdout, name),
                read_stream(proc.stderr, f"{name}:ERR"),
            )

            await proc.wait()
            log.warning("⚠️ [%s] Process exited with code %d. Restarting in 5s...", name, proc.returncode)

        except Exception as e:
            log.error("💥 [%s] Worker crash: %s. Restarting in 10s...", name, e)

        await asyncio.sleep(5)


async def main() -> None:
    log.info("=" * 60)
    log.info("🌟 CORE MARKET AUTONOMOUS MASTER DAEMON (BOT MÈRE) 🌟")
    log.info("=" * 60)
    log.info("Supervising %d autonomous background workers 24/7...", len(WORKERS))

    tasks = [asyncio.create_task(run_supervised_worker(w)) for w in WORKERS]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Master Daemon stopped.")
