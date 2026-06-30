from pathlib import Path
from threading import Event as ThreadEvent, Thread
from time import time
from typing import Any, Callable

from cliengine import CLIEngine
from color import ColorTheme, DEFAULT_THEME
from utils import catch_interrupt

from .data import Event, Item
from .profile import PlayerProfile


__all__ = [
    "GameContext",
]


class GameContext:
    profile: PlayerProfile
    engine: CLIEngine = CLIEngine()
    engine.commands["exit"].__doc__ = "Exit and save game."
    working_directory: Path
    settings: dict[str, Any] | None
    session_start_time: float | None

    def __init__(self, profile: PlayerProfile, working_directory: str | Path,
                 theme: ColorTheme = DEFAULT_THEME):
        self.profile = profile
        self.theme = theme
        self.settings = None
        self.session_start_time = None
        self.working_directory = Path(working_directory)
        self._autosave_stop: ThreadEvent | None = None
        self._autosave_thread: Thread | None = None
        self._event_queue: list[Event] = []

    def launch_message(self) -> None:
        print(self.theme.heading(f"Running game profile: {self.profile.id}"))

    def is_triggerable(self, event: Event, /) -> bool:
        """Return ``True`` when all of ``event``'s trigger conditions are satisfied
        and the occurrence limit has not been reached.

        Supported trigger condition types (each entry in ``event.trigger`` is a
        list whose first element is the type string):

        * ``["always"]`` — always satisfied.
        * ``["never"]`` — never satisfied.
        * ``["quest", quest_id, stage]`` — ``profile.quest_stages[quest_id] == stage``.
        * ``["quest_complete", quest_id]`` — ``profile.quest_stages[quest_id]`` is truthy
          (non-zero), indicating the quest has advanced past stage 0.
        * ``["achievement", achievement_id]`` — the achievement is unlocked.
        * ``["skill_xp", skill_id, min_xp]`` — ``profile.skill_xp[skill_id] >= min_xp``.
        * ``["item", item_id]`` — at least one item matching ``item_id`` is in inventory.

        All conditions are evaluated with AND logic; all must pass.
        """
        profile = self.profile
        occurrences = profile.event_occurrences.get(event.id, 0)
        if occurrences >= event.max_occurances:
            return False
        for condition in event.trigger:
            if not condition:
                continue
            ctype = condition[0]
            match ctype:
                case "always":
                    pass
                case "never":
                    return False
                case "quest":
                    if len(condition) < 3:
                        return False
                    if profile.quest_stages.get(condition[1], 0) != condition[2]:
                        return False
                case "quest_complete":
                    if len(condition) < 2:
                        return False
                    if not profile.quest_stages.get(condition[1], 0):
                        return False
                case "achievement":
                    if len(condition) < 2:
                        return False
                    if not profile.achievements.get(condition[1], False):
                        return False
                case "skill_xp":
                    if len(condition) < 3:
                        return False
                    # type: ignore[operator]
                    if profile.skill_xp.get(condition[1], 0) < condition[2]:
                        return False
                case "item":
                    if len(condition) < 2:
                        return False
                    if not any(i.id == condition[1] for i in profile.inventory):
                        return False
                case _:
                    return False
        return True

    def trigger_event(self, event: Event, /) -> None:
        """Narrate ``event``, apply its rewards, and record the occurrence.

        Supported reward types (each entry in ``event.rewards`` is a list whose
        first element is the type string):

        * ``["quest_stage", quest_id, new_stage]`` — set ``profile.quest_stages[quest_id]``.
        * ``["achievement", achievement_id]`` — unlock the achievement.
        * ``["add_skill_xp", skill_id, amount]`` — add XP to ``profile.skill_xp[skill_id]``.
        * ``["add_item", item_id, quantity]`` — append an ``Item`` to ``profile.inventory``.
        """
        profile = self.profile
        for line in event.narration:
            print(self.theme.info(line))
        for reward in event.rewards:
            if not reward:
                continue
            match reward[0]:
                case "quest_stage":
                    if len(reward) >= 3:
                        # type: ignore[assignment]
                        profile.quest_stages[reward[1]] = reward[2]
                case "achievement":
                    if len(reward) >= 2:
                        profile.achievements[reward[1]] = True
                case "add_skill_xp":
                    if len(reward) >= 3:
                        profile.skill_xp[reward[1]] = (
                            # type: ignore[assignment,operator]
                            profile.skill_xp.get(reward[1], 0) + reward[2]
                        )
                case "add_item":
                    if len(reward) >= 3:
                        profile.inventory.append(
                            Item(id=reward[1], quantity=reward[2]))
        profile.event_occurrences[event.id] = (
            profile.event_occurrences.get(event.id, 0) + 1
        )

    # ------------------------------------------------------------------
    # Event queue
    # ------------------------------------------------------------------

    def schedule_event(self, event: Event) -> None:
        """Add *event* to the pending event queue.

        The event will be fired on the next call to :meth:`flush_event_queue`
        (which is called automatically by :meth:`update` after each command).
        """
        self._event_queue.append(event)

    def flush_event_queue(self) -> None:
        """Fire every queued event that is currently triggerable, then clear
        the queue.

        Input is locked while events are being processed so that narration
        cannot be interrupted by buffered player input.  Any buffered commands
        are flushed back to the engine after all events have been triggered.
        """
        if not self._event_queue:
            return
        queue = self._event_queue[:]
        self._event_queue.clear()
        self.engine.lock_input()
        try:
            for event in queue:
                if self.is_triggerable(event):
                    self.trigger_event(event)
        finally:
            self.engine.unlock_input(self)

    def update_time(self) -> None:
        current_time = time()
        if self.profile.last_updated == -1:  # type: ignore[comparison-overlap]
            dt: float = 0.0
        else:
            # type: ignore[operator]
            dt = current_time - self.profile.last_updated
        self.profile.last_updated = current_time  # type: ignore[assignment]
        self.profile.total_playtime = self.profile.total_playtime + \
            dt  # type: ignore[assignment,operator]

    def update(self) -> None:
        self.update_time()
        self.flush_event_queue()

    def add_command(self, name: str, patterns: list[str]) -> Callable[..., Any]:
        return self.engine.add_command(name, patterns)

    # ------------------------------------------------------------------
    # Auto-save
    # ------------------------------------------------------------------

    def start_autosave(self, interval: float) -> None:
        """Start a background daemon thread that saves the profile every *interval* seconds.

        Calling this when an autosave thread is already running is a no-op.

        Args:
            interval: Seconds between automatic saves.  Must be positive.
        """
        if interval <= 0:
            return
        if self._autosave_thread is not None and self._autosave_thread.is_alive():
            return
        self._autosave_stop = ThreadEvent()
        stop_event = self._autosave_stop

        def _autosave_loop() -> None:
            while not stop_event.wait(timeout=interval):
                try:
                    self.profile.save(self.working_directory)
                except Exception:
                    pass

        self._autosave_thread = Thread(target=_autosave_loop, daemon=True,
                                       name="autosave")
        self._autosave_thread.start()

    def stop_autosave(self) -> None:
        """Stop the background autosave thread, if running."""
        if self._autosave_stop is not None:
            self._autosave_stop.set()
        if self._autosave_thread is not None:
            self._autosave_thread.join(timeout=2)
            self._autosave_thread = None
        self._autosave_stop = None

    @catch_interrupt
    def run(self) -> None:
        self.launch_message()

        self.session_start_time = time()

        # Start auto-save if configured
        autosave_interval = 0
        if self.settings and isinstance(self.settings.get("auto_save_interval"), (int, float)):
            autosave_interval = self.settings["auto_save_interval"]
        if autosave_interval > 0:
            self.start_autosave(autosave_interval)

        try:
            while True:
                command = self.engine.read_command(self.theme.prompt(">> "))
                if not command:
                    continue

                api = self.engine.run_command(self, command)
                match api["type"]:
                    case "exit":
                        break
                    case "help":
                        print('\n' + api["content"] + '\n')
                    case "success":
                        continue
                    case "unknown_command":
                        print(self.theme.error(
                            f"Unknown command: {api['command']!r}."))
                        print(self.theme.info(
                            f"Use 'help' for a list of commands available."))
                    case other:
                        print(self.theme.warning(
                            f"Unknown API response: {other}"))
        finally:
            self.stop_autosave()

    @engine.add_command("save", ["save"])
    def save(self) -> dict[str, Any]:
        """
        Save profile data.
        """
        self.profile.save(self.working_directory)
        print(self.theme.success("Saved!"))
        return {"type": "success"}
