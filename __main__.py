from pathlib import Path

from game_objects import *


def main():
    launcher = GameLauncher(GameContext, PlayerProfile,
                            Path.home() / "cliengine")
    launcher.run()


if __name__ == "__main__":
    main()
