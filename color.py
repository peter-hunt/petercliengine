import os
import sys
from dataclasses import dataclass, field
from typing import Callable


__all__ = [
    "FG", "BG", "STYLE",
    "is_color_supported",
    "colorize",
    "ColorTheme",
    "DEFAULT_THEME", "DARK_THEME", "LIGHT_THEME",
]

# ---------------------------------------------------------------------------
# ANSI code namespaces
# ---------------------------------------------------------------------------


class FG:
    """ANSI foreground color escape codes."""
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    # bright variants
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    RESET = "\033[39m"


class BG:
    """ANSI background color escape codes."""
    BLACK = "\033[40m"
    RED = "\033[41m"
    GREEN = "\033[42m"
    YELLOW = "\033[43m"
    BLUE = "\033[44m"
    MAGENTA = "\033[45m"
    CYAN = "\033[46m"
    WHITE = "\033[47m"
    RESET = "\033[49m"


class STYLE:
    """ANSI text style escape codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    STRIKE = "\033[9m"


# ---------------------------------------------------------------------------
# Color support detection
# ---------------------------------------------------------------------------

def is_color_supported() -> bool:
    """Return True when ANSI color codes are likely to render correctly.

    Color is considered unsupported when:
    - The ``NO_COLOR`` environment variable is set (https://no-color.org/).
    - ``TERM`` is ``"dumb"``.
    - stdout is not a TTY (e.g. piped to a file).
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()


# ---------------------------------------------------------------------------
# colorize
# ---------------------------------------------------------------------------

def colorize(
    text: str,
    fg: str | None = None,
    bg: str | None = None,
    style: str | None = None,
) -> str:
    """Wrap *text* in ANSI escape sequences.

    Returns plain *text* unchanged when color is not supported
    (see :func:`is_color_supported`).

    Args:
        text:  The string to style.
        fg:    An ANSI foreground code from :class:`FG`, or ``None``.
        bg:    An ANSI background code from :class:`BG`, or ``None``.
        style: An ANSI style code from :class:`STYLE`, or ``None``.

    Returns:
        The styled string when color is supported, otherwise *text* as-is.
    """
    if not is_color_supported():
        return text
    prefix = (style or "") + (fg or "") + (bg or "")
    if not prefix:
        return text
    return f"{prefix}{text}{STYLE.RESET}"


# ---------------------------------------------------------------------------
# ColorTheme
# ---------------------------------------------------------------------------

@dataclass
class ColorTheme:
    """A collection of text-styling callables for common semantic roles.

    Each field is a ``Callable[[str], str]`` that accepts plain text and
    returns a (possibly styled) string.  The built-in themes expose all
    fields; custom themes can override individual ones.

    Fields:
        prompt:  Used for interactive prompts shown to the user.
        error:   Used for error/failure messages.
        success: Used for success/confirmation messages.
        warning: Used for non-fatal warnings.
        info:    Used for neutral informational output.
        heading: Used for section or context headings.
    """
    prompt:  Callable[[str], str] = field(default=lambda t: t)
    error:   Callable[[str], str] = field(default=lambda t: t)
    success: Callable[[str], str] = field(default=lambda t: t)
    warning: Callable[[str], str] = field(default=lambda t: t)
    info:    Callable[[str], str] = field(default=lambda t: t)
    heading: Callable[[str], str] = field(default=lambda t: t)


# ---------------------------------------------------------------------------
# Built-in themes
# ---------------------------------------------------------------------------

#: No-op theme: all fields are identity functions.
#: Use this as a safe default; existing ``print()`` calls are unaffected.
DEFAULT_THEME = ColorTheme()

#: Dark-terminal theme: colours chosen for legibility on dark backgrounds.
DARK_THEME = ColorTheme(
    prompt=lambda t: colorize(t, fg=FG.BRIGHT_CYAN, style=STYLE.BOLD),
    error=lambda t: colorize(t, fg=FG.BRIGHT_RED,  style=STYLE.BOLD),
    success=lambda t: colorize(t, fg=FG.BRIGHT_GREEN),
    warning=lambda t: colorize(t, fg=FG.BRIGHT_YELLOW),
    info=lambda t: colorize(t, fg=FG.BRIGHT_WHITE),
    heading=lambda t: colorize(t, fg=FG.BRIGHT_MAGENTA, style=STYLE.BOLD),
)

#: Light-terminal theme: colours chosen for legibility on light backgrounds.
LIGHT_THEME = ColorTheme(
    prompt=lambda t: colorize(t, fg=FG.BLUE,    style=STYLE.BOLD),
    error=lambda t: colorize(t, fg=FG.RED,     style=STYLE.BOLD),
    success=lambda t: colorize(t, fg=FG.GREEN),
    warning=lambda t: colorize(t, fg=FG.YELLOW),
    info=lambda t: colorize(t, fg=FG.BLACK),
    heading=lambda t: colorize(t, fg=FG.MAGENTA, style=STYLE.BOLD),
)


# ---------------------------------------------------------------------------
# Sample
# ---------------------------------------------------------------------------

def main():
    print(f"Color supported: {is_color_supported()}")
    for theme_name, theme in [("DARK", DARK_THEME), ("LIGHT", LIGHT_THEME)]:
        print(f"\n--- {theme_name} THEME ---")
        print(theme.heading("Heading"))
        print(theme.info("Info message"))
        print(theme.success("Success message"))
        print(theme.warning("Warning message"))
        print(theme.error("Error message"))
        print(theme.prompt("Prompt text"))


if __name__ == "__main__":
    main()
