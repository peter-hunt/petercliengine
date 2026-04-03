from pathlib import Path
from time import time

from cliengine import CLIEngine
from utils import catch_interrupt

from .data import Event
from .profile import PlayerProfile


__all__ = [
    "GameContext",
]


class GameContext:
    profile: PlayerProfile
    engine: CLIEngine = CLIEngine()
    engine.commands["exit"].__doc__ = "Exit and save game."
    working_directory: str | Path

    def __init__(self, profile: PlayerProfile, working_directory: str | Path):
        self.profile = profile
        self.settings = None
        self.session_start_time = None
        self.working_directory = Path(working_directory)

    def launch_message(self):
        print(f"Running game profile: {self.profile.id}")

    def is_triggerable(self, event: Event, /):
        return False

    def trigger_event(self, event: Event, /):
        pass

    def update_time(self):
        current_time = time()
        if self.profile.last_updated == -1:
            dt = 0
        else:
            dt = current_time - self.profile.last_updated
        self.profile.last_updated = current_time
        self.profile.total_playtime += dt

    def update(self):
        self.update_time()

    def add_command(self, name: str, patterns: list[str]):
        return self.engine.add_command(name, patterns)

    @catch_interrupt
    def run(self):
        self.launch_message()

        self.session_start_time = time()

        while True:
            command = self.engine.read_command(">> ")
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
                    print(f"Unknown command: {api['command']!r}.")
                    print(f"Use 'help' for a list of commands available.")
                case other:
                    print(f"Unknown API response: {other}")

    @engine.add_command("save", ["save"])
    def save(self):
        """
        Save profile data.
        """
        self.profile.save(self.working_directory)
        print("Saved!")
