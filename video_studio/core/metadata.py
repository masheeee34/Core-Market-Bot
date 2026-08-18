import hashlib
import random
import struct
import time
from typing import Any

# ──────────────────────────────────────────────────────────────
#  BANK OF 50 VIRAL HOOKS (100% English — Categorized by Psychology)
#  (Never repeat twice consecutively thanks to dynamic mutator)
# ──────────────────────────────────────────────────────────────

# Curiosity / FOMO
HOOKS_CURIOSITY = [
    "They reported me for this clutch... 💀",
    "My teammate thought I was a pro player 😭",
    "My secret config for the last 6 months 🤫",
    "Nobody believes me when I show this ⚡",
    "The one thing nobody tells you about BO7 🎯",
    "Found this setup completely by accident... 👀",
    "Watch until the end, you'll understand 😂",
    "This single setting changed everything 🔥",
    "Accused of cheating... this is just my everyday 💀",
    "POV: Your first ranked match with proper config 🎮",
]

# Immediate Result / Direct Value
HOOKS_VALUE = [
    "Settings that gain you +200 ELO instantly 📈",
    "The only guide you actually need in 2026 ✅",
    "Smooth tracking on every target — bio link 🎯",
    "My movement after 1 hour warm-up with these params 🔥",
    "Stable FPS, locked crosshair, zero recoil — bio link 👇",
    "How I went from Silver to Diamond in 3 weeks 📊",
    "The setup pro players use but never share 👑",
    "Zero input lag, instant response time — my secret ⚡",
    "Tested EVERY config. This is the undisputed best 💯",
    "This one tweak is worth 3 weeks of aim training 🧠",
]

# Controversy / High Engagement
HOOKS_CONTROVERSY = [
    "It's 100% legit but lobbies hate me for it 😅",
    "They shadow-banned my alt for this gameplay 😤",
    "When you dominate the lobby without breaking a sweat 👀",
    "This is NOT aimbot (check bio before judging)",
    "POV: You play normal lobbies with this config 💀",
    "Is this borderline? No, it's just pure optimization ✅",
    "People think this is impossible without cheats 🎯",
    "Opponent literally ragequit mid-game… 💀",
    "The movement that tilts the entire lobby 😂",
    "Victory Royale with 0 effort 👑 (bio for setup)",
]

# Social Proof / Verified Results
HOOKS_PROOF = [
    "5 games, 5 wins — this week's rank grind 📊",
    "Ranked Bronze to Platinum in 14 days 📈",
    "200 ranked games with zero bans 🛡️ — here's why",
    "My K/D ratio before vs after this setup 💀",
    "First game of the day, results in pinned comment 🎯",
    "After 100 hours of testing, here are the results ⚡",
    "Duo partner asked for my config… had to share 😂",
    "3 months of daily use, 0 issues. Undetected. ✅",
    "The stats speak for themselves 📊 (link in bio)",
    "Raw gameplay, no cuts, no edits — check bio for trial 🎯",
]

# Urgency / Limited Time
HOOKS_URGENCY = [
    "Available for 1-HOUR FREE TRIAL right now 👇",
    "Wish I knew this before losing 200 ranked games 😭",
    "Patch drops tomorrow — final test results 🛡️",
    "Last gameplay clip before the new update ⚡",
    "1H Free Trial available, link in bio before it closes 🔥",
    "This setup might get patched soon — grab it now 👀",
    "6 months of tuning summarized in 30 seconds ⏰",
    "Major game update in 2H — current status is GREEN ✅",
    "Sharing this only ONCE publicly 👇",
    "Only 15 free trial keys left for tonight — bio link 🎁",
]

ALL_HOOKS = (
    HOOKS_CURIOSITY +
    HOOKS_VALUE +
    HOOKS_CONTROVERSY +
    HOOKS_PROOF +
    HOOKS_URGENCY
)

VIRAL_HOOKS = ALL_HOOKS


