from pathlib import Path

from datatype import DataType
from myjson import load, dump


__all__ = [
    "init_working_folder", "init_settings",
    "load_settings", "get_profiles",
]


def init_working_folder(path: Path, /):
    path.mkdir(parents=True, exist_ok=True)
    (path / "saves").mkdir(parents=True, exist_ok=True)
    init_settings(path)


def init_settings(path: Path, /, override: bool = False):
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
    try:
        with open(path) as file:
            return load(file)
    except:
        pass


def load_settings(path: Path, /) -> dict[str, any] | None:
    filepath = (path / "settings.json")
    if filepath.is_file():
        return safe_load_json(filepath)


def get_profiles(path: Path, profile_cls: DataType):
    for filepath in (path / "saves").glob("*.json"):
        if not filepath.is_file():
            continue
        try:
            with open(filepath) as file:
                profile = profile_cls.load(file)
            yield (profile.name, profile.id)
        except:
            pass
