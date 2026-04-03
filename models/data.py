if __name__ == "__main__":
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).parent.parent))

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


class Item(DataType):
    variables = [
        Variable("id", str),
        Variable("quantity", int, default=1),
    ]


class Location(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
    ]


class NPC(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
        Variable("location", str),  # id
        Variable("greetings", list[str]),
        Variable("dialogs", list[str]),
    ]


class Achievement(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
    ]


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
        Variable("trigger", list[list[str | Any]]),  # list of type and content
        Variable("narration", list[str]),
        Variable("rewards", list[list[str | Any]]),  # list of type and content
        Variable("max_occurances", int),
    ]


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


def main():
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
    npc.dump(buf)
    buf.seek(0)
    print("NPC JSON:", buf.read())
    buf.seek(0)
    npc2 = NPC.load(buf)
    print("Reloaded NPC:", npc2)


if __name__ == "__main__":
    main()
