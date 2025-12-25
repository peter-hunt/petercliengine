from pathlib import Path


__all__ = [
    "init_working_folder", "init_settings",
    "load_settings", "list_profiles",
]


def init_working_folder(path: Path, /):
    path.mkdir(parents=True, exist_ok=True)


def init_settings(path: Path, /):
    (path / "settings.json").touch(exist_ok=True)


def load_settings(path: Path, /) -> dict[str, any] | None:
    filepath = (path / "settings.json")
    if filepath.is_file():
        print('nope')


def list_profiles(path: Path, cls):
    pass
