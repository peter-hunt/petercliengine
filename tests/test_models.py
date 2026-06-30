"""Tests for models package — data, profile, and context."""
import pytest
from models.data import (
    ItemType, Item, Location, NPC, Achievement, Event, Quest, SkillType,
)
from models.profile import PlayerProfile
from models.context import GameContext


# ---------------------------------------------------------------------------
# data.py — entity models
# ---------------------------------------------------------------------------

class TestItemType:
    def setup_method(self):
        self.st = ItemType(id="potion", name="Potion",
                           stackable=True, max_stack=10)
        self.item = Item(id="potion", quantity=4)

    def test_can_stack_with_matching(self):
        assert self.st.can_stack_with(self.item)

    def test_cannot_stack_with_different_id(self):
        other = Item(id="arrow", quantity=3)
        assert not self.st.can_stack_with(other)

    def test_not_stackable(self):
        sword = ItemType(id="sword", name="Sword", stackable=False)
        assert not sword.can_stack_with(self.item)

    def test_available_stack_space(self):
        assert self.st.available_stack_space(self.item) == 6

    def test_available_stack_space_full(self):
        full = Item(id="potion", quantity=10)
        assert self.st.available_stack_space(full) == 0


class TestItem:
    def test_use(self):
        i = Item(id="sword", quantity=1)
        assert "sword" in i.use()

    def test_drop(self):
        i = Item(id="potion", quantity=3)
        text = i.drop()
        assert "potion" in text
        assert "3" in text


class TestLocation:
    def setup_method(self):
        self.loc = Location(id="town", name="Town",
                            connections=["forest", "cave"])

    def test_can_travel_to_connected(self):
        assert self.loc.can_travel_to("forest")

    def test_cannot_travel_to_disconnected(self):
        assert not self.loc.can_travel_to("castle")

    def test_travel_to_valid(self):
        result = self.loc.travel_to("forest")
        assert "forest" in result

    def test_travel_to_invalid(self):
        result = self.loc.travel_to("mars")
        assert "cannot" in result.lower() or "reach" in result.lower()


class TestNPC:
    def test_greet_returns_one_of_greetings(self):
        npc = NPC(id="smith", name="Smith", location="town",
                  greetings=["Hello!"], dialogs=["Need something?"])
        assert npc.greet() == "Hello!"

    def test_greet_empty(self):
        npc = NPC(id="ghost", name="Ghost", location="cave",
                  greetings=[], dialogs=[])
        assert npc.greet() == ""

    def test_dialog(self):
        npc = NPC(id="smith", name="Smith", location="town",
                  greetings=[], dialogs=["Need a blade?"])
        assert npc.dialog() == "Need a blade?"


class TestAchievement:
    def test_unlock_message(self):
        a = Achievement(id="first_kill", name="First Blood")
        assert "First Blood" in a.unlock_message()


class TestEvent:
    def test_narrate_joins_lines(self):
        e = Event(id="ev", trigger=[["always"]], narration=["Line 1.", "Line 2."],
                  rewards=[], max_occurances=1)
        text = e.narrate()
        assert "Line 1." in text
        assert "Line 2." in text


class TestQuest:
    def setup_method(self):
        self.q = Quest(id="hunt", name="Hunt", stages=3, rewards=[])

    def test_is_complete_false_mid(self):
        assert not self.q.is_complete(1)

    def test_is_complete_true_at_max(self):
        assert self.q.is_complete(3)

    def test_advance_stage(self):
        assert self.q.advance_stage(1) == 2

    def test_advance_stage_clamped(self):
        assert self.q.advance_stage(3) == 3

    def test_stage_description_in_progress(self):
        assert "in progress" in self.q.stage_description(1)

    def test_stage_description_complete(self):
        assert "complete" in self.q.stage_description(3)


class TestSkillType:
    def setup_method(self):
        # levels[i] = XP threshold to reach level (i+1)
        self.skill = SkillType(
            id="sword", name="Swordsmanship", levels=[100, 300, 600])

    def test_level_for_xp_zero(self):
        assert self.skill.level_for_xp(0) == 0

    def test_level_for_xp_at_threshold(self):
        assert self.skill.level_for_xp(100) == 1
        assert self.skill.level_for_xp(300) == 2
        assert self.skill.level_for_xp(600) == 3

    def test_level_for_xp_beyond_max(self):
        assert self.skill.level_for_xp(9999) == 3

    def test_xp_to_next_level(self):
        assert self.skill.xp_to_next_level(0) == 100
        assert self.skill.xp_to_next_level(50) == 50

    def test_xp_to_next_level_at_max(self):
        assert self.skill.xp_to_next_level(600) is None


