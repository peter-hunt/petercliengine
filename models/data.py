if __name__ == "__main__":
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).parent.parent))

import random
from typing import Any

from datatype import DataType, Variable


__all__ = [
    "ItemType",
    "Item",
    "Location",
    "NPC",
    "Achievement",
    "Event",
    "Quest",
    "SkillType",
]


class ItemType(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
        Variable("stackable", bool, default=False),
        Variable("max_stack", int, default=1),
    ]
    id: str
    name: str
    stackable: bool
    max_stack: int

    def can_stack_with(self, item: "Item") -> bool:
        """Return True if ``item`` shares this item type and stacking is allowed."""
        return self.stackable and item.id == self.id

    def available_stack_space(self, existing: "Item") -> int:
        """Return how many more units can be added to an existing stack.

        Args:
            existing: An ``Item`` instance already in the inventory with this type.

        Returns:
            Remaining stack capacity (0 if the stack is full or not stackable).
        """
        if not self.stackable or existing.id != self.id:
            return 0
        return max(0, self.max_stack - existing.quantity)


class Item(DataType):
    variables = [
        Variable("id", str),
        Variable("quantity", int, default=1),
    ]
    id: str
    quantity: int

    def use(self) -> str:
        """Return a generic use-action description for this item.

        Override in subclasses or supply custom logic in ``GameContext``.

        Returns:
            A plain-text description of the action.
        """
        return f"You use {self.id}."

    def drop(self) -> str:
        """Return a generic drop-action description for this item.

        Returns:
            A plain-text description of the action.
        """
        return f"You drop {self.id} (x{self.quantity})."


class Location(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
        Variable("connections", list[str], default_factory=list),
    ]
    id: str
    name: str
    connections: list[str]

    def can_travel_to(self, location_id: str) -> bool:
        """Return True if ``location_id`` is reachable from this location.

        Args:
            location_id: The ID of the destination location.
        """
        return location_id in self.connections

    def travel_to(self, location_id: str) -> str:
        """Return a travel description if the destination is connected, or an
        error message if it is not.

        Args:
            location_id: The ID of the destination location.

        Returns:
            A plain-text description of the outcome.
        """
        if self.can_travel_to(location_id):
            return f"You travel from {self.name} to {location_id}."
        return f"You cannot reach {location_id!r} from {self.name}."


class NPC(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
        Variable("location", str),  # id
        Variable("greetings", list[str]),
        Variable("dialogs", list[str]),
    ]
    id: str
    name: str
    location: str
    greetings: list[str]
    dialogs: list[str]

    def greet(self) -> str:
        """Return a random greeting line from this NPC.

        Returns:
            A randomly selected greeting string, or an empty string if none
            are defined.
        """
        if not self.greetings:
            return ""
        return random.choice(self.greetings)

    def dialog(self) -> str:
        """Return a random dialogue line from this NPC.

        Returns:
            A randomly selected dialogue string, or an empty string if none
            are defined.
        """
        if not self.dialogs:
            return ""
        return random.choice(self.dialogs)


class Achievement(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
    ]
    id: str
    name: str

    def unlock_message(self) -> str:
        """Return the text shown when this achievement is first unlocked."""
        return f"Achievement unlocked: {self.name}!"


# a moment
# example usages:
# narration, tutorial, unlocking content, world-shift moments
class Event(DataType):
    # trigger condition/requirement
    # - always/never
    # - quest stage/failed, story branch
    # - skill level, skill branch, power estimation, item/resource
    # - location, area/world state, time, other events
    # randomness/rarity
    # presentation: text, choices, flavor text not logic
    # rewards (consequences): should change what the player can do
    # - unlocking skill, mechanics, interfaces, quests
    # - rule changes, enable shortcuts, allowing actions
    # - area open/close, NPC action/change
    # - lore, hints, narration, modifiers
    # life cycle: one time, cycle
    variables = [
        Variable("id", str),
        Variable("trigger", list[list[str | Any]]),  # list of type and content
        Variable("narration", list[str]),
        Variable("rewards", list[list[str | Any]]),  # list of type and content
        Variable("max_occurances", int),
    ]
    id: str
    trigger: list[list[str | Any]]
    narration: list[str]
    rewards: list[list[str | Any]]
    max_occurances: int

    def narrate(self) -> str:
        """Return all narration lines joined by newlines."""
        return "\n".join(self.narration)


