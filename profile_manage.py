from sys import version_info
from pathlib import Path
from re import fullmatch
from typing import Any, Generator
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime, timezone

from datatype import DataType
from myjson import load, dump
from str_convert import to_snake_case


__all__ = [
    "init_working_folder", "init_settings",
    "load_settings", "save_settings", "get_profiles",
    "load_profile", "save_profile", "delete_profile", "profile_exists",
    "generate_unique_profile_id",
    "migrate_save", "migrate_saves_in_folder",
    "export_profile", "import_profile",
]


def _validate_profile_id(profile_id: str, /) -> None:
    """Validate that the profile ID is safe and does not allow directory traversal.

    Profile IDs should only contain alphanumeric characters, underscores, and dashes.
    """
    if not isinstance(profile_id, str):
        raise TypeError("Profile ID must be a string")
    if not fullmatch(r"^[a-zA-Z0-9_-]+$", profile_id):
        raise ValueError(
            f"Invalid profile ID: {profile_id!r}. "
            "Only alphanumeric characters, underscores, and dashes are allowed."
        )


def init_working_folder(path: Path, /) -> None:
    """Create the working folder structure, including the saves directory and a default settings file."""
    if version_info < (3, 12, 0):
        raise RuntimeError(
            "Python version of at least 3.12.0 is required for PeterCLIEngine."
        )
    path.mkdir(parents=True, exist_ok=True)
    (path / "saves").mkdir(parents=True, exist_ok=True)
    init_settings(path)


def init_settings(path: Path, /, override: bool = False) -> None:
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
            except Exception:
                tmp_filepath = filepath.with_suffix(".tmp")
                try:
                    with open(tmp_filepath, "w") as file:
                        dump({}, file)
                    tmp_filepath.replace(filepath)
                except Exception as e:
                    tmp_filepath.unlink(missing_ok=True)
                    raise e
    else:
        tmp_filepath = filepath.with_suffix(".tmp")
        try:
            with open(tmp_filepath, "w") as file:
                dump({}, file)
            tmp_filepath.replace(filepath)
        except Exception as e:
            tmp_filepath.unlink(missing_ok=True)
            raise e


def safe_load_json(path: Path, /) -> Any:
    """Attempt to load and return parsed JSON from a file, returning None on any error."""
    try:
        with open(path) as file:
            return load(file)
    except Exception:
        pass


def load_settings(path: Path, /) -> Any:
    """Load and return the settings dict from settings.json in the working folder.

    Returns None if the file does not exist or cannot be parsed.
    """
    filepath = (path / "settings.json")
    if filepath.is_file():
        return safe_load_json(filepath)
    return None


def save_settings(path: Path, settings: dict[str, Any], /) -> None:
    """Write a settings dict to settings.json in the working folder, overwriting existing content.

    Writes are performed atomically using a temporary file to prevent corruption.
    """
    filepath = (path / "settings.json")
    tmp_filepath = filepath.with_suffix(".tmp")
    try:
        with open(tmp_filepath, "w") as file:
            dump(settings, file)
        tmp_filepath.replace(filepath)
    except Exception as e:
        tmp_filepath.unlink(missing_ok=True)
        raise e


def get_profiles(
    path: Path, profile_cls: type[Any], *, validate: bool = False
) -> Generator[Any, None, None]:
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
        except Exception:
            if validate:
                yield (filepath.stem, None, False)


def load_profile(path: Path, profile_cls: type[Any], profile_id: str, /) -> Any:
    """Load and return a single profile by its ID from the saves directory.

    Returns None if no matching profile file is found or the file cannot be parsed.
    """
    _validate_profile_id(profile_id)
    filepath = path / "saves" / f"{profile_id}.json"
    if filepath.is_file():
        return safe_load_json(filepath)
    return None


def save_profile(path: Path, profile: Any, /) -> None:
    """Serialize and write a profile to its corresponding file in the saves directory.

    The filename is derived from the profile's ID.  Creates the file if it
    does not yet exist, and overwrites it if it does. Writes are performed
    atomically using a temporary file to prevent corruption. Validates that
    the profile ID is safe.
    """
    _validate_profile_id(profile.id)
    filepath = path / "saves" / f"{profile.id}.json"
    tmp_filepath = filepath.with_suffix(".tmp")
    try:
        with open(tmp_filepath, "w") as file:
            profile.dump(file)
        tmp_filepath.replace(filepath)
    except Exception as e:
        tmp_filepath.unlink(missing_ok=True)
        raise e


def delete_profile(path: Path, profile_id: str, /) -> None:
    """Delete the save file for the profile with the given ID.

    Does nothing if no matching file exists.
    """
    _validate_profile_id(profile_id)
    filepath = path / "saves" / f"{profile_id}.json"
    filepath.unlink(missing_ok=True)


