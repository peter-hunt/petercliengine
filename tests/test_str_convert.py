"""Tests for str_convert module."""
import pytest
from str_convert import (
    to_snake_case, to_camel_case, to_pascal_case,
    to_title_case, to_kebab_case,
)


class TestToSnakeCase:
    def test_camel(self):
        assert to_snake_case("camelCase") == "camel_case"

    def test_pascal(self):
        assert to_snake_case("PascalCase") == "pascal_case"

    def test_spaces(self):
        assert to_snake_case("hello world") == "hello_world"

    def test_kebab(self):
        assert to_snake_case("foo-bar") == "foo_bar"

    def test_already_snake(self):
        assert to_snake_case("already_snake") == "already_snake"

    def test_acronym(self):
        # Consecutive uppercase letters are kept as a group
        assert to_snake_case("HTTPRequest") == "http_request"

    def test_mixed(self):
        assert to_snake_case("some mixed_string") == "some_mixed_string"


class TestToCamelCase:
    def test_from_snake(self):
        assert to_camel_case("hello_world") == "helloWorld"

    def test_already_camel(self):
        assert to_camel_case("helloWorld") == "helloWorld"

    def test_single_word(self):
        assert to_camel_case("hello") == "hello"


class TestToPascalCase:
    def test_from_snake(self):
        assert to_pascal_case("hello_world") == "HelloWorld"

    def test_single_word(self):
        assert to_pascal_case("hello") == "Hello"

    def test_from_camel(self):
        # camelCase -> snake (camel_case) -> pascal (CamelCase)
        assert to_pascal_case("camelCase") == "CamelCase"


class TestToTitleCase:
    def test_from_snake(self):
        assert to_title_case("hello_world") == "Hello World"

    def test_single_word(self):
        assert to_title_case("hello") == "Hello"


class TestToKebabCase:
    def test_from_snake(self):
        assert to_kebab_case("hello_world") == "hello-world"

    def test_from_camel(self):
        assert to_kebab_case("camelCase") == "camel-case"

    def test_single_word(self):
        assert to_kebab_case("hello") == "hello"
