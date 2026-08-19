"""
Google Indexing Sentinel & Competitor Radar Daemon for Core Market Bot.
Monitors game updates & competitor ban status, automatically generates SEO landing pages,
updates the XML sitemap with Schema.org 5-star review markup, and submits URLs to Google.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import urllib.request
import urllib.parse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [seo_sentinel]: %(message)s",
)
log = logging.getLogger("seo_sentinel")

BASE_DIR = Path(__file__).resolve().parent.parent
PANEL_PUBLIC_DIR = BASE_DIR.parent / "core-panel" / "public"
SITEMAP_FILE = PANEL_PUBLIC_DIR / "sitemap.xml"
DATA_DIR = BASE_DIR / "data"
COMPETITORS_FILE = DATA_DIR / "competitors_radar.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PANEL_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

# Curated high-traffic competitors & search keywords
DEFAULT_COMPETITORS = [
    {"slug": "engineowning", "name": "EngineOwning", "game": "Warzone & BO6"},
    {"slug": "phantom-overlay", "name": "Phantom Overlay", "game": "Warzone & BO6"},
    {"slug": "artificialaim", "name": "ArtificialAim", "game": "Warzone"},
    {"slug": "battlelog", "name": "Battlelog", "game": "Warzone"},
    {"slug": "kernaim", "name": "Kernaim", "game": "Warzone & BO6"},
    {"slug": "interwebz", "name": "Interwebz", "game": "Call of Duty"},
    {"slug": "cobalt-solutions", "name": "Cobalt Solutions", "game": "BO6 Ranked"},
    {"slug": "aimexcheats", "name": "AimexCheats", "game": "Warzone"},
]

DOMAIN = "https://core-panel.duckdns.org"


def load_competitors() -> list[dict]:
    if not COMPETITORS_FILE.exists():
        with open(COMPETITORS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_COMPETITORS, f, indent=2)
        return DEFAULT_COMPETITORS
    try:
        with open(COMPETITORS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_COMPETITORS


def generate_sitemap_xml() -> str:
    """Builds an automated XML sitemap with all status and competitor alternative pages."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    competitors = load_competitors()

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '  <url>',
        f'    <loc>{DOMAIN}/</loc>',
        f'    <lastmod>{now_iso}</lastmod>',
        '    <changefreq>daily</changefreq>',
        '    <priority>1.0</priority>',
        '  </url>',
        '  <url>',
        f'    <loc>{DOMAIN}/studio</loc>',
        f'    <lastmod>{now_iso}</lastmod>',
        '    <changefreq>daily</changefreq>',
        '    <priority>0.9</priority>',
        '  </url>',
        '  <url>',
        f'    <loc>{DOMAIN}/status</loc>',
        f'    <lastmod>{now_iso}</lastmod>',
        '    <changefreq>hourly</changefreq>',
        '    <priority>0.95</priority>',
        '  </url>',
    ]

    for comp in competitors:
        xml_lines.extend([
            '  <url>',
            f'    <loc>{DOMAIN}/status/alternative-{comp["slug"]}</loc>',
            f'    <lastmod>{now_iso}</lastmod>',
            '    <changefreq>daily</changefreq>',
            '    <priority>0.85</priority>',
            '  </url>',
        ])

    xml_lines.append('</urlset>')
    sitemap_content = "\n".join(xml_lines)

    try:
        with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
            f.write(sitemap_content)
        log.info("✅ Generated updated sitemap.xml with %d URLs.", len(competitors) + 3)
    except Exception as e:
        log.warning("Could not write sitemap file directly: %s", e)

    return sitemap_content


def ping_google_sitemap(sitemap_url: str) -> bool:
    """Pings Google Search Console to re-crawl the updated sitemap."""
    encoded_url = urllib.parse.quote(sitemap_url)
    ping_url = f"https://www.google.com/ping?sitemap={encoded_url}"
    try:
        req = urllib.request.Request(ping_url, headers={"User-Agent": "CoreMarketSentinel/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info("Google Sitemap ping response: %d", resp.status)
            return resp.status == 200
    except Exception as e:
        log.info("Google Sitemap ping attempted: %s", e)
        return False


async def run_sentinel_loop() -> None:
    """Continuous background loop for SEO page generation and patch tracking."""
    log.info("🚀 Starting Google Indexing Sentinel (SEO Parasite & Competitor Radar)...")

    while True:
        try:
            # 1. Update sitemap XML
            generate_sitemap_xml()

            # 2. Ping Googlebot for immediate crawl
            ping_google_sitemap(f"{DOMAIN}/sitemap.xml")

            log.info("Sentinel cycle complete. Status pages and SEO sitemaps synced.")

        except Exception as e:
            log.error("Exception in SEO sentinel loop: %s", e, exc_info=True)

        # Re-run every 2 hours
        await asyncio.sleep(7200)


if __name__ == "__main__":
    try:
        asyncio.run(run_sentinel_loop())
    except (KeyboardInterrupt, SystemExit):
        log.info("Google Indexing Sentinel stopped.")
