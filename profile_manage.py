from sys import version_info
from pathlib import Path
from re import fullmatch

from datatype import DataType
from myjson import load, dump
from str_convert import to_snake_case


__all__ = [
    "init_working_folder", "init_settings",
    "load_settings", "save_settings", "get_profiles",
    "load_profile", "save_profile", "delete_profile", "profile_exists",
    "generate_unique_profile_id",
]


def init_working_folder(path: Path, /):
    """Create the working folder structure, including the saves directory and a default settings file."""
    if version_info < (3, 14, 2):
        raise RuntimeError(
            "Python version of at least 3.14.2 is required for PeterCLIEngine."
        )
    path.mkdir(parents=True, exist_ok=True)
    (path / "saves").mkdir(parents=True, exist_ok=True)
    init_settings(path)


def init_settings(path: Path, /, override: bool = False):
    """Create a default settings.json in the working folder if it does not exist.

    If ``override`` is True and the existing file is corrupt or unreadable,
    it will be reset to an empty object.
    """
    filepath = path / "settings.json"
    if filepath.is_file():
        if override:
            try:
                with open(filepath) as file:
                    load(file)
            except:
                with open(filepath, "w") as file:
                    dump({}, file)
    else:
        with open(filepath, "w") as file:
            dump({}, file)


def safe_load_json(path: Path, /):
    """Attempt to load and return parsed JSON from a file, returning None on any error."""
    try:
        with open(path) as file:
            return load(file)
    except:
        pass


def load_settings(path: Path, /) -> dict[str, object] | None:
    """Load and return the settings dict from settings.json in the working folder.

    Returns None if the file does not exist or cannot be parsed.
    """
    filepath = (path / "settings.json")
    if filepath.is_file():
        return safe_load_json(filepath)


def save_settings(path: Path, settings: dict, /):
    """Write a settings dict to settings.json in the working folder, overwriting existing content."""
    filepath = (path / "settings.json")
    with open(filepath, "w") as file:
        dump(settings, file)


def get_profiles(path: Path, profile_cls: DataType, *, validate: bool = False):
    """Yield basic info for every profile found in the saves directory.

    Each entry is a ``(name, id)`` tuple by default.  When ``validate`` is
    True each entry is a ``(name, id, is_valid)`` tuple — valid profiles
    carry the parsed name and id, while unreadable files yield their
    filename stem, ``None``, and ``False``.
    """
    for filepath in (path / "saves").glob("*.json"):
        if not filepath.is_file():
            continue
        try:
            with open(filepath) as file:
                profile = profile_cls.load(file)
            if validate:
                yield (profile.name, profile.id, True)
            else:
                yield (profile.name, profile.id)
        except:
            if validate:
                yield (filepath.stem, None, False)


def load_profile(path: Path, profile_cls: DataType, profile_id: str, /):
    """Load and return a single profile by its ID from the saves directory.

    Returns None if no matching profile file is found or the file cannot be parsed.
    """
    filepath = path / "saves" / f"{profile_id}.json"
    if filepath.is_file():
        return safe_load_json(filepath)


def save_profile(path: Path, profile: DataType, /):
    """Serialize and write a profile to its corresponding file in the saves directory.

    The filename is derived from the profile's ID.  Creates the file if it
    does not yet exist, and overwrites it if it does.
    """
    filepath = path / "saves" / f"{profile.id}.json"
    with open(filepath, "w") as file:
        profile.dump(file)


def delete_profile(path: Path, profile_id: str, /):
    """Delete the save file for the profile with the given ID.

    Does nothing if no matching file exists.
    """
    filepath = path / "saves" / f"{profile_id}.json"
    filepath.unlink(missing_ok=True)


def profile_exists(path: Path, profile_id: str, /) -> bool:
    """Return True if a save file for the given profile ID exists in the saves directory."""
    return (path / "saves" / f"{profile_id}.json").is_file()


def generate_unique_profile_id(path: Path, name: str, /) -> str:
    """Derive a unique profile ID from a display name.

    Converts ``name`` to snake_case as the base ID.  If a save file with that
    ID already exists, appends an incrementing numeric suffix (``_1``, ``_2``,
    …) until a free slot is found.  Existing ``_N`` suffixes in the base ID
    are respected: ``a_1`` will start at ``a_1_2`` rather than ``a_1_1``.

    Args:
        path: The working directory that contains the ``saves/`` folder.
        name: The human-readable profile name to derive the ID from.

    Returns:
        A profile ID string guaranteed not to collide with existing saves.
    """
    base_id = to_snake_case(name)
    saves = path / "saves"
    if not (saves / f"{base_id}.json").exists():
        return base_id
    if (segments := fullmatch(r"(.+)_(\d+)$", base_id)):
        root_id = segments.group(1)
        i = int(segments.group(2)) + 1
    else:
        root_id = base_id
        i = 1
    candidate = f"{root_id}_{i}"
    while (saves / f"{candidate}.json").exists():
        i += 1
        candidate = f"{root_id}_{i}"
    return candidate


def main():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)
        init_working_folder(path)

        id1 = generate_unique_profile_id(path, "Alice")
        print(id1)  # alice

        (path / "saves" / f"{id1}.json").write_text("{}")
        id2 = generate_unique_profile_id(path, "Alice")
        print(id2)  # alice_1

        (path / "saves" / f"{id2}.json").write_text("{}")
        id3 = generate_unique_profile_id(path, "Alice")
        print(id3)  # alice_2

        print(generate_unique_profile_id(path, "My Hero Name"))  # my_hero_name
        print(generate_unique_profile_id(
            path, "HTTPRequest"))   # h_t_t_p_request


if __name__ == "__main__":
    main()
