from re import Match, compile as re_compile, VERBOSE
from typing import Any, Callable

try:
    import readline as _readline
    _READLINE_AVAILABLE = True
except ImportError:
    _readline = None
    _READLINE_AVAILABLE = False


__all__ = [
    "bool_convert",
    "ArgType", "ARG_TYPES", "parse_argtype",
    "Arg",

    "CommandPattern", "Command",
    "tokenize",
    "CLIEngine",
]


TOKEN_REGEX = re_compile(
    r"""
    <(?P<reqname>[a-zA-Z_]\w*)(:(?P<reqtype>[a-zA-Z_]\w*))?>
    |
    \[(?P<optname>[a-zA-Z_]\w*)(:(?P<opttype>[a-zA-Z_]\w*))?\]
    |
    (?P<word>[^\s]+)
    """,
    VERBOSE,
)

TRUE_LITERALS = (r"1", r"true", r"yes", r"y", r"t")
FALSE_LITERALS = (r"0", r"false", r"no", r"n", r"f")
BOOL_LITERALS = TRUE_LITERALS + FALSE_LITERALS


def bool_convert(v: str, /) -> bool:
    """Converts a string literal to a boolean value.

    Recognizes common truthy strings (``'1'``, ``'true'``, ``'yes'``, ``'y'``,
    ``'t'``) and falsy strings (``'0'``, ``'false'``, ``'no'``, ``'n'``, ``'f'``),
    case-insensitively.

    Args:
        v (str): The string to convert.

    Returns:
        bool: True if ``v`` is a truthy literal, False if it is a falsy literal.

    Raises:
        ValueError: If ``v`` does not match any known boolean literal.
    """
    v = v.lower()
    if v in TRUE_LITERALS:
        return True
    elif v in FALSE_LITERALS:
        return False
    else:
        raise ValueError(f"Invalid boolean literal: {v}")


class ArgType:
    """Defines a named argument type with a regex pattern and a converter function.

    Attributes:
        name (str): The name of the type (e.g. ``'int'``, ``'str'``).
        pattern (re.Pattern): The compiled regex pattern used to validate values.
        converter (Callable[[str], Any]): A callable that converts a valid string
            value to the target Python type.
    """

    def __init__(self, name: str, pattern: str, converter: Callable[[str], Any]):
        """Initializes an ArgType with a name, regex pattern, and converter.

        Args:
            name (str): The display name of this argument type.
            pattern (str): A regex pattern string that valid values must fully match.
            converter (Callable[[str], Any]): A callable that parses a matched string
                into the desired Python type.
        """
        self.name = name
        self.pattern = re_compile(pattern)
        self.converter = converter

    def is_valid(self, value: str) -> bool:
        """Checks whether a string value matches this type's pattern.

        Args:
            value (str): The string to validate.

        Returns:
            bool: True if ``value`` fully matches the pattern, False otherwise.
        """
        return bool(self.pattern.fullmatch(value))

    def convert(self, value: str):
        """Converts a string value to this type's target Python type.

        Args:
            value (str): The string to convert.

        Returns:
            Any: The converted value.
        """
        return self.converter(value)


ARG_TYPES: dict[str, ArgType] = {
    "int": ArgType("int", r"[+-]?\d+", int),
    "num": ArgType("num", r"[+-]?(\d*\.?\d+|\d+\.?\d*)", float),
    "bool": ArgType("bool", rf"(?i:{'|'.join(BOOL_LITERALS)})", bool_convert),
    "str": ArgType("str", r".+", lambda x: x),
}


def parse_argtype(name: str, type_name: str | None, /):
    """Resolves an argument type by name from the global ARG_TYPES registry.

    If ``type_name`` is None, defaults to the ``'str'`` type.

    Args:
        name (str): The argument name, used for error messages.
        type_name (str | None): The name of the desired type, or None to default
            to ``'str'``.

    Returns:
        ArgType: The resolved ``ArgType`` instance.

    Raises:
        ValueError: If ``type_name`` is not None and not found in ``ARG_TYPES``.
    """
    if type_name is None:
        return ARG_TYPES["str"]

    if type_name not in ARG_TYPES:
        raise ValueError(f"Unknown type {type_name!r} "
                         f"in argument {name}:{type_name}")
    return ARG_TYPES[type_name]


