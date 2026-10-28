"""
The weather condition -> emoji map used by !w, !pw, !yr and !wemojitest.
"""
import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.weather import WEMOJI  # noqa: E402

SOURCE = Path(__file__).resolve().parent.parent / "modules" / "weather.py"


def test_no_duplicate_keys():
    # A repeated key in a dict literal silently discards the earlier entry.
    tree = ast.parse(SOURCE.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and getattr(n.targets[0], "id", "") == "WEMOJI")
    keys = [k.value for k in node.value.keys]
    assert len(keys) == len(set(keys))


def test_heavy_rain_and_thunder_emoji():
    assert WEMOJI["heavyrainandthunder"] == "⛈️⛈️"
    assert WEMOJI["heavyrainshowersandthunder_day"] == "⛈️⛈️"
    assert WEMOJI["heavyrainshowersandthunder_night"] == "⛈️⛈️🌙"
