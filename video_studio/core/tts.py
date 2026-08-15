import asyncio
import logging
import os
from typing import Any

import edge_tts

log = logging.getLogger("studio.tts")

VOICES = {
    "en_gamer_christopher": {
        "name": "Christopher (US Gamer / Dynamic)",
        "voice": "en-US-ChristopherNeural",
        "lang": "en",
    },
    "en_guy_authentic": {
        "name": "Guy (US Authentic / Energetic)",
        "voice": "en-US-GuyNeural",
        "lang": "en",
    },
    "en_jenny_female": {
        "name": "Jenny (US Female / Clear)",
        "voice": "en-US-JennyNeural",
        "lang": "en",
    },
    "en_brian_narrator": {
        "name": "Brian (UK Deep / Narrator)",
        "voice": "en-GB-BrianNeural",
        "lang": "en",
    },
    "fr_henri_impact": {
        "name": "Henri (FR Impact / Grave)",
        "voice": "fr-FR-HenriNeural",
        "lang": "fr",
    },
    "fr_vivienne_natural": {
        "name": "Vivienne (FR Naturelle / Moderne)",
        "voice": "fr-FR-VivienneMultilingualNeural",
        "lang": "fr",
    },
    "fr_denise_female": {
        "name": "Denise (FR Studio / Énergique)",
        "voice": "fr-FR-DeniseNeural",
        "lang": "fr",
    },
}


async def generate_voiceover(
    text: str,
    output_audio_path: str,
    voice_key: str = "en_gamer_christopher",
    rate: str = "+10%",
    pitch: str = "+0Hz",
) -> tuple[bool, list[dict[str, Any]]]:
    """
    Generates high-fidelity Neural AI voiceover using Edge-TTS.
    Returns: (success, list_of_word_boundaries_for_subtitles)
    """
    voice_id = VOICES.get(voice_key, {}).get("voice", "en-US-ChristopherNeural")
    communicate = edge_tts.Communicate(text, voice=voice_id, rate=rate, pitch=pitch)

    word_boundaries: list[dict[str, Any]] = []

    try:
        with open(output_audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    word_boundaries.append({
                        "offset": chunk["offset"] / 10_000_000,  # convert 100ns units to seconds
                        "duration": chunk["duration"] / 10_000_000,
                        "text": chunk["text"],
                    })

        return True, word_boundaries
    except Exception as e:
        log.error("Error generating voiceover: %s", e)
        return False, []
