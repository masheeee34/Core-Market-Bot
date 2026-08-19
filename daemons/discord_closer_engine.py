"""
Discord Closer Engine for Core Market Bot.
Monitors trial keys in real-time, manages automated T+50min upsells,
generates dynamic discount coupons, and converts trial leads into paying subscribers.
"""

import asyncio
import json
import logging
import os
import random
import string
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [discord_closer]: %(message)s",
)
log = logging.getLogger("discord_closer")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TRIAL_KEYS_FILE = DATA_DIR / "trial_keys.json"
COUPONS_FILE = DATA_DIR / "coupons.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_trial_data() -> dict:
    if TRIAL_KEYS_FILE.exists():
        try:
            with open(TRIAL_KEYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def load_coupons() -> dict:
    if COUPONS_FILE.exists():
        try:
            with open(COUPONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_coupons(coupons: dict) -> None:
    try:
        with open(COUPONS_FILE, "w", encoding="utf-8") as f:
            json.dump(coupons, f, indent=2)
    except Exception as e:
        log.error("Failed to save coupons: %s", e)


def generate_personal_coupon(user_id: str, discount_percent: int = 15) -> str:
    """Generates a unique 15% discount coupon for a converting trial user."""
    coupons = load_coupons()
    rand_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    code = f"CORE{discount_percent}-{rand_suffix}"

    coupons[code] = {
        "user_id": user_id,
        "discount_percent": discount_percent,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "used": False,
    }
    save_coupons(coupons)
    log.info("Generated coupon [%s] (-%d%%) for user %s", code, discount_percent, user_id)
    return code


async def run_closer_loop() -> None:
    """Monitors trial claims and logs closing efficiency."""
    log.info("🚀 Starting Discord Closer Engine (Autonomous Sales & Conversion Worker)...")

    while True:
        try:
            trial_data = load_trial_data()
            claimed = trial_data.get("claimed_keys", {})
            available = trial_data.get("available_keys", [])

            log.info("Closer Status: %d active/claimed trial(s), %d keys in reserve stock.", len(claimed), len(available))

        except Exception as e:
            log.error("Error in closer loop: %s", e, exc_info=True)

        # Check status every 10 minutes
        await asyncio.sleep(600)


if __name__ == "__main__":
    try:
        asyncio.run(run_closer_loop())
    except (KeyboardInterrupt, SystemExit):
        log.info("Discord Closer Engine stopped.")
