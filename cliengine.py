from re import compile as re_compile, VERBOSE
from typing import Callable


__all__ = [
    "bool_convert",
    "ArgType", "ARG_TYPES", "parse_argtype",
    "Arg",

    "CommandPattern", "Command",
    "tokenize",
    "CLIEngine",
]


def bool_convert(v: str, /) -> bool:
    v = v.lower()
    if v in ("1", "true", "yes", "y", "t"):
        return True
    if v in ("0", "false", "no", "n", "f"):
        return False
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
    "bool": ArgType("bool", r"(?i:true|false|yes|no|y|n|t|f)", bool_convert),
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
        self.type = type_obj
        self.is_optional = is_optional


class CommandPattern:
    """
    Parses and match a command pattern from incoming texts.
    Example pattern definition usage:
        get coord <player>
        set speed <speed:float> [<sprint:bool>]
    """

    token_re = re_compile(
        r"""
        <(?P<reqname>[a-zA-Z_]\w*)(:(?P<reqtype>[a-zA-Z_]\w*))?>
        |
        \[(?P<optname>[a-zA-Z_]\w*)(:(?P<opttype>[a-zA-Z_]\w*))?\]
        |
        (?P<lit>[^\s]+)
        """,
        VERBOSE,
    )

    def __init__(self, pattern_str: str):
        self.pattern_str = pattern_str
        self.parts = self._parse(pattern_str)

    def _parse(self, s: str):
        parts = []
        arg_names = {*()}
        saw_variable = False
        saw_optional = False

        for m in CommandPattern.token_re.finditer(s):
            if m.group("lit"):
                if saw_variable or saw_optional:
                    raise ValueError("Keyword arg found after variable arg.")
                parts.append(Arg("lit", m.group("lit")))
                continue

            if m.group("reqname"):
                if saw_optional:
                    raise ValueError("Required arg found after optional arg.")

                saw_variable = True
                name = m.group("reqname")
                type_obj = parse_argtype(name, m.group("reqtype"))

                if name in arg_names:
                    raise ValueError(f"Duplicate argument name: {name}")

                arg_names.add(name)
                parts.append(Arg("var", name, type_obj, False))
                continue

            saw_variable = True
            saw_optional = True
            name = m.group("optname")
            type_obj = parse_argtype(name, m.group("opttype"))

            if name in arg_names:
                raise ValueError(f"Duplicate argument name: {name}")

            arg_names.add(name)
            parts.append(Arg("var", name, type_obj, True))

        return parts

    def match(self, tokens: list[str]):
        idx = 0
        parsed = {}

        for arg in self.parts:
            if arg.kind == "lit":
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

        if idx != len(tokens):
            return None
        return parsed


class Command:
    def __init__(self, name: str, func: Callable, patterns: list[str]):
        self.name = name
        self.func = func
        self.patterns = [CommandPattern(p) for p in patterns]

    def try_match(self, tokens: list[str]):
        for p in self.patterns:
            parsed = p.match(tokens)
            if parsed is not None:
                return parsed
        return None

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

    def register(self, cmd: Command, /):
        if cmd.name in self.commands:
            raise ValueError(f"Duplicate command name '{cmd.name}'")
        self.commands[cmd.name] = cmd

    def _register_builtin_commands(self):
        self.register(Command(
            name="help",
            func=self._cmd_help,
            patterns=[
                "help",
                "help <command:str>"
            ]
        ))

        self.register(Command(
            name="exit",
            func=self._cmd_exit,
            patterns=["exit", "quit"]
        ))

    def _cmd_help(self, ctx, command=None, /):
        if command is None:
            out = ["Available commands:"]
            for name in sorted(self.commands):
                out.append(f"  {name}")
            out.append("Type 'help <command>' for details.")
            content = "\n".join(out)
            return {"type": "help", "content": content}

        if command not in self.commands:
            content = f"No such command '{command}'"
            return {"type": "help", "content": content}

        cmd = self.commands[command]
        lines = [f"Help for '{cmd.name}':"]
        for p in cmd.patterns:
            lines.append(f"  {p.pattern_str}")
        content = "\n".join(lines)
        return {"type": "help", "content": content}

    def _cmd_exit(self, ctx):
        return {"type": "exit"}

    def run_command(self, ctx, text: str):
        tokens = tokenize(text)

        for cmd in self.commands.values():
            parsed = cmd.try_match(tokens)
            if parsed is not None:
                return cmd.call(ctx, parsed)

        return {"type": "unknown_command", "text": text}


def main():
    class GameContext:
        def hello(self):
            return "Hello from game!"

    def cmd_hello(ctx):
        return ctx.hello()

    def cmd_say(ctx, content):
        return ctx.hello()

    def cmd_add(ctx, a: int, b: int):
        return a + b

    engine = CLIEngine()
    engine.register(Command("add", cmd_add, ["add <a:int> <b:int>"]))
    engine.register(Command("hello", cmd_hello, ["hello"]))
    engine.register(Command("say", cmd_say, ["say <content:str>"]))

    res = engine.run_command(GameContext(), "help")
    print(res)
    res = engine.run_command(GameContext(), "help add")
    print(res)
    res = engine.run_command(GameContext(), "add 5 7")
    print(res)
    res = engine.run_command(GameContext(), "hello")
    print(res)
    res = engine.run_command(GameContext(), 'say "hello \"world\""')
    print(res)


if __name__ == "__main__":
    main()
