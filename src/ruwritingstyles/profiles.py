"""User profile logic for RuWritingStyles (Phase G)."""

from __future__ import annotations
from typing import Any

PROFILES = {
    "researcher": {
        "name": "Исследователь",
        "description": "Полный спектр комментариев и обоснований, возможность оспаривать решения.",
        "prompt_suffix": "Provide exhaustive philological justification for every suggestion. Focus on methodological nuances and school-specific conflicts.",
    },
    "editor": {
        "name": "Редактор",
        "description": "Режим «Быстрая правка» с минимальным количеством предупреждений.",
        "prompt_suffix": "Be concise. Focus only on critical stylistic errors and major register shifts. Minimize meta-commentary.",
    },
    "student": {
        "name": "Студент",
        "description": "Обучающий режим со ссылками на филологические первоисточники.",
        "prompt_suffix": "Act as a mentor. For every finding, explain the underlying linguistic principle and provide a reference to authoritative works (e.g., Zaliznyak, Vinogradov).",
    },
}

def get_profile_suffix(profile_id: str) -> str:
    profile = PROFILES.get(profile_id, PROFILES["researcher"])
    return profile["prompt_suffix"]