class Arg:
    """Represents a single parsed token in a command pattern.

    Attributes:
        kind (str): Either ``'word'`` for a literal keyword or ``'var'`` for a
            variable argument.
        name (str): The literal keyword or the variable's name.
        type (ArgType): The type used to validate and convert the argument value.
        is_optional (bool): True if the argument is optional (enclosed in ``[…]``).
    """

    def __init__(self, kind: str, name: str, type_obj: ArgType | None = None, is_optional: bool = False):
        """Initializes an Arg with its kind, name, type, and optionality.

        Args:
            kind (str): ``'word'`` for a literal token, or ``'var'`` for a typed
                variable argument.
            name (str): The literal keyword text or variable name.
            type_obj (ArgType | None): The argument type. Defaults to the ``'str'``
                ArgType if None.
            is_optional (bool): Whether the argument is optional. Defaults to False.
        """
        self.kind = kind
        self.name = name
        self.type = type_obj or ARG_TYPES["str"]
        self.is_optional = is_optional


def parse_command(s: str) -> list[Arg]:
    """Parses a command pattern string into an ordered list of Arg objects.

    Recognizes three token forms:

    - ``<name>`` or ``<name:type>``: required variable argument.
    - ``[name]`` or ``[name:type]``: optional variable argument.
    - Any other non-whitespace sequence: literal keyword.

    Args:
        s (str): The command pattern string to parse.

    Returns:
        list[Arg]: The ordered list of parsed ``Arg`` tokens.

    Raises:
        ValueError: If a keyword appears after a variable, a required variable
            appears after an optional one, or a variable name is duplicated.
    """
    parts = []
    arg_names = {*()}
    saw_variable = False
    saw_optional = False

    for m in TOKEN_REGEX.finditer(s):
        if m.group("word"):
            if saw_variable or saw_optional:
                raise ValueError("Keyword arg found after variable arg.")
            parts.append(Arg("word", m.group("word")))
            continue

        saw_variable = True
        if m.group("reqname"):
            if saw_optional:
                raise ValueError("Required arg found after optional arg.")
            name = m.group("reqname")
            type_obj = parse_argtype(name, m.group("reqtype"))

            if name in arg_names:
                raise ValueError(f"Duplicate argument name: {name}")

            arg_names.add(name)
            parts.append(Arg("var", name, type_obj, False))
        else:
            saw_optional = True
            name = m.group("optname")
            type_obj = parse_argtype(name, m.group("opttype"))

            if name in arg_names:
                raise ValueError(f"Duplicate argument name: {name}")

            arg_names.add(name)
            parts.append(Arg("var", name, type_obj, True))

    return parts


