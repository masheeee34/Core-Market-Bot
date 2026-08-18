"""
Core Market Multi-Channel Farm & Account Kits.
Provides structured channel identities, rotating bio templates, anti-duplicate description variations,
and multi-account video distribution strategies for TikTok, YouTube Shorts, and Instagram Reels.
"""

from typing import Any
import random

# ──────────────────────────────────────────────────────────────
#  12 BRANDED CORE MARKET CHANNEL PROFILES
# ──────────────────────────────────────────────────────────────

CORE_MARKET_CHANNELS = [
    {
        "id": "coremarket_clips",
        "handle": "@coremarket.clips",
        "name": "Core Market Clips 🎯",
        "niche": "Warzone & BO6 Clutches",
        "tagline": "Zero Recoil & FPS Precision Configs",
        "bio": "🎯 Zero Recoil & Smooth Tracking Configs\n⚡ 100% Undetected on Current Patch\n🎁 1-Hour FREE Trial Link Below 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Gold / Neon Yellow",
    },
    {
        "id": "coremarket_warzone",
        "handle": "@coremarket.warzone",
        "name": "Core Market Warzone 🔥",
        "niche": "Warzone Ranked & Meta",
        "tagline": "Undetected Warzone / BO6 Setups & Settings",
        "bio": "🔥 Daily Warzone 1v4 Clutches & Meta Builds\n🛡️ Updated for Today's Patch (GREEN ✅)\n⚡ Test 1-Hour FREE in Bio 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Dark Flame / Amber",
    },
    {
        "id": "coremarket_fps",
        "handle": "@coremarket_fps",
        "name": "Core Market FPS 🏆",
        "niche": "FPS Optimization & Aim",
        "tagline": "Level Up Your Aim & Movement Instantly",
        "bio": "🏆 Pro Crosshair Placement & Smooth Aim\n📈 Gain +200 ELO in Ranked Matches\n🎁 Free 1-Hour Test Key in Bio 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Emerald / Cyan",
    },
    {
        "id": "coremarket_meta",
        "handle": "@coremarket.meta",
        "name": "Core Market Meta 📊",
        "niche": "Meta Weapon Builds & Tuning",
        "tagline": "Current Meta Weapon Builds & Aim Configs",
        "bio": "📊 Weapon Tuning & Zero-Recoil Setups\n🎮 Tested by Top Ranked Players\n⚡ 1H Free Trial Available Below 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Cyber Blue / Violet",
    },
    {
        "id": "coremarket_bo6",
        "handle": "@coremarket_bo6",
        "name": "Core Market BO6 🎮",
        "niche": "Black Ops 6 Multiplayer & Ranked",
        "tagline": "Daily Ranked Highlights & Undetected Configs",
        "bio": "🎮 BO6 Ranked Highlights & Best Configs\n💀 Dominating Lobbies Daily\n🎁 Get Your 1-Hour Free Key in Bio 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Crimson / Black",
    },
    {
        "id": "core_aimvault",
        "handle": "@core.aimvault",
        "name": "Core Aim Vault 🤫",
        "niche": "Headshot Only Movement & Aim Lock",
        "tagline": "Headshot Only Movement & Tracking Secrets",
        "bio": "🤫 The Secret Setup Pro Players Use\n🎯 Clean Headshots & Fast Reaction\n⚡ 1H Free Trial in Profile Link 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Midnight Stealth / Gold",
    },
    {
        "id": "coremarket_ranked",
        "handle": "@coremarket_ranked",
        "name": "Core Market Ranked 👑",
        "niche": "Road to Top 250 Ranked",
        "tagline": "Road to Top 250 Ranked / Zero Recoil Setup",
        "bio": "👑 Road to Top 250 Ranked Grind\n📊 200+ Games Without Ban (Undetected)\n🎁 Grab 1H Free Trial Key Below 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Royal Gold / Obsidian",
    },
    {
        "id": "coremarket_zero",
        "handle": "@coremarket_zero",
        "name": "Core Market Zero 🎯",
        "niche": "Zero Recoil Highlights",
        "tagline": "Zero Recoil is Pure Optimization",
        "bio": "🎯 Absolute Zero Recoil on Every Weapon\n⚡ Plug & Play Performance Config\n🎁 1-Hour FREE Trial Link in Bio 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Pure Neon Yellow",
    },
    {
        "id": "coremarket_tactical",
        "handle": "@coremarket.tactical",
        "name": "Core Market Tactical 🛡️",
        "niche": "Tactical Movement & Angles",
        "tagline": "Tactical Gameplay & Clean Tracking",
        "bio": "🛡️ Tactical Crosshair Control & Angles\n✅ Safe & Undetected Architecture\n⚡ Free Test Key in Bio Link 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Military Olive / Tactical Black",
    },
    {
        "id": "coremarket_gg",
        "handle": "@coremarket_gg",
        "name": "Core Market GG 💥",
        "niche": "Viral Clutch Gaming",
        "tagline": "Insane Clutch Highlights & Free Trial Configs",
        "bio": "💥 Pure Clutch Gaming Moments\n🎯 When the entire squad relies on you\n🎁 1H Free Trial Link in Profile 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Electric Purple / Neon",
    },
    {
        "id": "coremarket_vortex",
        "handle": "@coremarket.vortex",
        "name": "Core Market Vortex 🚀",
        "niche": "Aggressive Gameplay & Speed",
        "tagline": "Dominate every lobby effortlessly",
        "bio": "🚀 High Speed Movement & Aggressive Play\n⚡ 0 Input Lag • Maximum FPS\n🎁 Get 1-Hour Free Access in Bio 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Vortex Violet / Cyan",
    },
    {
        "id": "coremarket_prime",
        "handle": "@coremarket_prime",
        "name": "Core Market Prime 👑",
        "niche": "High-Tier Gameplay Showcase",
        "tagline": "High-tier movement & aim tracking setups",
        "bio": "👑 Premium Precision Configs & Demos\n🎯 Tested on Latest Game Patch\n⚡ 1-Hour FREE Trial in Bio 👇",
        "cta_link": "https://discord.gg/coremarket",
        "avatar_theme": "Platinum / Gold",
    },
]

