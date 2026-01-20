# PeterCliEngine

A common framework library for Python RPG like CLI engine for CLI interface and RPG, RPG profile manager template, Pydantic/dataclass styled data type base class for easier data management and JSON loading/dumping, and future contents to come.

## Usage

The code in the project is not organized to be executed directly. There will be some that require dependency libraries listed in the `requirements.txt`. Some example usages have been added in the `main()` functions in each file.

If used in a folder, put `.` in front of the relative imports, e.g. `utils.py`, to have it work properly. The `__init__.py` is already implemented to contain all content and work with `import *`.

For now, the only executable system would be the `profile_manage.py`, which will create a working directory at `~/cliengine`, where `~` is the home folder differing by username and OS, usually being `/Users/<username>` and `/home/<username>`.

## Table of Content

- `cliengine.py`: CLI engine for CLI interface and RPG;
- `datatype.py`: Pydantic/dataclass styled data type base class for easier data management and JSON loading/dumping;
- `game_objects.py`: Game internal data structure templates;
- `profile_manage.py`: Folder management functionalities with `saves` and `settings.json`;
- `str_convert.py`: String conversion functions between cases and capitalizing phrases etc.;
- `utils.py`: Utility script for general usage by other modules.

## Command Line Engine (CLIEngine)

A work-in-progress engine for command line interactions for applications. The engine handles the command parsing, basic argument types, and fitting the command to execute the corresponding functions.

Currently, the engine works best as the class attribute, like `cls.engine` to support adding new commands to the class value of the `CLIEngine` type. All the given commands are given an API, with `"type"` key giving values like `"exit"`, `"help"`, `"unknown_command"`, and so on, leaving the printing customization to the usage module to decide on. And as a convention and to make it easier, also as shown in the implementation of the sample `GameContext` and `GameLauncher` in `game_objects.py`, user-defined command methods could also return API dict with `"type"` being `"success"`, `"failed"`, `"interrupted"`, and so on to align with the format, making the processing of the parsing result more automatic.

### Features

- Defining commands with arguments of different value types;
- Parsing commands to interact with (game) context directly or to return a command API map;
- Checking for overlapping definitions and var types.

## Profile Management

As inherited from the [Skyblock Remake](https://github.com/peter-hunt/skyblock) project, the structure for profile management still large follows that:

Currently, the profile save files and settings (for future use) will be saved in the `~/cliengine` working directory for the usage demonstration code, which can be configured easily upon usage. The `saves` folder and `settings.json` configuration file will be automatically created on launch, and `settings.json` will be automatically replaced with a default one should the old one be an invalid JSON file.

As a rule of thumb for usage, try to name it something unique that it won't overlap with other folders. Or better, use some common directory like `~/petercliengine` to put the data for each game in a subdirectory, so managing the distinct game folder by ID will be easier (if this engine even goes that far).

In the saves folder, the save files are written in JSON format with profile ID with optional number identifier to avoid overlapping. For example, with an existing `a.json`, another new profile with `a` being the name will have ID `a_1.json`, and the next one `a_2.json`, and so on. Even created names like `a_1.json` will go up with the number suffix to avoid `a_1_1.json` with the chain, although this could be potentially confusing for `a_1` to resolve to `a_4.json` when you forget about the other ones.

## Game Objects

Internal game structures like `PlayerProfile`, `GameContext`, `Item`, and so on, as templates for implementing game content. Game content can be loaded from a data folder for items, skills, quests, etc, where the save files will be saved in `saves` and `settings.json` in the custom game folder.

Here are the list of game structures and progress:
- `Item`: WIP. Handles item stack size, item modification and customization, and so on;
- `Location`: WIP. Handles the location and connection data between locations;
- `NPC`: WIP. Handles location, greetings, dialogs, and so on;
- `Achievement`: WIP. Handles the logic of obtaining each achievement, potential reward and bonuses, and so on;
- `Event`: WIP. Handles random events or game events with specific triggering;
- `Quest`: WIP. Handles the unlock, advancement, and rewards of quests;
- `SkillType`: WIP. Handles the skill system calculations of XP-level, bonuses, and so on;
- `PlayerProfile`: A working basic template of player profile data with basic loading and saving mechanics;
- `GameContext`: The running instance for the game with a profile to run all the game logic;
- `GameLauncher`: The menu to create, rename, delete, and enter the profiles and adjusting settings (WIP).

## Todo List

- Implementation of game object functionalities, loading, and management.
- Usage of settings file to indicate preferences in whether to auto-enter last-loaded profile, auto-save toggle and interval, and so on;
- Pretty printing and potentially color theme support;
- Command line history system and potentially even full control over command line input to disallow typing spam during narrations and dialogues.

# License: MIT

[MIT License](./LICENSE.txt)
