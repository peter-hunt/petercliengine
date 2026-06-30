"""Tests for CLIEngine — command dispatch, aliases, locking, repeat."""
import pytest
from cliengine import CLIEngine, ArgType, register_argtype, replace_argtype, ARG_TYPES, tokenize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class DummyCtx:
    """Minimal stand-in for a game context."""

    def __init__(self):
        self.calls = []


def make_engine() -> tuple[CLIEngine, DummyCtx]:
    eng = CLIEngine()
    ctx = DummyCtx()
    return eng, ctx


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_simple(self):
        assert tokenize("go north") == ["go", "north"]

    def test_quoted_single(self):
        assert tokenize("say 'hello world'") == ["say", "hello world"]

    def test_quoted_double(self):
        assert tokenize('say "hello world"') == ["say", "hello world"]

    def test_backslash_escape(self):
        assert tokenize(r"say he\"llo") == ["say", 'he"llo']

    def test_empty(self):
        assert tokenize("") == []

    def test_extra_spaces(self):
        assert tokenize("  go   north  ") == ["go", "north"]


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

class TestCommandDispatch:
    def test_known_command(self):
        eng, ctx = make_engine()
        results = []

        @eng.add_command("greet", ["greet <name:str>"])
        def greet(ctx, name):
            results.append(name)
            return {"type": "success"}

        api = eng.run_command(ctx, "greet Alice")
        assert api["type"] == "success"
        assert results == ["Alice"]

    def test_unknown_command(self):
        eng, ctx = make_engine()
        api = eng.run_command(ctx, "fly north")
        assert api["type"] == "unknown_command"
        assert api["command"] == "fly"

    def test_optional_arg_present(self):
        eng, ctx = make_engine()
        results = []

        @eng.add_command("jump", ["jump [height:int]"])
        def jump(ctx, height=1):
            results.append(height)
            return {"type": "success"}

        eng.run_command(ctx, "jump 3")
        assert results == [3]

    def test_optional_arg_absent(self):
        eng, ctx = make_engine()
        results = []

        @eng.add_command("jump", ["jump [height:int]"])
        def jump(ctx, height=None):
            results.append(height)
            return {"type": "success"}

        eng.run_command(ctx, "jump")
        # CLIEngine passes None for an absent optional arg
        assert results == [None]

    def test_exit_command(self):
        eng, ctx = make_engine()
        api = eng.run_command(ctx, "exit")
        assert api["type"] == "exit"

    def test_quit_alias_for_exit(self):
        eng, ctx = make_engine()
        api = eng.run_command(ctx, "quit")
        assert api["type"] == "exit"


# ---------------------------------------------------------------------------
# Aliases
# ---------------------------------------------------------------------------

class TestAliases:
    def test_alias_dispatches(self):
        eng, ctx = make_engine()
        results = []

        @eng.add_command("go", ["go <dir:str>"], aliases=["g", "move"])
        def go(ctx, dir):
            results.append(dir)
            return {"type": "success"}

        eng.run_command(ctx, "g north")
        assert results == ["north"]

    def test_all_aliases_work(self):
        eng, ctx = make_engine()
        results = []

        @eng.add_command("attack", ["attack <target:str>"], aliases=["a", "atk"])
        def attack(ctx, target):
            results.append(target)
            return {"type": "success"}

        eng.run_command(ctx, "a goblin")
        eng.run_command(ctx, "atk troll")
        assert results == ["goblin", "troll"]

    def test_duplicate_alias_raises(self):
        eng, ctx = make_engine()

        @eng.add_command("go", ["go <dir:str>"])
        def go(ctx, dir): return {"type": "success"}

        with pytest.raises(ValueError):
            @eng.add_command("run", ["run <dir:str>"], aliases=["go"])
            def run(ctx, dir): return {"type": "success"}


# ---------------------------------------------------------------------------
# Input locking
# ---------------------------------------------------------------------------

class TestInputLocking:
    def test_locked_buffers_commands(self):
        eng, ctx = make_engine()
        processed = []

        @eng.add_command("step", ["step"])
        def step(c):
            processed.append("step")
            return {"type": "success"}

        eng.lock_input()
        assert eng.input_locked
        api = eng.run_command(ctx, "step")
        assert api["type"] == "buffered"
        assert processed == []

        eng.unlock_input(ctx)
        assert not eng.input_locked
        assert processed == ["step"]

    def test_buffer_flushed_in_order(self):
        eng, ctx = make_engine()
        order = []

        @eng.add_command("cmd", ["cmd <n:int>"])
        def cmd(c, n):
            order.append(n)
            return {"type": "success"}

        eng.lock_input()
        eng.run_command(ctx, "cmd 1")
        eng.run_command(ctx, "cmd 2")
        eng.run_command(ctx, "cmd 3")
        eng.unlock_input(ctx)
        assert order == [1, 2, 3]


# ---------------------------------------------------------------------------
# Repeat / !!
# ---------------------------------------------------------------------------

class TestRepeat:
    def test_repeat_reruns_last(self):
        eng, ctx = make_engine()
        counts = [0]

        @eng.add_command("ping", ["ping"])
        def ping(c):
            counts[0] += 1
            return {"type": "success"}

        eng.run_command(ctx, "ping")
        eng.push_history("ping")
        api = eng.run_command(ctx, "repeat")
        assert counts[0] == 2

    def test_repeat_no_history(self):
        eng, ctx = make_engine()
        api = eng.run_command(ctx, "repeat")
        assert api["type"] == "failed"


# ---------------------------------------------------------------------------
# Custom ArgType registration
# ---------------------------------------------------------------------------

class TestArgTypeRegistration:
    def teardown_method(self):
        ARG_TYPES.pop("compass", None)

    def test_register_custom(self):
        at = ArgType("compass", r"north|south|east|west", lambda x: x)
        register_argtype(at)
        assert "compass" in ARG_TYPES

    def test_register_duplicate_raises(self):
        at = ArgType("compass", r"north|south|east|west", lambda x: x)
        register_argtype(at)
        with pytest.raises(ValueError):
            register_argtype(at)

    def test_replace_overwrites(self):
        at1 = ArgType("compass", r"north|south", lambda x: x)
        ARG_TYPES["compass"] = at1
        at2 = ArgType("compass", r"north|south|east|west", lambda x: x)
        replace_argtype(at2)
        assert ARG_TYPES["compass"] is at2


class TestPatternCoverage:
    def test_required_covered_by_optional(self):
        from cliengine import CommandPattern
        p1 = CommandPattern("cmd <x:int>")
        p2 = CommandPattern("cmd [x:int]")
        assert p1.is_covered_by(p2) is True
        assert p2.is_covered_by(p1) is False
