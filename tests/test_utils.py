"""Tests for utils module."""
import pytest
from utils import istype


class TestIstype:
    def test_any(self):
        from typing import Any
        assert istype(42, Any)
        assert istype("x", Any)

    def test_none(self):
        assert istype(None, None)
        assert not istype(0, None)

    def test_plain_type(self):
        assert istype(42, int)
        assert not istype("x", int)

    def test_tuple_of_types(self):
        assert istype(42, (int, str))
        assert istype("x", (int, str))
        assert not istype(3.14, (int, str))

    def test_union(self):
        assert istype(42, int | str)
        assert istype("x", int | str)
        assert not istype([], int | str)

    def test_list_generic(self):
        assert istype([1, 2, 3], list[int])
        assert not istype([1, "x"], list[int])
        assert istype([], list[int])

    def test_dict_generic(self):
        assert istype({"a": 1}, dict[str, int])
        assert not istype({1: 1}, dict[str, int])
        assert not istype({"a": "v"}, dict[str, int])

    def test_nested_generic(self):
        assert istype([[1, 2], [3]], list[list[int]])
        assert not istype([[1, "x"]], list[list[int]])