# ──────────────────────────────────────────────────────────────
#  10+ ANTI-DUPLICATE VIRAL DESCRIPTION TEMPLATES
# ──────────────────────────────────────────────────────────────

DESCRIPTION_TEMPLATES = [
    # Template 1: Curiosity & Secret
    (
        "{hook}\n\n"
        "They thought this was impossible on normal settings... 💀 "
        "Testing the zero-recoil setup on today's patch. 100% smooth tracking & crisp response.\n\n"
        "⚡ Available for 1-HOUR FREE TRIAL right now (Link in Bio / Profile)!\n\n"
        "{hashtags}"
    ),
    # Template 2: Value & Ranked Tutorial
    (
        "{hook}\n\n"
        "How to lock your crosshair on targets with zero camera shake 🎯 "
        "Full setup guide & key generator available in our Discord community.\n\n"
        "🎁 Grab your 1-Hour Free Test Key in the bio link before it resets!\n\n"
        "{hashtags}"
    ),
    # Template 3: Ranked Grind Proof
    (
        "{hook}\n\n"
        "Ranking up 3 divisions in one weekend with this exact configuration 📈 "
        "Stable frames, 0 input delay, and perfect recoil compensation.\n\n"
        "👇 Check bio / description for your instant 1-Hour Free Trial.\n\n"
        "{hashtags}"
    ),
    # Template 4: Patch Update Status (Green)
    (
        "{hook}\n\n"
        "New patch dropped today and status is confirmed GREEN 🟢 "
        "Running completely undetected and fully optimized.\n\n"
        "⚡ Claim your 1-Hour Free Trial via link in bio!\n\n"
        "{hashtags}"
    ),
    # Template 5: Clutch & Killcam Reaction
    (
        "{hook}\n\n"
        "1v4 clutch in Diamond lobbies 🔥 The death comms were crazy 😂 "
        "Raw gameplay capture with zero lag.\n\n"
        "🎯 Setup & free trial keys available in my bio link!\n\n"
        "{hashtags}"
    ),
    # Template 6: Comparison / No Cheat Proof
    (
        "{hook}\n\n"
        "Pure mechanical optimization without breaking game rules ✅ "
        "Smooth tracking on every moving target.\n\n"
        "🎁 Try it yourself for 1-Hour FREE — Link in Bio 👇\n\n"
        "{hashtags}"
    ),
    # Template 7: Movement & Sensitivity
    (
        "{hook}\n\n"
        "My movement and centering after dialing in these parameters 🎮 "
        "If you're still playing on default settings, you're missing out.\n\n"
        "⚡ Get the config + 1H trial key in bio!\n\n"
        "{hashtags}"
    ),
    # Template 8: Urgency / Limited Keys
    (
        "{hook}\n\n"
        "Dropping the setup for tonight's ranked session 🏆 "
        "Limited 1-Hour trial slots available for new members.\n\n"
        "👇 Tap the profile link to claim yours instantly!\n\n"
        "{hashtags}"
    ),
]