class CommandPattern:
    """Parses and matches a command pattern against incoming token lists.

    A pattern is a string of space-separated tokens where bare words match
    literally, ``<name>`` or ``<name:type>`` denotes a required typed argument,
    and ``[name]`` or ``[name:type]`` denotes an optional typed argument.

    Example:
        >>> cp = CommandPattern("get coord <player>")
        >>> cp.match(["get", "coord", "Steve"])
        {'player': 'Steve'}

    Attributes:
        pattern_str (str): The original pattern string.
        parts (list[Arg]): The parsed sequence of Arg tokens.
    """

    pattern_str: str
    parts: list[Arg]

    def __init__(self, pattern_str: str):
        """Parses the given pattern string into an ordered list of Arg parts.

        Args:
            pattern_str (str): The command pattern string to parse.
        """
        self.pattern_str = pattern_str
        self.parts = parse_command(pattern_str)

    def match(self, tokens: list[str]) -> dict[str: any] | None:
        """Attempts to match a list of tokens against this command pattern.

        Args:
            tokens (list[str]): The tokenized input to match.

        Returns:
            dict[str, Any] | None: A dict mapping variable names to their converted
                values if the tokens match, or None if they do not.
        """
        idx = 0
        parsed = {}

        for arg in self.parts:
            if arg.kind == "word":
                if idx >= len(tokens) or tokens[idx] != arg.name:
                    return
                idx += 1
            elif arg.kind == "var" and not arg.is_optional:
                if idx >= len(tokens) or not arg.type.is_valid(tokens[idx]):
                    return
                parsed[arg.name] = arg.type.convert(tokens[idx])
                idx += 1
            elif arg.kind == "var" and arg.is_optional:
                if idx < len(tokens) and arg.type.is_valid(tokens[idx]):
                    parsed[arg.name] = arg.type.convert(tokens[idx])
                    idx += 1
                else:
                    parsed[arg.name] = None
            else:
                raise ValueError(f"unknown arg kind: {arg}")

        if idx != len(tokens):
            return
        return parsed

    def is_covered_by(self, pattern: "CommandPattern") -> bool:
        """Determines if this pattern is fully overshadowed by another pattern.

        A pattern is overshadowed if every input that could match this pattern
        would always match the given ``pattern`` first, meaning this instance
        would never be reached.

        Args:
            pattern (CommandPattern): The pattern to check coverage against.

        Returns:
            bool: True if this pattern is fully covered by ``pattern``,
                False otherwise.

        Raises:
            ValueError: If an unrecognized argument kind is encountered.
        """
        if len(pattern.parts) < len(self.parts):
            return False
        for sarg, parg in zip(self.parts, pattern.parts[:len(self.parts)]):
            if sarg.kind == "word":
                if parg.kind == "word":
                    if sarg.name != parg.name:
                        return False
                elif parg.kind == "var":
                    if not parg.type.is_valid(sarg.name):
                        return False
                else:
                    raise ValueError(f"unknown arg kind: {parg}")
            elif sarg.kind == "var":
                if parg.kind == "word":
                    return False
                elif parg.kind == "var":
                    if sarg.type != parg.type and parg.type != "str":
                        return False
                    if not sarg.is_optional and parg.is_optional:
                        return False
                else:
                    raise ValueError(f"unknown arg kind: {parg}")
            else:
                raise ValueError(f"unknown arg kind: {sarg}")
        return all(parg.kind == "var" and parg.is_optional
                   for parg in pattern.parts[len(self.parts):])


CHECK_PATTERN_COVERAGE: bool = True


class Command:
    """Represents a named CLI command with associated patterns and a handler function.

    At construction time, if ``CHECK_PATTERN_COVERAGE`` is enabled, a warning is
    printed for any pattern that is fully covered by a preceding pattern.

    Attributes:
        name (str): The unique name of the command.
        func (Callable): The handler function called when the command matches.
        patterns (list[CommandPattern]): The parsed command patterns.
    """

    def __init__(self, name: str, func: Callable, patterns: list[str]):
        """Initializes a Command and optionally checks for pattern coverage.

        Args:
            name (str): The name of the command.
            func (Callable): The function to call when the command matches, with
                signature ``func(ctx, **parsed_args)``.
            patterns (list[str]): A list of pattern strings to register for this
                command.
        """
        self.name = name
        self.func = func
        self.patterns = [CommandPattern(p) for p in patterns]
        if CHECK_PATTERN_COVERAGE:
            for i, patt in enumerate(self.patterns[1:], 1):
                for j, other in enumerate(self.patterns[:i]):
                    if patt.is_covered_by(other):
                        print(f"Warning: pattern {j + 1} fully covers"
                              f" pattern {i + 1} (command {self.name!r})")

    def try_match(self, tokens: list[str]) -> Match:
        """Tries each pattern in order and returns the first match result.

        Args:
            tokens (list[str]): The tokenized input to match against.

        Returns:
            dict[str, Any] | None: The parsed argument dict from the first matching
                pattern, or None if no pattern matches.
        """
        for p in self.patterns:
            parsed = p.match(tokens)
            if parsed is not None:
                return parsed
        return

    def call(self, ctx, parsed_args: dict):
        """Invokes the command's handler function with parsed arguments.

        Args:
            ctx: The context object passed as the first argument to the handler.
            parsed_args (dict): Keyword arguments from pattern matching to pass
                to the handler.

        Returns:
            Any: The return value of the handler function.
        """
        return self.func(ctx, **parsed_args)


