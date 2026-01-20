from re import Match, compile as re_compile, VERBOSE
from typing import Callable


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
    v = v.lower()
    if v in TRUE_LITERALS:
        return True
    elif v in FALSE_LITERALS:
        return False
    else:
        raise ValueError(f"Invalid boolean literal: {v}")


class ArgType:
    def __init__(self, name: str, pattern: str, converter: Callable[[str], any]):
        self.name = name
        self.pattern = re_compile(pattern)
        self.converter = converter

    def is_valid(self, value: str) -> bool:
        return bool(self.pattern.fullmatch(value))

    def convert(self, value: str):
        return self.converter(value)


ARG_TYPES: dict[str, ArgType] = {
    "int": ArgType("int", r"[+-]?\d+", int),
    "num": ArgType("num", r"[+-]?(\d*\.?\d+|\d+\.?\d*)", float),
    "bool": ArgType("bool", rf"(?i:{'|'.join(BOOL_LITERALS)})", bool_convert),
    "str": ArgType("str", r".+", lambda x: x),
}


def parse_argtype(name: str, type_name: str | None, /):
    if type_name is None:
        return ARG_TYPES["str"]

    if type_name not in ARG_TYPES:
        raise ValueError(f"Unknown type {type_name!r} "
                         f"in argument {name}:{type_name}")
    return ARG_TYPES[type_name]


class Arg:
    def __init__(self, kind: str, name: str, type_obj: ArgType | None = None, is_optional: bool = False):
        self.kind = kind
        self.name = name
        self.type = type_obj or ARG_TYPES["str"]
        self.is_optional = is_optional


def parse_command(s: str) -> list[Arg]:
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
    """
    Parses and match a command pattern from incoming texts.
    Example pattern definition usage:
        get coord <player>
        set speed <speed:float> [<sprint:bool>]
    """

    pattern_str: str
    parts: list[Arg]

    def __init__(self, pattern_str: str):
        self.pattern_str = pattern_str
        self.parts = parse_command(pattern_str)

    def match(self, tokens: list[str]) -> dict[str: any] | None:
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
        """
        Determine if instance is fully overshadowed by given pattern,
        i.e., that if the given pattern is matched for first, the self
        instance will never match.

        :param self: The instance.
        :param pattern: The pattern to check overshadowing with.
        :type pattern: CommandPattern
        :return: Whether if the instance is fully overshadowed.
        :rtype: bool

        :raises ValueError: If the argument kind is unrecognized.
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
    def __init__(self, name: str, func: Callable, patterns: list[str]):
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
        for p in self.patterns:
            parsed = p.match(tokens)
            if parsed is not None:
                return parsed
        return

    def call(self, ctx, parsed_args: dict):
        return self.func(ctx, **parsed_args)


def tokenize(s: str) -> list[str]:
    """Supporting strings as the same token along with keywords and numbers."""
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
    def __init__(self):
        self.commands: dict[str, Command] = {}
        self._register_builtin_commands()

    def register(self, cmd: Command):
        if cmd.name in self.commands:
            raise ValueError(f"Duplicate command name '{cmd.name}'")
        self.commands[cmd.name] = cmd

    def add_command(self, name: str, patterns: list[str]) -> Callable:
        def wrapper(func: Callable):
            self.register(Command(name, func, patterns))
            return func
        return wrapper

    def _register_builtin_commands(self):
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
        """
        List the available commands or show help for command if specified.
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
        """
        Exit the current process.
        """
        return {"type": "exit"}

    def run_command(self, ctx, text: str):
        tokens = tokenize(text)

        for cmd in self.commands.values():
            parsed = cmd.try_match(tokens)
            if parsed is not None:
                return cmd.call(ctx, parsed)

        return {"type": "unknown_command", "text": text, "command": tokens[0]}


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


if __name__ == "__main__":
    main()
