"""
config/config.py.example must document exactly the config keys the code reads.
"""
import ast
import re
from pathlib import Path

import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
# self.bot.config.x, bot.config.x, ctx.bot.config.x, palbot.py's config.x,
# and optional settings read through utils.settings.setting(bot, "x")
KEY_RE = re.compile(
    r"\bbot\.config\.([A-Za-z_]\w*)"
    r"|^\s*super\(\)\.run\(config\.(\w+)"
    r"|\bsetting\([\w.]+,\s*[\"'](\w+)[\"']\)", re.M)


def _keys_used():
    sources = [REPO / "palbot.py", *REPO.glob("modules/**/*.py"), *REPO.glob("utils/**/*.py")]
    used = set()
    for path in sources:
        for m in KEY_RE.finditer(path.read_text()):
            used.add(m.group(1) or m.group(2) or m.group(3))
    return used


def _example_assignments():
    tree = ast.parse((REPO / "config" / "config.py.example").read_text())
    return {t.id: node.value for node in tree.body if isinstance(node, ast.Assign)
            for t in node.targets if isinstance(t, ast.Name)}


def _keys_documented():
    return set(_example_assignments())


def test_every_used_key_is_documented():
    assert _keys_used() - _keys_documented() == set()


def test_every_documented_key_is_used():
    assert _keys_documented() - _keys_used() == set()


def test_optional_settings_documented_with_their_defaults():
    from utils.settings import DEFAULTS
    example = _example_assignments()
    for name, default in DEFAULTS.items():
        assert ast.literal_eval(example[name]) == default, name