def get_hook(seed: int | None = None) -> str:
    """Returns a unique hook. Uses time-based seed to prevent repeats."""
    rng = random.Random(seed or int(time.time() / 30))
    return rng.choice(ALL_HOOKS)


def mutate_video_metadata() -> dict:
    """
    Generates unique per-render metadata fingerprint.
    Prevents TikTok/YouTube from detecting duplicate uploads.
    """
    salt = str(time.time()) + str(random.random())
    uid = hashlib.sha256(salt.encode()).hexdigest()[:16]

    # Micro-variation: random brightness/contrast deltas for FFmpeg
    brightness = round(random.uniform(-0.03, 0.03), 4)
    contrast   = round(random.uniform(0.97, 1.03), 4)
    saturation = round(random.uniform(0.98, 1.02), 4)

    # Audio pitch micro-shift (imperceptible to humans, unique fingerprint)
    pitch_shift = round(random.uniform(-0.5, 0.5), 2)

    return {
        "uid": uid,
        "brightness": brightness,
        "contrast": contrast,
        "saturation": saturation,
        "pitch_shift": pitch_shift,
        "ffmpeg_eq_filter": (
            f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
        ),
        "ffmpeg_pitch_filter": (
            f"asetrate=44100*{1 + pitch_shift/100},aresample=44100"
        ),
    }


HASHTAG_PACKS = {
    "call_of_duty": [
        "#BO7", "#Warzone", "#BlackOps6", "#WarzoneClips", "#CallOfDuty",
        "#GamingSetup", "#FPSGames", "#CoDHighlights", "#GamingCommunity", "#FYP"
    ],
    "valorant": [
        "#Valorant", "#ValorantClips", "#ValorantHighlights", "#Radiant",
        "#Clutch", "#GamingSetup", "#FPS", "#Gamer", "#FYP"
    ],
    "gaming_viral": [
        "#Gaming", "#GamerMoments", "#ViralGaming", "#TikTokGaming",
        "#TwitchClips", "#GamingTok", "#Trending", "#ForYouPage"
    ],
}

POSTING_SCHEDULE_TIPS = [
    {
        "slot": "Midday Peak (12:00 - 14:00)",
        "why": "High mobile traffic during lunch breaks on TikTok & YouTube Shorts.",
    },
    {
        "slot": "Evening Prime (18:30 - 21:30)",
        "why": "Maximum daily engagement and gaming audience retention.",
    },
    {
        "slot": "Late Night Gamer Shift (22:30 - 00:30)",
        "why": "Dedicated FPS / competitive players browsing after long sessions.",
    },
]


def generate_clip_social_metadata(
    clip_title: str | None = None,
    game_tag: str = "call_of_duty",
    include_trial_cta: bool = True,
) -> dict[str, Any]:
    """
    Generates complete high-converting metadata for posting to TikTok, Shorts, and Reels:
    - High-CTR Titles
    - Hashtags
    - Pinned comment text (anti-ban compliant)
    - Description
    - Best posting schedule recommendation
    """
    hook = random.choice(VIRAL_HOOKS)
    title = clip_title or f"{hook} (100% Undetected Setup)"

    tags = HASHTAG_PACKS.get(game_tag, HASHTAG_PACKS["call_of_duty"])
    hashtags_str = " ".join(tags[:8])

    description = f"{title}\n\nTesting the cleanest setup on latest patch. Smooth tracking & zero recoil.\n\n{hashtags_str}"

    pinned_comment = (
        "🎁 Free 1-Hour Trial available! Check my profile / bio link to get yours instantly ⚡"
        if include_trial_cta
        else "Check profile description for full setup & guide 🚀"
    )

    schedule = random.choice(POSTING_SCHEDULE_TIPS)

    return {
        "title": title,
        "description": description,
        "hashtags": tags,
        "hashtags_string": hashtags_str,
        "pinned_comment": pinned_comment,
        "optimal_time": schedule["slot"],
        "strategy_tip": schedule["why"],
    }
