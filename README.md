# PeterCliEngine

![Python 3.12.0+](https://img.shields.io/badge/python-3.12.0%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![CI](https://img.shields.io/github/actions/workflow/status/peterhunt/petercliengine/ci.yml?label=CI)

A general-purpose framework library for building Python CLI applications and RPG-style games. Provides a command-line engine, a typed data-model system, profile management, string utilities, ANSI color theming, and game model templates.

> **Python version note:** The project is compatible with Python 3.12.0+ and `__init__.py` enforces this at import time. All modules are fully compatible with Python 3.12+.

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
  - [Roadmap](#roadmap)
    - [DataType System](#datatype-system)
    - [CLIEngine](#cliengine)
    - [Profile \& Settings](#profile--settings)
    - [Game Models](#game-models-1)
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
- **Command aliases** -- map short names or abbreviations to full command names via `aliases=[...]`
- **Custom `ArgType` registration** -- extend `ARG_TYPES` with `register_argtype()` / `replace_argtype()`
- **`!!` / `repeat` built-in** -- re-runs the most-recent history entry
- **Input locking** -- `lock_input()` / `unlock_input()` buffer commands during narrations; buffered commands are replayed automatically on unlock
- **In-memory history** -- `engine.get_history()` returns every submitted command
- **Tab-completion of argument values** -- pass a `value_completer(arg_name, partial_text) -> list[str]` callback to `Command` or `add_command()`
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

**Settings (`settings.json`):** `color_theme` (`"default"` | `"dark"` | `"light"`), `auto_enter_last_profile` (bool), `auto_save_interval` (seconds, `0` = disabled).

**Save versioning & migration:** every save carries a `save_version` integer. `migrate_save(obj)` upgrades old saves in-place; `migrate_saves_in_folder(path)` batch-upgrades all files in `saves/` and returns the count of updated files.

**Import / export:** `export_profile(path, profile_id, dest)` packs a save into a portable `.clisave` ZIP archive containing `save.json` and `meta.json`. `import_profile(path, archive)` unpacks it back into `saves/`.

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

**`PlayerProfile` fields:** `id`, `name`, `save_version`, `gamemode`, `difficulty`, `gamerules`, `character_xp`, `skill_xp`, `quest_stages`, `achievements`, `inventory`, `event_occurrences`, `total_playtime`, `last_updated`.

**Inventory helpers on `PlayerProfile`:**
- `find_items(item_id)` -- return all stacks matching the given ID
- `add_item(item_id, quantity, item_type=None)` -- fills existing stackable stacks first, then creates new ones
- `remove_item(item_id, quantity)` -- LIFO stack removal; returns shortfall
- `add_skill_xp(skill_id, amount, skill_registry)` -- adds XP and returns a list of newly crossed levels

**Data model methods:**
- `ItemType`: `can_stack_with(item)`, `available_stack_space(stack)`
- `Item`: `use()`, `drop()`
- `Location`: `can_travel_to(location_id)`, `travel_to(location_id)` (connections list)
- `NPC`: `greet()` (random greeting), `dialog()` (random dialog line)
- `Achievement`: `unlock_message()`
- `Event`: `narrate()` (prints all narration lines)
- `Quest`: `is_complete()`, `advance_stage()`, `stage_description()`
- `SkillType`: `level_for_xp(xp)`, `xp_to_next_level(xp)`

**`GameContext` event system:**
- `is_triggerable(event)` -- evaluates all trigger conditions (`always`, `never`, `quest`, `quest_complete`, `achievement`, `skill_xp`, `item`) and checks the occurrence limit
- `trigger_event(event)` -- narrates, applies rewards (`quest_stage`, `achievement`, `add_skill_xp`, `add_item`), and increments `event_occurrences`
- `schedule_event(event)` / `flush_event_queue()` -- queue events for deferred firing; `flush_event_queue()` is called automatically by `update()`
- `start_autosave(interval)` / `stop_autosave()` -- background auto-save daemon thread

## Roadmap

### DataType System
- **Auto-serialize nested `DataType` fields** — `dumps()`/`loads()` currently treat fields whose type is a `DataType` subclass (e.g. `list[Item]` in `PlayerProfile.inventory`) as raw JSON. Auto-detection and round-tripping should be built into `Variable` so no manual `loader`/`dumper` is needed for nested types.
- **`__eq__` and `__hash__`** — field-wise equality and a frozen-instance hash mode so `DataType` objects can be stored in sets or used as dict keys.
- **`copy()` / `clone()`** — shallow and deep copy helpers; currently users must reconstruct instances manually.
- **Nullable fields (`None` default)** — `Variable(default=None)` is ambiguous with "no default"; add an explicit `nullable=True` flag so a field can genuinely hold `None`.
- **`diff()` / `patch()`** — field-level diffing between two instances of the same type, useful for detecting which save fields changed.
- **`Variable(choices=...)`** — enum-style constraint without requiring a full validator callable.

### CLIEngine
- **Command groups / subcommands** — hierarchical dispatch (`inventory add`, `inventory drop`) rather than flat top-level names only.
- **Pre/post command hooks** — middleware callbacks invoked before and after every dispatch, enabling logging, auth checks, or side-effect tracking.
- **Multi-word phrase aliases** — current aliases must be single tokens; enable phrases like `"pick up"` as an alias for `take`.
- **Async input support** — an `asyncio`-compatible variant of `read_command` / `run_command` for integration with async game loops or GUIs.

### Profile & Settings
- **Settings schema validation** — `settings.json` is loaded as an unvalidated `dict`; validate it against a schema and emit warnings for unrecognised or out-of-range keys.
- **Pre-migration backup** — `migrate_saves_in_folder` overwrites files in-place; create a `.bak` snapshot before applying migrations.
- **Multiple working directories / profile groups** — support for separate save folders (e.g. per-game-title) under a shared root.

### Game Models
- **World registry in `GameContext`** — a built-in registry (`context.register(location)`, `context.get_location(id)`, etc.) for `Location`, `NPC`, `Quest`, `SkillType`, `ItemType`, `Achievement`, and `Event` objects, so game code doesn't have to manage lookup dicts manually.
- **`PlayerProfile.inventory` polymorphic loading** — `list[Item]` currently round-trips through raw dicts; wire up auto-`DataType` loading (see above) so `Item` instances survive a save/load cycle without manual `loader=` on the variable.
- **`Event` trigger OR / NOT logic** — the current evaluator is pure AND; add `["or", [...]]` and `["not", [...]]` wrapper conditions for richer scripted sequences.
- **`Quest` per-stage descriptions** — `Quest.stages` is only an integer count; add a `stage_labels: list[str]` field to associate human-readable descriptions with each stage.
- **`SkillType` per-level modifiers** — XP thresholds express level-up points but carry no per-level effect data; add an optional `modifiers: list[dict]` field for bonuses, unlocks, and stat changes.
- **NPC dialogue trees** — replace the flat `dialogs: list[str]` random selection with a simple state-machine structure (`{"id": ..., "text": ..., "next": [...]}`) enabling branching conversations.
- **Equipment slots on `PlayerProfile`** — a `dict[str, Item | None]` `equipment` field for head/body/weapon/offhand slots, distinct from the general inventory.
- **`Location` description and inhabitant lists** — add a `description: str` field and optional `npcs: list[str]` / `items: list[str]` ID lists so locations carry their own content manifest.

### Testing & Quality
- **Property-based tests (Hypothesis)** — complement fixed unit tests with generated inputs for `istype`, `DataType.__init__` validation, and `tokenize`.
- **Coverage reporting in CI** — add `pytest --cov` with a minimum threshold and upload an HTML report or coverage badge.
- **Benchmark suite** — micro-benchmarks for `myjson.dumps`, `istype`, and `CLIEngine.run_command` to catch regressions.

## License: MIT

[MIT License](./LICENSE.txt)