# a commitment
# what quests are, how they advanced, what they unlock
# rewards
class Quest(DataType):
    # a sequence of pairs of reward type and content
    variables = [
        Variable("id", str),
        Variable("name", str),
        Variable("stages", int),
        Variable("rewards", list[list[str | Any]]),  # list of type and content
    ]
    id: str
    name: str
    stages: int
    rewards: list[list[str | Any]]

    def is_complete(self, current_stage: int) -> bool:
        """Return True when ``current_stage`` equals or exceeds the total stages.

        Args:
            current_stage: The player's current stage index for this quest.
        """
        return current_stage >= self.stages

    def advance_stage(self, current_stage: int) -> int:
        """Return the next stage index, clamped to the total stage count.

        Args:
            current_stage: The player's current stage index.

        Returns:
            ``current_stage + 1`` capped at ``self.stages``.
        """
        return min(current_stage + 1, self.stages)

    def stage_description(self, current_stage: int) -> str:
        """Return a human-readable progress description for the given stage.

        Args:
            current_stage: The player's current stage index.

        Returns:
            A progress string, e.g. ``"Quest 'Hunt' — stage 2/3 (in progress)"``.
        """
        status = "complete" if self.is_complete(
            current_stage) else "in progress"
        return f"Quest {self.name!r} \u2014 stage {current_stage}/{self.stages} ({status})"


# prerequisites, caps, scaling curves
# how skills level up, xp costs
# modifiers and stacking
# unlocking, availability, bonuses
class SkillType(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
        Variable("levels", list[int]),
    ]
    id: str
    name: str
    levels: list[int]

    def level_for_xp(self, xp: int | float) -> int:
        """Return the level (0-indexed) a player has reached for the given XP.

        ``levels`` is a list of XP thresholds where ``levels[i]`` is the
        total XP required to *enter* level ``i + 1``.  Level 0 requires no
        XP.

        Args:
            xp: The player's current total XP for this skill.

        Returns:
            The highest level whose threshold the player has met.
        """
        level = 0
        for threshold in self.levels:
            if xp >= threshold:
                level += 1
            else:
                break
        return level

    def xp_to_next_level(self, xp: int | float) -> int | float | None:
        """Return the XP still needed to reach the next level, or ``None``
        if the player is already at the maximum level.

        Args:
            xp: The player's current total XP.

        Returns:
            XP remaining to the next threshold, or ``None`` at max level.
        """
        current = self.level_for_xp(xp)
        if current >= len(self.levels):
            return None
        return self.levels[current] - xp


def main() -> None:
    import io

    sword_type = ItemType(id="sword", name="Iron Sword", stackable=False)
    print("ItemType:", sword_type)

    item = Item(id="sword", quantity=2)
    print("Item:", item)

    loc = Location(id="town", name="Starter Town")
    print("Location:", loc)

    npc = NPC(
        id="blacksmith",
        name="Old Blacksmith",
        location="town",
        greetings=["Need something forged?", "Got any iron to spare?"],
        dialogs=["I've been smithing since I was twelve."],
    )
    print("NPC:", npc)

    # JSON round-trip
    buf = io.StringIO()
    npc.dump(buf)  # type: ignore[arg-type]
    buf.seek(0)
    print("NPC JSON:", buf.read())
    buf.seek(0)
    npc2 = NPC.load(buf)  # type: ignore[arg-type]
    print("Reloaded NPC:", npc2)


if __name__ == "__main__":
    main()
