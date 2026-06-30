from pathlib import Path
from typing import Any

from cliengine import CLIEngine
from color import ColorTheme, DEFAULT_THEME, DARK_THEME, LIGHT_THEME
from myjson import load
from profile_manage import (
    get_profiles, init_working_folder, init_settings,
    load_settings, save_settings, generate_unique_profile_id,
)
from utils import catch_interrupt, catch_interrupt_with_api, match_input

from .context import GameContext
from .profile import PlayerProfile


__all__ = [
    "GameLauncher",
    "DEFAULT_LAUNCHER_SETTINGS",
]

#: Default values written to settings.json on first launch.
DEFAULT_LAUNCHER_SETTINGS: dict[str, Any] = {
    "color_theme": "default",       # "default" | "dark" | "light"
    "auto_enter_last_profile": False,
    "auto_save_interval": 0,        # seconds; 0 = disabled
}

_THEME_MAP = {
    "default": DEFAULT_THEME,
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
}


class GameLauncher:
    engine: CLIEngine = CLIEngine()
    engine.commands["exit"].__doc__ = "Exit game launcher."
    working_directory: Path
    settings: dict[str, Any] | None

    def __init__(self, context_cls: type[Any], profile_cls: type[Any],
                 working_directory: str | Path, /,
                 theme: ColorTheme = DEFAULT_THEME):
        self.settings = None
        self.theme = theme
        self.context_cls = context_cls
        self.profile_cls = profile_cls
        self.working_directory = Path(working_directory)

    def launch_message(self) -> None:
        print(self.theme.heading("Game Launcher Running."))

    @engine.add_command("list", ["list", "ls"])
    def list_profiles(self) -> dict[str, Any]:
        """
        List the available profiles.
        """
        seen_profile = False
        for profile_name, profile_id in get_profiles(self.working_directory, self.profile_cls):
            if not seen_profile:
                print(self.theme.info("Available profiles:"))
                seen_profile = True
            print(f" - {profile_name} ({profile_id})")
        if not seen_profile:
            print(self.theme.info("No profile available."))
        return {"type": "success"}

    @engine.add_command("new", ["new", "init"])
    @catch_interrupt_with_api
    def init_profile(self) -> dict[str, Any]:
        """
        Create a new profile.
        """
        print(self.theme.info("Please enter the name of the profile."))
        profile_name = match_input(r".*[^\s]+.*")
        if profile_name is None:
            return {"type": "interrupted"}
        profile_name = profile_name.strip()

        unique_id = generate_unique_profile_id(
            self.working_directory, profile_name
        )

        print(self.theme.info("Please enter the ID of the profile."))
        print(self.theme.info(
            f"Leave empty for auto-generated one: {unique_id!r}"))
        while True:
            profile_id = match_input(r"^[a-zA-Z0-9_-]*$")
            if profile_id is None:
                return {"type": "interrupted"}
            elif profile_id == '':
                profile_id = unique_id
            else:
                profile_id = profile_id.strip()
            if (self.working_directory / "saves" / f"{profile_id}.json").exists():
                print(self.theme.error(
                    "Profile ID taken, please choose another one."))
            else:
                break

        self.profile_cls(profile_id, profile_name).save(self.working_directory)

        print(self.theme.success(f"Successfully created"))
        return {"type": "success"}

    @engine.add_command("run", ["run <profile_id:str>", "play <profile_id:str>"])
    def run_profile(self, profile_id: str) -> dict[str, Any]:
        """
        Play the selected profile by ID.
        """
        filepath = (self.working_directory / "saves" /
                    f"{profile_id.removesuffix('.json')}.json")
        if not filepath.is_file():
            print(self.theme.error(
                f"Failed to load: Profile not found: {profile_id}."))
            return {"type": "failed"}

        try:
            with open(filepath) as file:
                obj = load(file)
        except Exception:
            print(self.theme.error(
                "Failed to load: Profile has invalid JSON structure."))
            return {"type": "failed"}
        try:
            profile = self.profile_cls.loads(obj)
        except Exception:
            print(self.theme.error("Failed to load: Profile has invalid data."))
            return {"type": "failed"}

        self.context_cls(profile, self.working_directory, self.theme).run()
        # Remember last played profile for auto_enter_last_profile
        if self.settings is not None:
            self.settings["last_profile_id"] = profile_id
            save_settings(self.working_directory, self.settings)
        return {"type": "success"}

    @engine.add_command("rm", ["rm <profile_id:str>", "del <profile_id:str>"])
    def remove_profile(self, profile_id: str) -> dict[str, Any]:
        """
        Delete the selected profile by ID.
        """
        filepath = (self.working_directory / "saves" /
                    f"{profile_id.removesuffix('.json')}.json")
        if not filepath.is_file():
            print(self.theme.error(
                f"Failed to remove: Profile not found: {profile_id}."))
            return {"type": "failed"}
        print(self.theme.warning(
            f"Are you sure you want to delete profile {profile_id!r}?"))
        print(self.theme.warning(
            "This profile will be deleted immediately. You can't undo this action. (y/N)"))
        confirmation = match_input(r"^[ynYN]?$", strip=True)
        if confirmation is not None and confirmation.lower() == 'y':
            filepath.unlink(missing_ok=True)
            print(self.theme.success(f"Deleted profile {profile_id!r}!"))
            return {"type": "success"}
        else:
            print(self.theme.info("Canceled."))
            return {"type": "failed"}

    @engine.add_command("mv", ["mv <old_profile_id:str>",
                               "rename <old_profile_id:str>"])
    def rename_profile(self, old_profile_id: str) -> dict[str, Any]:
        """
        Rename the selected profile by ID.
        New name and ID will be prompted for.
        """
        filepath = (self.working_directory / "saves" /
                    f"{old_profile_id.removesuffix('.json')}.json")
        if not filepath.is_file():
            print(self.theme.error(
                f"Failed to rename: Profile not found: {old_profile_id}."))
            return {"type": "failed"}

        try:
            with open(filepath) as file:
                obj = load(file)
        except Exception:
            print(self.theme.error(
                "Failed to rename: Profile has invalid JSON structure."))
            return {"type": "failed"}
        try:
            profile = self.profile_cls.loads(obj)
        except Exception:
            print(self.theme.error("Failed to rename: Profile has invalid data."))
            return {"type": "failed"}

        old_profile_name = profile.name
        print(self.theme.info(f"Original profile name: {old_profile_name!r}"))
        print(self.theme.info(f"Original profile ID: {profile.id!r}"))

        print(self.theme.info("Please enter the new name for this profile."))
        new_profile_name = match_input(r".*[^\s]+.*")
        if new_profile_name is None:
            return {"type": "interrupted"}
        new_profile_name = new_profile_name.strip()

        unique_id = generate_unique_profile_id(
            self.working_directory, new_profile_name
        )

        print(self.theme.info("Please enter the ID of the profile."))
        print(self.theme.info(
            f"Leave empty for auto-generated one: {unique_id!r}"))
        while True:
            new_profile_id = match_input(r"^[a-zA-Z0-9_-]*$")
            if new_profile_id is None:
                return {"type": "interrupted"}
            elif new_profile_id == '':
                new_profile_id = unique_id
            else:
                new_profile_id = new_profile_id.strip()
            if (self.working_directory / "saves" / f"{new_profile_id}.json").exists():
                print(self.theme.error(
                    "Profile ID taken, please choose another one."))
            else:
                break

        profile.name = new_profile_name
        profile.id = new_profile_id
        profile.save(self.working_directory)
        filepath.unlink()
        print(self.theme.success(
            f"Successfully renamed profile name from"
            f" {old_profile_name} to {new_profile_name},"
        ))
        print(self.theme.success(
            f"And profile ID from {old_profile_id} to {new_profile_id}!"))
        return {"type": "success"}

    @catch_interrupt
    def run(self) -> None:
        self.launch_message()

        init_working_folder(self.working_directory)
        self.settings = load_settings(self.working_directory)

        if self.settings is None:
            print(self.theme.warning(
                "Warning: settings.json not found or corrupt. Overriding."))
            init_settings(self.working_directory, override=True)
            self.settings = {}

        # Merge defaults so new keys are always present
        changed = False
        for key, val in DEFAULT_LAUNCHER_SETTINGS.items():
            if key not in self.settings:
                self.settings[key] = val
                changed = True
        if changed:
            save_settings(self.working_directory, self.settings)

        # Apply color_theme preference
        theme_name = self.settings.get("color_theme", "default")
        if theme_name in _THEME_MAP:
            self.theme = _THEME_MAP[theme_name]

        history_file = str(self.working_directory / ".launcher_history")
        self.engine.setup_readline(history_file=history_file)

        # auto_enter_last_profile: run the most-recently-saved profile
        if self.settings.get("auto_enter_last_profile"):
            last_id = self.settings.get("last_profile_id")
            if last_id:
                self.run_profile(last_id)

        while True:
            command = self.engine.read_command(self.theme.prompt("> "))
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
                    print(self.theme.error(
                        f"Unknown command: {api['command']!r}."))
                    print(self.theme.info(
                        f"Use 'help' for a list of commands available."))
                case other:
                    print(self.theme.warning(
                        f"Unknown API response type: {other}"))


def main() -> None:
    launcher = GameLauncher(GameContext, PlayerProfile,
                            Path.home() / "cliengine")
    launcher.run()


if __name__ == "__main__":
    main()
