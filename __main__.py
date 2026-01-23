from pathlib import Path

from models import *


def main():
    launcher = GameLauncher(GameContext, PlayerProfile,
                            Path.home() / "cliengine")
    launcher.run()


if __name__ == "__main__":
    main()
