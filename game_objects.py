from numbers import Number
from pathlib import Path
from re import fullmatch
from time import time
from typing import Any

from cliengine import CLIEngine
from datatype import DataType, Variable
from myjson import load
from profile_manage import *
from str_convert import to_snake_case
from utils import catch_interrupt, catch_interrupt_with_api, match_input


__all__ = [
    "Item",
    "Location",
    "NPC",
    "Achievement",
    "Event",
    "Quest",
    "SkillType",
    "PlayerProfile",
    "GameContext",
    "GameLauncher",
]


class Item(DataType):
    variables = [
        Variable("id", str),
        Variable("name", str),
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
        Variable("rewards", list[list[str | Any]]),  # list of type and content
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
        Variable("gamerules", dict[str, any], default_factory=lambda: {}),

        Variable("character_xp", Number, default=0),
        Variable("skill_xp", dict[str, Number], default_factory=lambda: {}),
        Variable("quest_stages", dict[str, int], default_factory=lambda: {}),
        Variable("achievements", dict[str: bool], default_factory=lambda: {}),

        Variable("inventory", list[Item], default_factory=lambda: []),

        Variable("total_playtime", Number, default=0),
        Variable("last_updated", Number, default=-1),
    ]

    def save(self, working_directory: str | Path):
        with open(working_directory / "saves" / f"{self.id}.json", "w") as file:
            self.dump(file)


class GameContext:
    profile: PlayerProfile
    engine: CLIEngine = CLIEngine()
    engine.commands["exit"].__doc__ = "Exit and save game."
    working_directory: str | Path

    def __init__(self, profile: PlayerProfile, working_directory: str | Path, /):
        self.profile = profile
        self.settings = None
        self.session_start_time = None
        self.working_directory = Path(working_directory)
        # self.session_duration = None

    def launch_message(self):
        print(f"Running game profile: {self.profile.id}")

    def trigger_event(self, event: Event, /):
        pass

    def update_time(self, /):
        current_time = time()
        if self.profile.last_updated == -1:
            dt = 0
        else:
            dt = current_time - self.profile.last_updated
        self.profile.last_updated = current_time
        self.profile.total_playtime += dt

    def add_command(self, name: str, patterns: list[str]):
        return self.engine.add_command(name, patterns)

    @catch_interrupt
    def run(self):
        self.launch_message()

        self.session_start_time = time()

        while True:
            command = input(">> ").strip()
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