PINNED_COMMENT_TEMPLATES = [
    "🎁 Free 1-Hour Trial available right now! Check my profile / bio link to claim your key ⚡",
    "👇 Link in bio for the exact config & 1-Hour Free Trial! Join our Discord community 🎯",
    "⚡ Tested on today's patch (GREEN 🟢). Get your free 1-hour test key in bio!",
    "🎯 Want this exact zero-recoil setup? Head to the link in my profile for a 1H free trial 🎁",
    "👑 Profile link has the full setup + 1-Hour FREE Trial. Be quick before slots close! 🚀",
]

ROTATING_HASHTAG_SETS = [
    "#BO7 #Warzone #BlackOps6 #WarzoneClips #CallOfDuty #GamingSetup #FPSGames #CoDHighlights #FYP",
    "#WarzoneMeta #CallOfDutyWarzone #WarzoneLoadout #GamingTok #GamingCommunity #FPSClutch #ViralShorts",
    "#ZeroRecoil #GamingSetup #CoDClips #RankedWarzone #Top250 #GamerMoment #TikTokGaming #ForYou",
    "#BlackOps6Clips #CoDBOCW #FPSAim #CrosshairLock #AimTraining #GamingLife #ReelsGaming #FYP",
    "#WarzoneClips #GamingHighlight #ClutchOrKick #ApexLegends #ValorantClips #FPSGaming #Trending",
]


def get_channel_profiles() -> list[dict[str, Any]]:
    """Returns the list of all 12 Core Market channel presets."""
    return CORE_MARKET_CHANNELS


def generate_multichannel_pack(
    base_title: str | None = None,
    hook_text: str | None = None,
    num_channels: int = 3,
) -> list[dict[str, Any]]:
    """
    Generates tailored, anti-duplicate post packages for multiple channels.
    Each channel gets a distinct Title, Description, Pinned Comment, and Hashtag set.
    """
    hook = hook_text or base_title or "POV: You finally found the zero-recoil config 😳"
    selected_channels = random.sample(CORE_MARKET_CHANNELS, min(num_channels, len(CORE_MARKET_CHANNELS)))

    pack = []
    for idx, chan in enumerate(selected_channels):
        desc_template = DESCRIPTION_TEMPLATES[idx % len(DESCRIPTION_TEMPLATES)]
        hashtags = ROTATING_HASHTAG_SETS[idx % len(ROTATING_HASHTAG_SETS)]
        pinned = PINNED_COMMENT_TEMPLATES[idx % len(PINNED_COMMENT_TEMPLATES)]

        # Unique Title Variation
        if idx == 0:
            title = hook
        elif idx == 1:
            title = f"{hook} 🎯 (WARZONE / BO6)"
        elif idx == 2:
            title = f"Secret Setup: {hook}"
        elif idx == 3:
            title = f"{hook} 💀 (100% Undetected)"
        else:
            title = f"{hook} 🔥 (1H Free Trial in Bio)"

        description = desc_template.format(hook=title, hashtags=hashtags)

        pack.append({
            "channel_id": chan["id"],
            "channel_name": chan["name"],
            "channel_handle": chan["handle"],
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "pinned_comment": pinned,
            "bio_cta": chan["bio"],
        })

    return pack
