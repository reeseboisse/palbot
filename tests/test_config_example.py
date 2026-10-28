"""
config/config.py.example must document exactly the config keys the code reads.
"""
import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# self.bot.config.x, bot.config.x, ctx.bot.config.x, and palbot.py's config.x
KEY_RE = re.compile(r"\bbot\.config\.([A-Za-z_]\w*)|^\s*super\(\)\.run\(config\.(\w+)", re.M)


def _keys_used():
    sources = [REPO / "palbot.py", *REPO.glob("modules/**/*.py"), *REPO.glob("utils/**/*.py")]
    used = set()
    for path in sources:
        for m in KEY_RE.finditer(path.read_text()):
            used.add(m.group(1) or m.group(2))
    return used


def _keys_documented():
    tree = ast.parse((REPO / "config" / "config.py.example").read_text())
    return {t.id for node in tree.body if isinstance(node, ast.Assign)
            for t in node.targets if isinstance(t, ast.Name)}


def test_every_used_key_is_documented():
    assert _keys_used() - _keys_documented() == set()


def test_every_documented_key_is_used():
    assert _keys_documented() - _keys_used() == set()
