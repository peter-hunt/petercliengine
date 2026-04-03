from pathlib import Path

from cliengine import CLIEngine
from myjson import load
from profile_manage import (
    get_profiles, init_working_folder, init_settings,
    load_settings, generate_unique_profile_id,
)
from utils import catch_interrupt, catch_interrupt_with_api, match_input

from .context import GameContext
from .profile import PlayerProfile


__all__ = [
    "GameLauncher",
]


class GameLauncher:
    engine: CLIEngine = CLIEngine()
    engine.commands["exit"].__doc__ = "Exit game launcher."
    working_directory: str | Path

    def __init__(self, context_cls, profile_cls,
                 working_directory: str | Path, /):
        self.settings = None
        self.context_cls = context_cls
        self.profile_cls = profile_cls
        self.working_directory = Path(working_directory)

    def launch_message(self):
        print("Game Launcher Running.")

    @engine.add_command("list", ["list", "ls"])
    def list_profiles(self):
        """
        List the available profiles.
        """
        seen_profile = False
        for profile_name, profile_id in get_profiles(self.working_directory, self.profile_cls):
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

        unique_id = generate_unique_profile_id(
            self.working_directory, profile_name
        )

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

        self.profile_cls(profile_id, profile_name).save(self.working_directory)

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
        except Exception:
            print("Failed to load: Profile has invalid JSON structure.")
            print(f"Profile not found: {profile_id}.")
            return {"type": "failed"}
        try:
            profile = self.profile_cls.loads(obj)
        except Exception:
            print("Failed to load: Profile has invalid data.")
            return {"type": "failed"}

        self.context_cls(profile, self.working_directory).run()
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
        except Exception:
            print("Failed to rename: Profile has invalid JSON structure.")
            print(f"Profile not found: {old_profile_id}.")
            return {"type": "failed"}
        try:
            profile = self.profile_cls.loads(obj)
        except Exception:
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

        unique_id = generate_unique_profile_id(
            self.working_directory, new_profile_name
        )

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
            command = self.engine.read_command("> ")
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
    launcher = GameLauncher(GameContext, PlayerProfile,
                            Path.home() / "cliengine")
    launcher.run()


if __name__ == "__main__":
    main()
