from numbers import Number
from pathlib import Path
from typing import Any

from datatype import DataType, Variable

from .data import Item


__all__ = [
    "PlayerProfile",
]


# sample player profile with common basic functionalities
# alternatives can be modified based on this or redesigned
# to replace the data structures
class PlayerProfile(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),

        # a lot of those are interchangable
        # regular, ironman, permadeath, etc.
        Variable("gamemode", str, default="regular"),
        # easy, normal, hard, etc.
        Variable("difficulty", str, default="normal"),
        Variable("gamerules", dict[str, Any], default_factory=lambda: {}),

        Variable("character_xp", Number, default=0),
        Variable("skill_xp", dict[str, Number], default_factory=lambda: {}),
        Variable("quest_stages", dict[str, int], default_factory=lambda: {}),
        Variable("achievements", dict[str, bool], default_factory=lambda: {}),

        Variable("inventory", list[Item], default_factory=lambda: []),

        Variable("total_playtime", Number, default=0),
        Variable("last_updated", Number, default=-1),
    ]

    def save(self, working_directory: str | Path):
        with open(working_directory / "saves" / f"{self.id}.json", "w") as file:
            self.dump(file)