def tokenize(s: str) -> list[str]:
    """Splits a command string into tokens, respecting quoted strings and escapes.

    Quoted substrings (single or double quotes) are treated as a single token.
    Backslash escaping is supported within both quoted and unquoted contexts.

    Args:
        s (str): The raw command input string to tokenize.

    Returns:
        list[str]: The list of extracted tokens.
    """
    tokens = []
    buf = []
    in_quotes = False
    escape = False
    quote_char = None

    for ch in s:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if in_quotes:
            if ch == quote_char:
                in_quotes = False
                quote_char = None
            else:
                buf.append(ch)
            continue
        if ch in ("'", '"'):
            in_quotes = True
            quote_char = ch
            continue
        if ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
            continue
        buf.append(ch)

    if buf:
        tokens.append("".join(buf))
    return tokens


class CLIEngine:
    """A simple command-line interpreter engine that dispatches text commands.

    Commands are registered by name with one or more pattern strings. Input text
    is tokenized and matched against registered command patterns to invoke the
    corresponding handler.

    Attributes:
        commands (dict[str, Command]): The registry of registered commands,
            keyed by name.
        history (list[str]): In-memory log of every non-empty command submitted
            via :meth:`run_command` or :meth:`read_command`.
    """

    def __init__(self):
        """Initializes the CLIEngine and registers the built-in commands."""
        self.commands: dict[str, Command] = {}
        self.history: list[str] = []
        self._readline_setup: bool = False
        self._register_builtin_commands()

    def register(self, cmd: Command):
        """Registers a Command object with the engine.

        Args:
            cmd (Command): The command to register.

        Raises:
            ValueError: If a command with the same name is already registered.
        """
        if cmd.name in self.commands:
            raise ValueError(f"Duplicate command name '{cmd.name}'")
        self.commands[cmd.name] = cmd
        # invalidate cached completions whenever commands change
        self._readline_setup = False

    def add_command(self, name: str, patterns: list[str]) -> Callable:
        """Returns a decorator that registers the decorated function as a command.

        Args:
            name (str): The name of the command to register.
            patterns (list[str]): The list of pattern strings for the command.

        Returns:
            Callable: A decorator that wraps the function in a ``Command``,
                registers it, and returns the original function unchanged.
        """
        def wrapper(func: Callable):
            self.register(Command(name, func, patterns))
            return func
        return wrapper

    def _register_builtin_commands(self):
        """Registers the built-in ``help`` and ``exit`` commands."""
        self.register(Command(
            name="help",
            func=self._cmd_help,
            patterns=["help [command:str]"]
        ))

        self.register(Command(
            name="exit",
            func=self._cmd_exit,
            patterns=["exit", "quit"]
        ))

    def _cmd_help(self, ctx, command=None):
        """Lists available commands or shows pattern help for a specific command.

        Args:
            ctx: The current context (unused).
            command (str | None): The name of the command to look up, or None to
                list all commands.

        Returns:
            dict: A result dict with ``'type': 'help'`` and a ``'content'`` string.
        """
        if command is None:
            out = ["Available commands:"]
            for name in sorted(self.commands):
                out.append(f"- {name}")
            out.append("\nType 'help <command>' for details.")
            content = "\n".join(out)
            return {"type": "help", "content": content}

        if command not in self.commands:
            content = f"No such command '{command}'"
            return {"type": "help", "content": content}

        cmd = self.commands[command]
        lines = [f"Help for command '{cmd.name}':"]
        for p in cmd.patterns:
            lines.append(f"- {p.pattern_str}")
        if cmd.func.__doc__:
            lines.append('\n' + cmd.func.__doc__.strip())
        content = "\n".join(lines)
        return {"type": "help", "content": content}

    def _cmd_exit(self, ctx):
        """Signals that the CLI session should exit.

        Args:
            ctx: The current context (unused).

        Returns:
            dict: A result dict with ``'type': 'exit'``.
        """
        return {"type": "exit"}

    def run_command(self, ctx, text: str):
        """Tokenizes and dispatches a text command to the matching handler.

        Iterates over all registered commands and returns the result of the first
        matching one. If no command matches, returns an unknown-command result dict.

        Args:
            ctx: The context object passed to the matched command handler.
            text (str): The raw command input string.

        Returns:
            dict: The result dict from the matched command handler, or
                ``{'type': 'unknown_command', 'text': ..., 'command': ...}``
                if no match is found.
        """
        tokens = tokenize(text)

        for cmd in self.commands.values():
            parsed = cmd.try_match(tokens)
            if parsed is not None:
                return cmd.call(ctx, parsed)

        return {"type": "unknown_command", "text": text, "command": tokens[0]}

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def push_history(self, command: str) -> None:
        """Append a non-empty command string to the in-memory history.

        Args:
            command: The raw command text. Empty strings are silently ignored.
        """
        if command:
            self.history.append(command)

    def get_history(self) -> list[str]:
        """Return a copy of the recorded command history.

        Returns:
            list[str]: Chronologically ordered list of non-empty commands.
        """
        return list(self.history)

    # ------------------------------------------------------------------
    # Readline / tab completion
    # ------------------------------------------------------------------

    def setup_readline(self, history_file: str | None = None) -> None:
        """Configure readline tab-completion and optional history persistence.

        Registers a completer that expands the current prefix to matching
        command names.  If ``history_file`` is provided and readable it will
        be loaded on first call and written out on :meth:`read_command` exit.
        Does nothing if readline is not available (e.g. on Windows).

        Args:
            history_file: Optional filesystem path to a readline history file.
        """
        if not _READLINE_AVAILABLE:
            return

        self._readline_history_file = history_file

        if history_file:
            try:
                _readline.read_history_file(history_file)
            except (OSError, FileNotFoundError):
                pass

        candidates: list[str] = []

        def completer(text: str, state: int) -> str | None:
            nonlocal candidates
            if state == 0:
                candidates = [
                    name for name in self.commands
                    if name.startswith(text)
                ]
            return candidates[state] if state < len(candidates) else None

        _readline.set_completer(completer)
        _readline.parse_and_bind("tab: complete")
        self._readline_setup = True

    def read_command(self, prompt: str = "") -> str:
        """Read a command from stdin with readline support.

        Sets up readline tab-completion on the first call (if available),
        records each non-empty input to :attr:`history`, and returns the
        stripped text.

        Args:
            prompt: The prompt string shown to the user.

        Returns:
            The stripped command string (may be empty).
        """
        if not self._readline_setup:
            self.setup_readline(
                getattr(self, "_readline_history_file", None)
            )
        text = input(prompt).strip()
        if text:
            self.push_history(text)
        return text