def profile_exists(path: Path, profile_id: str, /) -> bool:
    """Return True if a save file for the given profile ID exists in the saves directory."""
    _validate_profile_id(profile_id)
    return (path / "saves" / f"{profile_id}.json").is_file()


def migrate_save(obj: dict[str, Any], /) -> tuple[dict[str, Any], bool]:
    """Upgrade a raw save-file dict to the current schema version.

    Applies in-place migrations for each version step.  Returns the updated
    dict and a boolean indicating whether any changes were made.

    Migration steps:
    - Missing ``save_version`` (version 0 → 1): inject ``save_version: 1``
      and any fields added during that version bump.

    Args:
        obj: The raw dict parsed from a ``.json`` save file.

    Returns:
        ``(migrated_obj, changed)`` — the (possibly updated) dict and True when
        at least one migration was applied.
    """
    changed = False
    version = obj.get("save_version", 0)

    # 0 → 1: save_version field was introduced
    if version < 1:
        obj["save_version"] = 1
        version = 1
        changed = True

    # Future migration steps go here:
    # if version < 2:
    #     obj.setdefault("new_field", default_value)
    #     obj["save_version"] = 2
    #     version = 2
    #     changed = True

    return obj, changed


def migrate_saves_in_folder(path: Path, /) -> int:
    """Run :func:`migrate_save` on every profile in the ``saves/`` folder.

    Saves that are modified are written back to disk atomically.

    Args:
        path: The working directory that contains the ``saves/`` folder.

    Returns:
        The number of files that were updated.
    """
    updated = 0
    for filepath in (path / "saves").glob("*.json"):
        if not filepath.is_file():
            continue
        obj = safe_load_json(filepath)
        if not isinstance(obj, dict):
            continue
        migrated, changed = migrate_save(obj)
        if changed:
            tmp_path = filepath.with_suffix(".tmp")
            with open(tmp_path, "w") as f:
                dump(migrated, f)
            tmp_path.replace(filepath)
            updated += 1
    return updated


def export_profile(path: Path, profile_id: str, dest: Path, /) -> Path:
    """Pack a profile save file into a portable ``.clisave`` ZIP archive.

    The archive contains:
    - ``save.json`` — the raw save data.
    - ``meta.json`` — export metadata (profile ID, exported-at timestamp).

    Args:
        path: The working directory that contains the ``saves/`` folder.
        profile_id: The ID of the profile to export.
        dest: Directory or file path for the output archive.  When a directory
            is given, the archive is named ``<profile_id>.clisave``.

    Returns:
        The :class:`~pathlib.Path` of the created archive.

    Raises:
        FileNotFoundError: If no save file exists for ``profile_id``.
    """
    _validate_profile_id(profile_id)
    save_path = path / "saves" / f"{profile_id}.json"
    if not save_path.is_file():
        raise FileNotFoundError(f"Profile not found: {profile_id!r}")

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_dir():
        dest = dest / f"{profile_id}.clisave"

    meta = {
        "profile_id": profile_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "engine": "petercliengine",
    }

    with ZipFile(dest, "w", compression=ZIP_DEFLATED) as zf:
        zf.write(save_path, "save.json")
        import io
        buf = io.StringIO()
        dump(meta, buf)
        zf.writestr("meta.json", buf.getvalue())

    return dest


def import_profile(path: Path, archive: Path, /, *,
                   overwrite: bool = False) -> str:
    """Unpack a ``.clisave`` archive and copy the save file into the saves folder.

    Args:
        path: The working directory that contains the ``saves/`` folder.
        archive: Path to the ``.clisave`` archive to import.
        overwrite: When False (default) raises ``FileExistsError`` if the
            profile ID is already taken; set to True to overwrite.

    Returns:
        The profile ID extracted from the archive.

    Raises:
        FileNotFoundError: If the archive does not exist.
        ValueError: If the archive is missing ``save.json`` or ``meta.json``.
        FileExistsError: If a profile with that ID already exists and
            ``overwrite`` is False.
    """
    archive = Path(archive)
    if not archive.is_file():
        raise FileNotFoundError(f"Archive not found: {archive}")

    with ZipFile(archive, "r") as zf:
        names = zf.namelist()
        if "save.json" not in names or "meta.json" not in names:
            raise ValueError("Archive is missing save.json or meta.json")

        import io
        import json as _json
        meta_bytes = zf.read("meta.json")
        meta = _json.loads(meta_bytes.decode())
        profile_id: str = meta.get("profile_id") or ""
        if not profile_id:
            raise ValueError("meta.json is missing 'profile_id'")
        _validate_profile_id(profile_id)

        dest_path = path / "saves" / f"{profile_id}.json"
        if dest_path.is_file() and not overwrite:
            raise FileExistsError(
                f"Profile {profile_id!r} already exists. Use overwrite=True.")

        save_data = zf.read("save.json")
        dest_path.write_bytes(save_data)

    return profile_id


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


def main() -> None:
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