class GameLauncher:
    engine: CLIEngine = CLIEngine()
    engine.commands["exit"].__doc__ = "Exit game launcher."
    working_directory: str | Path

    def __init__(self, working_directory: str | Path, /):
        self.settings = None
        self.working_directory = Path(working_directory)

    def launch_message(self):
        print("Game Launcher Running.")

    @engine.add_command("list", ["list", "ls"])
    def list_profiles(self):
        """
        List the available profiles.
        """
        seen_profile = False
        for profile_name, profile_id in get_profiles(self.working_directory, PlayerProfile):
            if not seen_profile:
                print("Available profiles:")
                seen_profile = True
            print(f" - {profile_name} ({profile_id})")
        if not seen_profile:
            print("No profile available.")
        return {"type": "success"}

    @engine.add_command("new", ["new", "init"])
    @catch_interrupt_with_api
    def init_profile(self):
        """
        Create a new profile.
        """
        print("Please enter the name of the profile.")
        profile_name = match_input(r".*[^\s]+.*")
        if profile_name is None:
            return {"type": "interrupted"}
        profile_name = profile_name.strip()

        default_id = to_snake_case(profile_name)
        if (self.working_directory / "saves" / f"{default_id}.json").exists():
            if (segments := fullmatch(r"(.+)_(\d+)$", default_id)):
                base_id = segments.group(1)
                i = int(segments.group(2)) + 1
            else:
                base_id = default_id
                i = 1
            unique_id = f"{base_id}_{i}"
            while (self.working_directory / "saves" / f"{unique_id}.json").exists():
                i += 1
                unique_id = f"{base_id}_{i}"
        else:
            unique_id = default_id

        print("Please enter the ID of the profile.")
        print(f"Leave empty for auto-generated one: {unique_id!r}")
        while True:
            profile_id = match_input(r".*")
            if profile_id is None:
                return {"type": "interrupted"}
            elif profile_id == '':
                profile_id = unique_id
            else:
                profile_id = profile_id.strip()
            if (self.working_directory / "saves" / f"{profile_id}.json").exists():
                print("Profile ID taken, please choose another one.")
            else:
                break

        PlayerProfile(profile_id, profile_name).save(self.working_directory)

        print(f"Successfully created")
        return {"type": "success"}

    @engine.add_command("run", ["run <profile_id:str>", "play <profile_id:str>"])
    def run_profile(self, profile_id: str):
        """
        Play the selected profile by ID.
        """
        filepath = (self.working_directory / "saves" /
                    f"{profile_id.removesuffix('.json')}.json")
        if not filepath.is_file():
            print(f"Failed to load: Profile not found: {profile_id}.")
            return {"type": "failed"}

        try:
            with open(filepath) as file:
                obj = load(file)
        except:
            print("Failed to load: Profile has invalid JSON structure.")
            print(f"Profile not found: {profile_id}.")
            return {"type": "failed"}
        try:
            profile = PlayerProfile.loads(obj)
        except:
            print("Failed to load: Profile has invalid data.")
            return {"type": "failed"}

        GameContext(profile, self.working_directory).run()
        return {"type": "success"}

    @engine.add_command("rm", ["rm <profile_id:str>", "del <profile_id:str>"])
    def remove_profile(self, profile_id: str):
        """
        Delete the selected profile by ID.
        """
        filepath = (self.working_directory / "saves" /
                    f"{profile_id.removesuffix('.json')}.json")
        if not filepath.is_file():
            print(f"Failed to remove: Profile not found: {profile_id}.")
            return {"type": "failed"}
        print(f"Are you sure you want to delete profile {profile_id!r}?")
        print("This profile will be deleted immediately. You can't undo this action. (y/N)")
        confirmation = match_input(r"^[ynYN]?$", strip=True).lower()
        if confirmation == 'y':
            filepath.unlink(missing_ok=True)
            print(f"Deleted profile {profile_id!r}!")
            return {"type": "success"}
        else:
            print("Canceled.")
            return {"type": "failed"}

    @engine.add_command("mv", ["mv <old_profile_id:str>",
                               "rename <old_profile_id:str>"])
    def rename_profile(self, old_profile_id: str):
        """
        Rename the selected profile by ID.
        New name and ID will be prompted for.
        """
        filepath = (self.working_directory / "saves" /
                    f"{old_profile_id.removesuffix('.json')}.json")
        if not filepath.is_file():
            print(f"Failed to rename: Profile not found: {old_profile_id}.")
            return {"type": "failed"}

        try:
            with open(filepath) as file:
                obj = load(file)
        except:
            print("Failed to rename: Profile has invalid JSON structure.")
            print(f"Profile not found: {old_profile_id}.")
            return {"type": "failed"}
        try:
            profile = PlayerProfile.loads(obj)
        except:
            print("Failed to rename: Profile has invalid data.")
            return {"type": "failed"}

        old_profile_name = profile.name
        print(f"Original profile name: {old_profile_name!r}")
        print(f"Original profile ID: {profile.id!r}")

        print("Please enter the new name for this profile.")
        new_profile_name = match_input(r".*[^\s]+.*")
        if new_profile_name is None:
            return {"type": "interrupted"}
        new_profile_name = new_profile_name.strip()

        default_id = to_snake_case(new_profile_name)
        if (self.working_directory / "saves" / f"{default_id}.json").exists():
            if (segments := fullmatch(r"(.+)_(\d+)$", default_id)):
                base_id = segments.group(1)
                i = int(segments.group(2)) + 1
            else:
                base_id = default_id
                i = 1
            unique_id = f"{base_id}_{i}"
            while (self.working_directory / "saves" / f"{unique_id}.json").exists():
                i += 1
                unique_id = f"{base_id}_{i}"
        else:
            unique_id = default_id

        print("Please enter the ID of the profile.")
        print(f"Leave empty for auto-generated one: {unique_id!r}")
        while True:
            new_profile_id = match_input(r".*")
            if new_profile_id is None:
                return {"type": "interrupted"}
            elif new_profile_id == '':
                new_profile_id = unique_id
            else:
                new_profile_id = new_profile_id.strip()
            if (self.working_directory / "saves" / f"{new_profile_id}.json").exists():
                print("Profile ID taken, please choose another one.")
            else:
                break

        profile.name = new_profile_name
        profile.id = new_profile_id
        profile.save(self.working_directory)
        filepath.unlink()
        print(f"Successfully renamed profile name from"
              f" {old_profile_name} to {new_profile_name},")
        print(f"And profile ID from {old_profile_id} to {new_profile_id}!")
        return {"type": "success"}

    @catch_interrupt
    def run(self):
        self.launch_message()

        init_working_folder(self.working_directory)
        self.settings = load_settings(self.working_directory)

        if self.settings is None:
            print("Warning: settings.json not found or corrupt. Overriding.")
            init_settings(self.working_directory, override=True)

        while True:
            command = input("> ").strip()
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
                case "failed":
                    continue
                case "interrupted":
                    continue
                case "unknown_command":
                    print(f"Unknown command: {api['command']!r}.")
                    print(f"Use 'help' for a list of commands available.")
                case other:
                    print(f"Unknown API response type: {other}")


def main():
    launcher = GameLauncher(Path.home() / "cliengine")
    launcher.run()


if __name__ == "__main__":
    main()
