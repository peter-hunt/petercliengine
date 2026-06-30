from numbers import Number
from pathlib import Path
from typing import Any

from datatype import DataType, Variable

from .data import Item, ItemType, SkillType


__all__ = [
    "PlayerProfile",
    "PROFILE_SAVE_VERSION",
]

#: Bump this integer whenever the serialisation schema changes so that
#: migration code can detect and upgrade older saves.
PROFILE_SAVE_VERSION: int = 1


# sample player profile with common basic functionalities
# alternatives can be modified based on this or redesigned
# to replace the data structures
class PlayerProfile(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),

        # Serialisation version — increment PROFILE_SAVE_VERSION on schema changes
        Variable("save_version", int, default=PROFILE_SAVE_VERSION),

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

        Variable("event_occurrences",
                 dict[str, int], default_factory=lambda: {}),

        Variable("total_playtime", Number, default=0),
        Variable("last_updated", Number, default=-1),
    ]
    id: str
    name: str
    save_version: int
    gamemode: str
    difficulty: str
    gamerules: dict[str, Any]
    character_xp: Number
    skill_xp: dict[str, Number]
    quest_stages: dict[str, int]
    achievements: dict[str, bool]
    inventory: list[Item]
    event_occurrences: dict[str, int]
    total_playtime: Number
    last_updated: Number

    def save(self, working_directory: str | Path) -> None:
        path = Path(working_directory)
        from profile_manage import save_profile
        save_profile(path, self)

    # ------------------------------------------------------------------
    # Inventory helpers
    # ------------------------------------------------------------------

    def find_items(self, item_id: str) -> list[Item]:
        """Return all inventory stacks whose ``id`` matches *item_id*."""
        return [i for i in self.inventory if i.id == item_id]

    def add_item(self, item_id: str, quantity: int,
                 item_type: ItemType | None = None) -> None:
        """Add *quantity* units of *item_id* to the inventory.

        If *item_type* is provided and the type is stackable, existing stacks
        are filled first before a new stack is created.  Without *item_type*
        (or for non-stackable types) a new ``Item`` is appended for every unit.

        Args:
            item_id: The item's type identifier.
            quantity: Number of units to add.  Must be positive.
            item_type: Optional ``ItemType`` used to determine stacking rules.
        """
        remaining = quantity
        if item_type is not None and item_type.stackable and item_type.id == item_id:
            for stack in self.find_items(item_id):
                space = item_type.available_stack_space(stack)
                if space <= 0:
                    continue
                fill = min(remaining, space)
                stack.quantity += fill
                remaining -= fill
                if remaining == 0:
                    return
            # Create new full stacks for the remainder
            while remaining > 0:
                take = min(remaining, item_type.max_stack)
                self.inventory.append(Item(id=item_id, quantity=take))
                remaining -= take
        else:
            self.inventory.append(Item(id=item_id, quantity=remaining))

    def remove_item(self, item_id: str, quantity: int) -> int:
        """Remove *quantity* units of *item_id* from the inventory.

        Stacks are consumed from last to first (LIFO).  If there are not
        enough units, all matching stacks are emptied and the shortfall is
        returned.

        Args:
            item_id: The item type to remove.
            quantity: Number of units to remove.

        Returns:
            The number of units that could *not* be removed (0 on success).
        """
        remaining = quantity
        stacks = self.find_items(item_id)
        for stack in reversed(stacks):
            if remaining <= 0:
                break
            take = min(remaining, stack.quantity)
            stack.quantity -= take
            remaining -= take
        # Prune empty stacks
        self.inventory = [i for i in self.inventory if i.quantity > 0]
        return remaining

    # ------------------------------------------------------------------
    # Skill helpers
    # ------------------------------------------------------------------

    def add_skill_xp(self, skill_id: str, amount: int | float,
                     skill_registry: dict[str, SkillType]) -> list[int]:
        """Add *amount* XP to *skill_id* and return a list of new levels reached.

        Args:
            skill_id: The skill's type identifier.
            amount: XP to add.  Must be non-negative.
            skill_registry: Mapping of skill ID → :class:`SkillType`, used to
                look up level thresholds.

        Returns:
            A list of integers representing each level the player has just
            crossed (e.g. ``[2, 3]`` if they levelled up twice in one call).
            Returns an empty list when no level-up occurred or the skill type
            is not found in *skill_registry*.
        """
        skill_type = skill_registry.get(skill_id)
        old_xp: int | float = self.skill_xp.get(
            skill_id, 0)  # type: ignore[assignment]
        old_level = skill_type.level_for_xp(old_xp) if skill_type else 0
        new_xp: int | float = old_xp + amount
        self.skill_xp[skill_id] = new_xp  # type: ignore[assignment]
        if skill_type is None:
            return []
        new_level = skill_type.level_for_xp(
            self.skill_xp[skill_id])  # type: ignore[arg-type]
        return list(range(old_level + 1, new_level + 1))
