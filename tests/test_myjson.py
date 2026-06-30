"""Tests for the custom JSON library myjson."""
import json
import myjson


def test_simple_types():
    assert myjson.dumps(None) == "null"
    assert myjson.dumps(True) == "true"
    assert myjson.dumps(False) == "false"
    assert myjson.dumps(123) == "123"
    assert myjson.dumps(12.34) == "12.34"


def test_string_escaping_special_chars():
    # Double quote and backslash
    assert myjson.dumps('he"llo') == '"he\\"llo"'
    assert myjson.dumps('he\\llo') == '"he\\\\llo"'

    # Common control characters
    assert myjson.dumps('a\nb') == '"a\\nb"'
    assert myjson.dumps('a\tb') == '"a\\tb"'
    assert myjson.dumps('a\rb') == '"a\\rb"'
    assert myjson.dumps('a\bb') == '"a\\bb"'
    assert myjson.dumps('a\fb') == '"a\\fb"'

    # Other control characters (e.g. vertical tab)
    assert myjson.dumps('a\vb') == '"a\\u000bb"'


def test_standard_roundtrip_compatibility():
    # Verify that python's json.loads can parse the myjson.dumps output
    test_str = 'Quote: ", Backslash: \\, Newline: \n, Tab: \t, Control: \x0e'
    encoded = myjson.dumps(test_str)
    
    # Assert that no literal single quotes were added around character escapes
    assert "'" not in encoded

    decoded = json.loads(encoded)
    assert decoded == test_str
