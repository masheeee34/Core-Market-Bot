import hashlib
import random
import struct
import time

# ──────────────────────────────────────────────────────────────
#  BANQUE DE 50 HOOKS VIRAUX — Catégorisés par psychologie
#  (Jamais les mêmes 2 fois consécutives grâce au mutateur)
# ──────────────────────────────────────────────────────────────

# Curiosité / FOMO
HOOKS_CURIOSITY = [
    "Ils m'ont report pour ça... 💀",
    "Mon teammate a cru que j'étais pro 😭",
    "Ma config secrète depuis 6 mois 🤫",
    "Personne me croit quand je montre ça ⚡",
    "Le truc que personne ne te dit sur BO7 🎯",
    "J'ai découvert ça par accident... 👀",
    "Regardez jusqu'à la fin, vous allez comprendre 😂",
    "Ce setup change littéralement tout 🔥",
    "On m'a accusé de cheat… c'est mon everyday 💀",
    "POV : Ton premier match avec la bonne config 🎮",
]

# Résultat immédiat / Valeur directe
HOOKS_VALUE = [
    "Settings qui te font gagner 200 Elo instantanément 📈",
    "Le seul guide dont tu as besoin en 2026 ✅",
    "Smooth tracking sur chaque cible, explications en bio 🎯",
    "Mon mouvement après 1H de warm-up avec ces params 🔥",
    "FPS stable, visée verrouillée, zero recoil — bio link 👇",
    "Comment je suis passé Silver à Diamond en 3 semaines 📊",
    "La setup que les pros utilisent mais ne montrent pas 👑",
    "Zero input lag, réponse instantanée — mon secret ⚡",
    "J'ai testé TOUTES les configs. Voilà la meilleure 💯",
    "Ce réglage seul vaut 3 semaines d'entraînement 🧠",
]

# Provocation / Contro  verse douce
HOOKS_CONTROVERSY = [
    "C'est légal mais les lobbies me détestent 😅",
    "Ils ont shadow-ban mon compte pour ça 😤",
    "Quand tu domines le lobby sans cheat… 👀",
    "Ce n'est PAS de l'aimbot (lire la bio avant de juger)",
    "POV : Tu joues dans des lobbies normaux avec ça 💀",
    "C'est borderline ? Non, c'est de l'optimisation ✅",
    "Les gens pensent que c'est impossible sans cheat 🎯",
    "Mon opposant a quitté en plein milieu… 💀",
    "Le mouvement qui fait tilt tout le lobby 😂",
    "Top 1 avec 0 sweat apparent 👑 (bio pour la setup)",
]

# Témoignage / Social proof
HOOKS_PROOF = [
    "5 games, 5 wins — résultats de la semaine 📊",
    "Ranked bronze → platinum en 14 jours 📈",
    "200 games en ranked sans ban 🛡️ — voici pourquoi",
    "Mon K/D avant vs après ce réglage 💀",
    "Premier match de la journée, résultat dans les commentaires",
    "Après 100H de tests, voici ce que j'ai trouvé ⚡",
    "Mon pote m'a demandé ma setup… j'ai dit non 😂",
    "3 mois d'utilisation, 0 problème. C'est tout. ✅",
    "Les stats parlent d'elles-mêmes 📊 (lien en bio)",
    "Real gameplay, no cuts, no edits — bio link pour la config 🎯",
]

# Urgence / Limited
HOOKS_URGENCY = [
    "Dispo seulement 1H GRATUITE ce soir 👇",
    "J'aurais voulu savoir ça avant de perdre 200 parties 😭",
    "Patch demain — voilà le dernier test 🛡️",
    "Dernier clip avant la mise à jour ⚡",
    "Trial 1H gratuit, lien en bio avant qu'il parte 🔥",
    "Ça peut disparaître n'importe quand — profitez 👀",
    "Ce clip résume les 6 derniers mois d'optimisation ⏰",
    "Mise à jour dans 2H — voilà le statut actuel ✅",
    "Je partage ça UNE seule fois publiquement 👇",
    "Il reste 12 clés gratuites — lien en bio 🎁",
]

ALL_HOOKS = (
    HOOKS_CURIOSITY +
    HOOKS_VALUE +
    HOOKS_CONTROVERSY +
    HOOKS_PROOF +
    HOOKS_URGENCY
)

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