def main():
    class SampleGameContext:
        def hello(self):
            return "Hello from game!"

    def cmd_add(ctx, a: int, b: int):
        """
        Adds two integers together.
        Integers prefered.
        """
        return {"type": "numerical", "value": a + b}

    def cmd_hello(ctx, content: str):
        print(f"Hello: {content!r}")
        return {"type": "success"}

    # def cmd_say(ctx, content: str):
    #     print(content)
    #     return ctx.hello()

    engine = CLIEngine()
    engine.register(Command("add", cmd_add, ["add <a:int> <b:int>"]))
    engine.register(Command("hello", cmd_hello, ["hello [content:str]"]))
    # engine.register(Command("say", cmd_say, ["say <content:str>"]))

    @engine.add_command("say", ["say <content:str>"])
    def cmd_say(ctx, content: str):
        print(f"Saying: {content!r}")
        return {"type": "success"}

    res = engine.run_command(SampleGameContext(), "help")
    print(res)
    res = engine.run_command(SampleGameContext(), "help add")
    print(res)
    res = engine.run_command(SampleGameContext(), "add 5 7")
    print(res)
    res = engine.run_command(SampleGameContext(), "hello hi")
    print(res)
    res = engine.run_command(SampleGameContext(), "hello")
    print(res)
    res = engine.run_command(SampleGameContext(), 'say "hello \"world\""')
    print(res)

    # --- history ---
    print("\n--- History ---")
    engine.push_history("add 5 7")
    engine.push_history("hello hi")
    engine.push_history("help")
    for entry in engine.get_history():
        print(f"  {entry!r}")
    print(f"Total history entries: {len(engine.get_history())}")


if __name__ == "__main__":
    main()
