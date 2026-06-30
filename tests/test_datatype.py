"""Tests for the DataType and Variable base classes."""
import io
import pytest
from datatype import DataType, Variable


class Point(DataType):
    variables = [
        Variable("x", int),
        Variable("y", int),
        Variable("label", str, default="unnamed"),
    ]


class TestVariableDefaults:
    def test_required_has_no_default(self):
        v = Variable("x", int)
        assert not v.optional

    def test_default_makes_optional(self):
        v = Variable("x", int, default=0)
        assert v.optional
        assert v.default_value == 0

    def test_default_factory(self):
        v = Variable("items", list, default_factory=list)
        assert v.optional
        a = v.default_value
        b = v.default_value
        assert a == []
        assert a is not b  # fresh list each time

    def test_both_default_and_factory_raises(self):
        with pytest.raises(ValueError):
            Variable("x", int, default=1, default_factory=lambda: 1)

    def test_reserved_name_raises(self):
        with pytest.raises(NameError):
            Variable("type", str)

    def test_mutable_default_raises(self):
        with pytest.raises(ValueError):
            class Bad(DataType):
                variables = [Variable("items", list, default=[])]

    def test_invalid_default_type_raises(self):
        with pytest.raises(TypeError):
            Variable("age", int, default="ten")

    def test_invalid_default_factory_type_raises(self):
        with pytest.raises(TypeError):
            Variable("items", list[int], default_factory=lambda: ["not_int"])

    def test_default_fails_validator_raises(self):
        with pytest.raises(ValueError):
            Variable("score", int, default=150, validator=lambda x: x < 100)

    def test_default_factory_fails_validator_raises(self):
        with pytest.raises(ValueError):
            Variable("score", int, default_factory=lambda: 150, validator=lambda x: x < 100)


class TestDataTypeInit:
    def test_positional_args(self):
        p = Point(1, 2)
        assert p.x == 1
        assert p.y == 2
        assert p.label == "unnamed"

    def test_keyword_args(self):
        p = Point(x=3, y=4, label="origin")
        assert p.label == "origin"

    def test_wrong_type_raises(self):
        with pytest.raises(TypeError):
            Point("not_int", 2)

    def test_missing_required_raises(self):
        with pytest.raises(TypeError):
            Point(1)

    def test_extra_args_raises(self):
        with pytest.raises(TypeError):
            Point(1, 2, "label", "extra")

    def test_unexpected_kwarg_raises(self):
        with pytest.raises(TypeError):
            Point(x=1, y=2, unknown=99)


class TestDataTypeSerialisation:
    def test_dumps_includes_type_tag(self):
        p = Point(10, 20)
        d = p.dumps()
        assert d["type"] == "point"
        assert d["x"] == 10
        assert d["y"] == 20

    def test_dumps_omits_unchanged_defaults(self):
        p = Point(1, 2)
        d = p.dumps()
        assert "label" not in d

    def test_dumps_includes_changed_default(self):
        p = Point(1, 2, label="A")
        d = p.dumps()
        assert d["label"] == "A"

    def test_loads_roundtrip(self):
        p = Point(5, 6, "test")
        buf = io.StringIO()
        p.dump(buf)
        buf.seek(0)
        p2 = Point.load(buf)
        assert p2.x == 5
        assert p2.y == 6
        assert p2.label == "test"

    def test_loads_wrong_type_tag_raises(self):
        with pytest.raises(TypeError):
            Point.loads({"type": "wrong_type", "x": 1, "y": 2})

    def test_loads_missing_type_tag_raises(self):
        with pytest.raises(TypeError):
            Point.loads({"x": 1, "y": 2})
