# PeterCliEngine

![Python 3.14.2+](https://img.shields.io/badge/python-3.14.2%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A general-purpose framework library for building Python CLI applications and RPG-style games. Provides a command-line engine, a typed data-model system, profile management, string utilities, ANSI color theming, and game model templates.

> **Python version note:** The project is developed with Python 3.14.2 and `__init__.py` enforces this at import time. Most individual modules are compatible with Python 3.12+; only `profile_manage` (via `init_working_folder`) hard-requires 3.14.2+.

## Table of Contents

- [PeterCliEngine](#petercliengine)
  - [Table of Contents](#table-of-contents)
  - [Usage](#usage)
    - [Minimal non-game CLI example](#minimal-non-game-cli-example)
    - [Per-module demos](#per-module-demos)
  - [Modules](#modules)
  - [Command Line Engine (CLIEngine)](#command-line-engine-cliengine)
    - [Features](#features)
  - [Color \& Theming](#color--theming)
  - [Profile Management](#profile-management)
  - [Game Models](#game-models)
  - [Todo List](#todo-list)
    - [Engine \& Input](#engine--input)
    - [Data \& Persistence](#data--persistence)
    - [Game Logic](#game-logic)
    - [Testing \& Quality](#testing--quality)
  - [License: MIT](#license-mit)

## Usage

Install dependencies (currently none; for the future):

```bash
pip install -r requirements.txt
```

Run the sample `GameLauncher`:

```bash
python3 .
```

### Minimal non-game CLI example

```python
from cliengine import CLIEngine, Command

engine = CLIEngine()

@engine.add_command("greet", ["greet <name:str>"])
def cmd_greet(ctx, name: str):
    print(f"Hello, {name}!")
    return {"type": "success"}

while True:
    text = engine.read_command("> ")
    if not text:
        continue
    api = engine.run_command(None, text)
    if api["type"] == "exit":
        break
    if api["type"] == "unknown_command":
        print(f"Unknown: {api['command']!r}")
```

`Tab` auto-completes command names; `Up`/`Down` cycle through history (readline).

If used as a package inside another folder, prefix relative imports with `.` (e.g. `from .utils import ...`). The `__init__.py` re-exports everything and works with `import *`.

### Per-module demos

Each module can be run directly as a script for a self-contained demonstration:

```bash
python3 cliengine.py      # command parsing, dispatch, history demo
python3 color.py          # ANSI output for DARK and LIGHT themes
python3 datatype.py       # typed DataType construction and JSON round-trip
python3 str_convert.py    # all five case converters on sample strings
python3 utils.py          # istype generics, interrupt-decorator behavior
python3 profile_manage.py # unique ID collision avoidance in a temp directory
python3 models/data.py    # game data types + NPC JSON dump/reload
```

## Modules

| File | Purpose |
|---|---|
| `cliengine.py` | CLI engine: command parsing, typed arguments, history, readline/tab-completion |
| `color.py` | Dependency-free ANSI color/style helpers and `ColorTheme` dataclass |
| `datatype.py` | Pydantic/dataclass-style base class with typed variables, JSON load/dump |
| `models/` | Game data structures subpackage (see [Game Models](#game-models)) |
| `profile_manage.py` | Working-directory management: `saves/`, `settings.json`, profile CRUD |
| `str_convert.py` | String case converters: `snake`, `camel`, `pascal`, `title`, `kebab` |
| `utils.py` | `istype`, interrupt-handling decorators, `match_input` |
| `myjson/` | Custom JSON encoder with clean float formatting and compact pretty-print |

## Command Line Engine (CLIEngine)

A command-parsing and dispatch engine suitable for any CLI application, not just games.

Commands are registered with pattern strings like `"go <direction:str>"` or `"add <a:int> [b:int]"`. Built-in argument types: `int`, `num` (float), `bool`, `str`.

The engine works best as a class-level attribute (`cls.engine`) so decorated methods can be registered at class definition time.

All handlers return an API dict with a `"type"` key (`"exit"`, `"help"`, `"success"`, `"failed"`, `"interrupted"`, `"unknown_command"`, ...), letting the caller process results uniformly.

### Features

- Typed required (`<name:type>`) and optional (`[name:type]`) arguments
- Pattern-coverage warnings for unreachable patterns
- Quoted string tokens and backslash escaping in input
- **In-memory history** -- `engine.get_history()` returns every submitted command
- **Readline integration** -- `engine.setup_readline(history_file=None)` enables `Tab` completion (by command name prefix) and optional history file persistence; `engine.read_command(prompt)` wraps `input()` and records each command automatically. Degrades gracefully on platforms without `readline` (e.g. Windows)

## Color & Theming

`color.py` provides dependency-free ANSI styling:

```python
from color import colorize, FG, STYLE, DARK_THEME

print(colorize("Hello!", fg=FG.BRIGHT_GREEN, style=STYLE.BOLD))
print(DARK_THEME.error("Something went wrong."))
```

- `is_color_supported()` -- respects `NO_COLOR` env var, `TERM=dumb`, and non-TTY stdout
- `colorize(text, fg, bg, style)` -- wraps text in ANSI codes; returns plain text when color is unsupported
- `FG`, `BG`, `STYLE` -- constant namespaces for all standard ANSI codes
- `ColorTheme` -- dataclass with `prompt`, `error`, `success`, `warning`, `info`, `heading` callables
- `DEFAULT_THEME` (all identity, zero behavior change), `DARK_THEME`, `LIGHT_THEME` built in

Pass a `ColorTheme` to `GameContext`/`GameLauncher` (default: `DEFAULT_THEME`) to opt into styled output.

## Profile Management

Profile save files and settings are stored in a configurable working directory (default: `~/cliengine`). The `saves/` folder and `settings.json` are created automatically on first launch.

**ID collision avoidance:** `generate_unique_profile_id(path, name)` derives a snake_case ID from the display name, appending `_1`, `_2`, ... until a free slot is found.

Save files are JSON. With an existing `a.json`, creating another profile named `a` yields `a_1.json`, then `a_2.json`, etc.

## Game Models

The `models/` subpackage contains game-oriented templates, split by concern:

| Module | Contents |
|---|---|
| `models/data.py` | Pure data types: `ItemType`, `Item`, `Location`, `NPC`, `Achievement`, `Event`, `Quest`, `SkillType` |
| `models/profile.py` | `PlayerProfile` -- typed save data with `save()` |
| `models/context.py` | `GameContext` -- runtime game loop with event hooks |
| `models/launcher.py` | `GameLauncher` -- profile CRUD menu |

All names are re-exported from `models/__init__.py`, so `from models import GameLauncher` still works.

**`PlayerProfile` fields:** id, name, gamemode, difficulty, gamerules, character\_xp, skill\_xp, quest\_stages, achievements, inventory, total\_playtime, last\_updated.

WIP data models:
- `Item` -- stack size, modification
- `Location` -- connection data between areas
- `NPC` -- location, greetings, dialogs
- `Achievement` -- unlock logic and rewards
- `Event` -- trigger conditions, narration, rewards, lifecycle
- `Quest` -- stages, rewards
- `SkillType` -- XP curves, level caps, bonuses

## Todo List

### Engine & Input
- [ ] Thread `ColorTheme` through `GameContext` and `GameLauncher` print calls
- [ ] Persist readline history between sessions via `setup_readline(history_file=...)` in `GameLauncher`
- [ ] Command aliases: map short names or abbreviations to full command names
- [ ] Tab-completion of argument values (item IDs, location names) via a provider callback on `Command`
- [ ] `!!` / `repeat` built-in to re-run the most-recent history entry
- [ ] Custom user-defined `ArgType` registration so domain code can extend `ARG_TYPES`
- [ ] Restrict/buffer input during narrations and dialogues

### Data & Persistence
- [ ] Use `settings.json` for preferences: auto-enter last profile, auto-save interval, color theme selection
- [ ] Save file versioning and migration: detect old formats and upgrade on load
- [ ] Profile import/export: copy a `.json` save to a portable archive with metadata
- [ ] `myjson` encoder: register `DataType` as a natively serializable type for nested structures
- [ ] Auto-save timer: save the active profile at a configurable interval in a background thread

### Game Logic
- [ ] Implement game model class logic: item actions, location travel, NPC dialogue, quest advancement
- [ ] Flesh out `GameContext.is_triggerable` and `trigger_event` with real event-condition evaluation
- [ ] `GameContext` event queue: schedule and replay events non-interactively for scripted sequences
- [ ] Item stack merging and split logic in `PlayerProfile.inventory`
- [ ] Skill XP and level-up resolution using `SkillType.levels` curve

### Testing & Quality
- [ ] Full test suite (`pytest`) covering `istype`, `DataType` dispatch, `CLIEngine` matching, `str_convert`
- [ ] Type-check the whole project with `mypy --strict` and fix remaining `Any` escapes
- [ ] CI workflow (GitHub Actions) running tests on Python 3.12 and 3.14

## License: MIT

[MIT License](./LICENSE.txt)
