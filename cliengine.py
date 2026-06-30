from re import Match, compile as re_compile, VERBOSE
from typing import Any, Callable, cast

_readline: Any = None
_READLINE_AVAILABLE: bool = False
try:
    import readline as _readline
    _READLINE_AVAILABLE = True
except ImportError:
    pass


__all__ = [
    "bool_convert",
    "ArgType", "ARG_TYPES", "parse_argtype",
    "register_argtype", "replace_argtype",
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

    def convert(self, value: str) -> Any:
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


def register_argtype(argtype: ArgType, /) -> None:
    """Register a custom :class:`ArgType` in the global ``ARG_TYPES`` registry.

    After registration the type is available by name in all command pattern
    strings (e.g. ``"go <direction:compass>"``).

    Args:
        argtype: The :class:`ArgType` instance to register.

    Raises:
        ValueError: If a type with the same name is already registered.
    """
    if argtype.name in ARG_TYPES:
        raise ValueError(
            f"ArgType {argtype.name!r} is already registered. "
            f"Use replace_argtype() to replace an existing type.")
    ARG_TYPES[argtype.name] = argtype


def replace_argtype(argtype: ArgType, /) -> None:
    """Replace or add a custom :class:`ArgType` in the global ``ARG_TYPES`` registry.

    Unlike :func:`register_argtype`, this silently overwrites an existing entry.

    Args:
        argtype: The :class:`ArgType` instance to register or replace.
    """
    ARG_TYPES[argtype.name] = argtype


def parse_argtype(name: str, type_name: str | None, /) -> ArgType:
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

    def match(self, tokens: list[str]) -> dict[str, Any] | None:
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
                    return None
                idx += 1
            elif arg.kind == "var" and not arg.is_optional:
                if idx >= len(tokens) or not arg.type.is_valid(tokens[idx]):
                    return None
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
            return None
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
                    if sarg.type != parg.type and parg.type.name != "str":
                        return False
                    if sarg.is_optional and not parg.is_optional:
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
        aliases (list[str]): Short names / abbreviations that also trigger this command.
        func (Callable): The handler function called when the command matches.
        patterns (list[CommandPattern]): The parsed command patterns.
        value_completer (Callable[[str, str], list[str]] | None): Optional callback
            invoked during readline tab-completion to provide argument value
            suggestions.  Called as ``value_completer(arg_name, partial_text)``
            and should return a list of candidate strings.
    """

    def __init__(self, name: str, func: Callable[..., Any], patterns: list[str],
                 aliases: list[str] | None = None,
                 value_completer: Callable[[str, str], list[str]] | None = None):
        """Initializes a Command and optionally checks for pattern coverage.

        Args:
            name (str): The name of the command.
            func (Callable): The function to call when the command matches, with
                signature ``func(ctx, **parsed_args)``.
            patterns (list[str]): A list of pattern strings to register for this
                command.
            aliases (list[str] | None): Optional short names / abbreviations that
                also dispatch to this command.
            value_completer (Callable[[str, str], list[str]] | None): Optional
                callback ``(arg_name, partial_text) -> [candidate, ...]`` used to
                complete argument values during readline Tab expansion.
        """
        self.name = name
        self.aliases = list(aliases) if aliases else []
        self.value_completer = value_completer
        self.func = func
        self.patterns = [CommandPattern(p) for p in patterns]
        if CHECK_PATTERN_COVERAGE:
            for i, patt in enumerate(self.patterns[1:], 1):
                for j, other in enumerate(self.patterns[:i]):
                    if patt.is_covered_by(other):
                        print(f"Warning: pattern {j + 1} fully covers"
                              f" pattern {i + 1} (command {self.name!r})")

    def try_match(self, tokens: list[str]) -> dict[str, Any] | None:
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
        return None

    def call(self, ctx: Any, parsed_args: dict[str, Any]) -> Any:
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

    def __init__(self) -> None:
        """Initializes the CLIEngine and registers the built-in commands."""
        self.commands: dict[str, Command] = {}
        self.history: list[str] = []
        self._readline_setup: bool = False
        self._input_locked: bool = False
        self._input_buffer: list[str] = []
        self._register_builtin_commands()

    def register(self, cmd: Command) -> None:
        """Registers a Command object with the engine.

        Also registers every alias listed in ``cmd.aliases`` as additional
        lookup keys pointing to the same Command object.

        Args:
            cmd (Command): The command to register.

        Raises:
            ValueError: If a command with the same name (or any alias) is
                already registered.
        """
        if cmd.name in self.commands:
            raise ValueError(f"Duplicate command name '{cmd.name}'")
        for alias in cmd.aliases:
            if alias in self.commands:
                raise ValueError(
                    f"Alias '{alias}' conflicts with existing command")
        self.commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self.commands[alias] = cmd
        # invalidate cached completions whenever commands change
        self._readline_setup = False

    def add_command(self, name: str, patterns: list[str],
                    aliases: list[str] | None = None,
                    value_completer: Callable[[str, str], list[str]] | None = None) -> Callable[..., Any]:
        """Returns a decorator that registers the decorated function as a command.

        Args:
            name (str): The name of the command to register.
            patterns (list[str]): The list of pattern strings for the command.
            aliases (list[str] | None): Optional short names that also dispatch
                to this command.
            value_completer (Callable[[str, str], list[str]] | None): Optional
                callback ``(arg_name, partial_text) -> [candidate, ...]`` used
                during readline Tab completion to suggest argument values.

        Returns:
            Callable: A decorator that wraps the function in a ``Command``,
                registers it, and returns the original function unchanged.
        """
        def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
            self.register(Command(name, func, patterns, aliases=aliases,
                                  value_completer=value_completer))
            return func
        return wrapper

    def _register_builtin_commands(self) -> None:
        """Registers the built-in ``help``, ``exit``, and ``repeat`` commands."""
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

        self.register(Command(
            name="repeat",
            func=self._cmd_repeat,
            patterns=["repeat", "!!"]
        ))

    def _cmd_help(self, ctx: Any, command: str | None = None) -> dict[str, Any]:
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
            seen = set()
            for name in sorted(self.commands):
                cmd = self.commands[name]
                if cmd.name in seen:
                    continue
                seen.add(cmd.name)
                alias_str = f"  (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                out.append(f"- {cmd.name}{alias_str}")
            out.append("\nType 'help <command>' for details.")
            content = "\n".join(out)
            return {"type": "help", "content": content}

        if command not in self.commands:
            content = f"No such command '{command}'"
            return {"type": "help", "content": content}

        cmd = self.commands[command]
        lines = [f"Help for command '{cmd.name}':"]
        if cmd.aliases:
            lines.append(f"Aliases: {', '.join(cmd.aliases)}")
        for p in cmd.patterns:
            lines.append(f"- {p.pattern_str}")
        if cmd.func.__doc__:
            lines.append('\n' + cmd.func.__doc__.strip())
        content = "\n".join(lines)
        return {"type": "help", "content": content}

    def _cmd_exit(self, ctx: Any) -> dict[str, Any]:
        """Signals that the CLI session should exit.

        Args:
            ctx: The current context (unused).

        Returns:
            dict: A result dict with ``'type': 'exit'``.
        """
        return {"type": "exit"}

    def _cmd_repeat(self, ctx: Any) -> dict[str, Any]:
        """Re-runs the most-recently submitted history entry.

        Looks up the last entry in :attr:`history`, dispatches it as a new
        command, and returns the result.  If history is empty, returns a
        failure result.

        Args:
            ctx: The context object forwarded to the repeated command.

        Returns:
            dict: The result of running the previous command, or
                ``{'type': 'failed'}`` when there is no history.
        """
        if not self.history:
            print("No previous command in history.")
            return {"type": "failed"}
        last = self.history[-1]
        # Guard against infinite recursion if last command was itself !! / repeat
        tokens = tokenize(last)
        if tokens and tokens[0] in ("!!", "repeat"):
            print("Cannot repeat a repeat command.")
            return {"type": "failed"}
        return self.run_command(ctx, last)

    def run_command(self, ctx: Any, text: str) -> dict[str, Any]:
        """Tokenizes and dispatches a text command to the matching handler.

        When the engine is locked (see :meth:`lock_input`), the command is
        added to the internal buffer and ``{'type': 'buffered'}`` is returned
        without dispatching.

        Iterates over all registered commands and returns the result of the first
        matching one.  When the first token matches a command alias, it is
        substituted with the canonical command name before pattern matching so
        that alias users see identical behaviour to the canonical name.

        If no command matches, returns an unknown-command result dict.

        Args:
            ctx: The context object passed to the matched command handler.
            text (str): The raw command input string.

        Returns:
            dict: The result dict from the matched command handler, or
                ``{'type': 'unknown_command', 'text': ..., 'command': ...}``
                if no match is found, or ``{'type': 'buffered'}`` when locked.
        """
        if self._input_locked:
            self._input_buffer.append(text)
            return {"type": "buffered"}

        tokens = tokenize(text)

        first = tokens[0] if tokens else ""
        if first in self.commands:
            cmd = self.commands[first]
            # If dispatched via alias, replace first token with canonical name
            if first != cmd.name:
                tokens = [cmd.name] + tokens[1:]
            parsed = cmd.try_match(tokens)
            if parsed is not None:
                return cast(dict[str, Any], cmd.call(ctx, parsed))

        for cmd in self.commands.values():
            parsed = cmd.try_match(tokens)
            if parsed is not None:
                return cast(dict[str, Any], cmd.call(ctx, parsed))

        return {"type": "unknown_command", "text": text, "command": first}

    # ------------------------------------------------------------------
    # Input locking (narrations / dialogues)
    # ------------------------------------------------------------------

    def lock_input(self) -> None:
        """Block command processing; commands entered while locked are buffered.

        While the engine is locked :meth:`run_command` queues any input in an
        internal buffer instead of dispatching it immediately.  Call
        :meth:`unlock_input` to release the lock and flush the buffer.
        """
        self._input_locked = True

    def unlock_input(self, ctx: Any = None) -> None:
        """Release the input lock and flush any buffered commands.

        Each buffered command is dispatched in order via :meth:`run_command`.
        The results are silently discarded unless the caller wraps this
        method or inspects :attr:`history`.

        Args:
            ctx: The context object forwarded to each replayed command.
        """
        self._input_locked = False
        pending = self._input_buffer[:]
        self._input_buffer.clear()
        for cmd_text in pending:
            self.run_command(ctx, cmd_text)

    @property
    def input_locked(self) -> bool:
        """True when command processing is currently locked."""
        return self._input_locked

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
                try:
                    import readline as _rl
                    line = _rl.get_line_buffer()
                except Exception:
                    line = text
                tokens = tokenize(line) if line.strip() else []
                # If the line ends with a space, the current word is empty and
                # we're starting a new token; otherwise the last token is partial.
                ends_with_space = line.endswith(' ')
                completed_tokens = tokens if ends_with_space else tokens[:-1]

                if not completed_tokens:
                    # completing the command name (or alias)
                    candidates = [
                        name for name in self.commands
                        if name.startswith(text)
                    ]
                else:
                    cmd_word = completed_tokens[0]
                    cmd = self.commands.get(cmd_word)
                    if cmd is None:
                        candidates = []
                    elif cmd.value_completer is not None:
                        # Determine which argument we're completing by walking
                        # through the best-matching pattern.
                        arg_name = None
                        # +1 because completed_tokens includes the command word
                        arg_index = len(completed_tokens) - \
                            1  # 0-based variable index
                        var_args = [a for p in cmd.patterns
                                    for a in p.parts if a.kind == "var"]
                        # deduplicate while preserving first occurrence
                        seen_names: set[str] = set()
                        unique_vars = []
                        for a in var_args:
                            if a.name not in seen_names:
                                seen_names.add(a.name)
                                unique_vars.append(a)
                        if arg_index < len(unique_vars):
                            arg_name = unique_vars[arg_index].name
                        if arg_name:
                            candidates = [
                                c for c in cmd.value_completer(arg_name, text)
                                if c.startswith(text)
                            ]
                        else:
                            candidates = []
                    else:
                        candidates = []
            return candidates[state] if state < len(candidates) else None

        _readline.set_completer(completer)
        _readline.parse_and_bind("tab: complete")
        self._readline_setup = True

    def read_command(self, prompt: str = "") -> str:
        """Read a command from stdin with readline support.

        Sets up readline tab-completion on the first call (if available),
        records each non-empty input to :attr:`history`, and returns the
        stripped text.  When a history file was configured via
        :meth:`setup_readline`, it is written out after each non-empty command.

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
            history_file = getattr(self, "_readline_history_file", None)
            if _READLINE_AVAILABLE and history_file:
                try:
                    _readline.write_history_file(history_file)
                except OSError:
                    pass
        return text


def main() -> None:
    class SampleGameContext:
        def hello(self) -> str:
            return "Hello from game!"

    def cmd_add(ctx: Any, a: int, b: int) -> dict[str, Any]:
        """
        Adds two integers together.
        Integers prefered.
        """
        return {"type": "numerical", "value": a + b}

    def cmd_hello(ctx: Any, content: str) -> dict[str, Any]:
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
    def cmd_say(ctx: Any, content: str) -> dict[str, Any]:
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
