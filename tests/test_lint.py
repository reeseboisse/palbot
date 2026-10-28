"""
pyflakes must stay clean: it catches undefined names, duplicate dict keys
and similar real bugs (two were found this way), not just style.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_pyflakes_clean():
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", "palbot.py", "modules", "utils", "tests"],
        cwd=REPO, capture_output=True, text=True)
    problems = [
        line for line in result.stdout.splitlines()
        # utils/__init__.py re-exports these for cogs to use as bot.utils.X
        if not (line.startswith("utils/__init__.py:") and "imported but unused" in line)
    ]
    assert problems == [], "\n".join(problems)
