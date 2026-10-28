"""
Guards the bot's behaviour surface against accidental change.

Compares a fresh offline inventory (see tests/inventory.py) against the
committed snapshot in tests/snapshots/inventory.json. Any added, removed or
renamed command, alias, check, cooldown, help text, listener, loop or sqlite
schema fails this test.

If a change is intentional, regenerate the snapshot and commit it alongside:

    python tests/inventory.py --update
"""
import difflib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "snapshots" / "inventory.json"


def _current_inventory():
    # Separate process: the inventory changes cwd, patches sockets and hard-exits.
    result = subprocess.run(
        [sys.executable, str(HERE / "inventory.py")],
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, f"inventory failed:\n{result.stderr[-4000:]}"
    return result.stdout


def test_inventory_matches_snapshot():
    current = _current_inventory()
    expected = SNAPSHOT.read_text()
    if current != expected:
        diff = "".join(difflib.unified_diff(
            expected.splitlines(keepends=True), current.splitlines(keepends=True),
            "snapshot", "current", n=2))
        raise AssertionError(
            "Bot behaviour surface changed. If intentional, run "
            "`python tests/inventory.py --update` and commit the snapshot.\n\n"
            + diff[:8000])


def test_all_extensions_load():
    inventory = json.loads(_current_inventory())
    assert inventory["load_failures"] == []
    modules = sorted(p.stem for p in (HERE.parent / "modules").glob("*.py"))
    assert inventory["extensions"] == [f"modules.{m}" for m in modules]
