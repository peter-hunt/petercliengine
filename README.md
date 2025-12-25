# PeterCliEngine

A common framework library for Python CLI like CLI engine for CLI interface and RPG, RPG profile manager template, Pydantic/dataclass styled data type base class for easier data management and JSON loading/dumping, and future contents to come.

## Usage

The code in the project is not organized to be executed directly. There will be some that require dependency libraries listed in the `requirements.txt`. Example usages might be added in the future.

If used in a folder, put `.` in front of the relative imports, e.g. `utils.py`, to have it work properly. The `__init__.py` is already implemented to contain all content and work with `import *`.

## Table of Content

- `cliengine.py`: CLI engine for CLI interface and RPG.
- `datatype.py`: Pydantic/dataclass styled data type base class for easier data management and JSON loading/dumping.
- `profile_manage.py` and `profile_template`: profile manager with working folder management with `saves` and `settings.json`. The profile class template is for functionality integration with the management code.

## Command Line Engine (CLIEngine)

A work-in-progress engine for command line interactions for applications. The engine handles the command parsing, basic argument types, and fitting the command to execute the corresponding functions. More documentation will be added as the functionalities refine.


# License: MIT

[MIT License](./LICENSE.txt)