# ---------------------------------------------------------------------------
# profile.py — PlayerProfile inventory and skill helpers
# ---------------------------------------------------------------------------

class TestInventoryHelpers:
    def setup_method(self):
        self.profile = PlayerProfile(id="p", name="P")
        self.arrow_type = ItemType(
            id="arrow", name="Arrow", stackable=True, max_stack=10)

    def test_add_item_no_type(self):
        self.profile.add_item("sword", 1)
        assert len(self.profile.inventory) == 1

    def test_add_item_stacks(self):
        self.profile.add_item("arrow", 7, self.arrow_type)
        # fills stack (7+3=10) + new(1)
        self.profile.add_item("arrow", 4, self.arrow_type)
        total = sum(i.quantity for i in self.profile.find_items("arrow"))
        assert total == 11

    def test_find_items(self):
        self.profile.add_item("arrow", 5, self.arrow_type)
        assert len(self.profile.find_items("arrow")) == 1
        assert self.profile.find_items("potion") == []

    def test_remove_item(self):
        self.profile.add_item("arrow", 10, self.arrow_type)
        shortfall = self.profile.remove_item("arrow", 6)
        assert shortfall == 0
        total = sum(i.quantity for i in self.profile.find_items("arrow"))
        assert total == 4

    def test_remove_item_shortfall(self):
        self.profile.add_item("arrow", 3, self.arrow_type)
        shortfall = self.profile.remove_item("arrow", 10)
        assert shortfall == 7

    def test_remove_clears_empty_stacks(self):
        self.profile.add_item("arrow", 3, self.arrow_type)
        self.profile.remove_item("arrow", 3)
        assert self.profile.find_items("arrow") == []


class TestSkillHelpers:
    def setup_method(self):
        self.profile = PlayerProfile(id="p", name="P")
        self.combat = SkillType(id="combat", name="Combat", levels=[100, 300])
        self.registry = {"combat": self.combat}

    def test_add_skill_xp_no_levelup(self):
        leveled = self.profile.add_skill_xp("combat", 50, self.registry)
        assert leveled == []

    def test_add_skill_xp_levelup(self):
        leveled = self.profile.add_skill_xp("combat", 100, self.registry)
        assert 1 in leveled

    def test_add_skill_xp_unknown_skill(self):
        leveled = self.profile.add_skill_xp("archery", 999, self.registry)
        assert leveled == []
        assert self.profile.skill_xp["archery"] == 999


# ---------------------------------------------------------------------------
# context.py — trigger / event queue
# ---------------------------------------------------------------------------

class TestGameContextTrigger:
    def setup_method(self):
        self.profile = PlayerProfile(id="p", name="P")
        self.ctx = GameContext(self.profile, "/tmp")

    def _ev(self, ev_id, trigger, rewards=None, max_occ=1):
        return Event(id=ev_id, trigger=trigger,
                     narration=[], rewards=rewards or [],
                     max_occurances=max_occ)

    def test_always_triggers(self):
        ev = self._ev("ev", [["always"]])
        assert self.ctx.is_triggerable(ev)

    def test_never_blocked(self):
        ev = self._ev("ev", [["never"]])
        assert not self.ctx.is_triggerable(ev)

    def test_max_occurances_blocks(self):
        ev = self._ev("ev", [["always"]], max_occ=1)
        self.ctx.trigger_event(ev)
        assert not self.ctx.is_triggerable(ev)

    def test_trigger_applies_rewards(self):
        ev = self._ev("ev", [["always"]],
                      rewards=[["achievement", "brave"]], max_occ=5)
        self.ctx.trigger_event(ev)
        assert self.profile.achievements.get("brave") is True


class TestEventQueue:
    def setup_method(self):
        self.profile = PlayerProfile(id="p", name="P")
        self.ctx = GameContext(self.profile, "/tmp")

    def test_schedule_and_flush(self):
        fired = []
        ev = Event(id="ev1", trigger=[["always"]], narration=[], rewards=[],
                   max_occurances=1)
        orig = self.ctx.trigger_event
        self.ctx.trigger_event = lambda e: (fired.append(e.id), orig(e))

        self.ctx.schedule_event(ev)
        assert len(self.ctx._event_queue) == 1
        self.ctx.flush_event_queue()
        assert "ev1" in fired
        assert len(self.ctx._event_queue) == 0

    def test_update_flushes_queue(self):
        fired = []
        ev = Event(id="ev2", trigger=[["always"]], narration=[], rewards=[],
                   max_occurances=1)
        orig = self.ctx.trigger_event
        self.ctx.trigger_event = lambda e: (fired.append(e.id), orig(e))

        self.ctx.schedule_event(ev)
        self.ctx.update()
        assert "ev2" in fired
