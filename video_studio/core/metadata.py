import random
from typing import Any

VIRAL_HOOKS = [
    "Wait until the end... 💀",
    "Nobody believed this was legit ⚡",
    "Is this the cleanest gameplay ever? 🎯",
    "They reported me for this clutch 😭",
    "How to dominate every lobby in 2026 🚀",
    "POV: You test the 1-hour free trial 🔥",
    "Unstoppable movement & aim assist 👑",
]

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
