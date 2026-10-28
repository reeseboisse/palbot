#!/usr/bin/env python3
"""
Offline inventory of the bot's behaviour surface.

Boots PalBot from palbot.py, loads every cog from modules/,
and records everything a user or operator can observe without a live
Discord connection: prefix commands (names, aliases, signatures, help text,
checks, cooldowns), app commands, listeners, background loops, and the
sqlite schemas the cogs create on load.

Runs in a throwaway directory with a stub config and all network access
blocked, so it never touches real data or external services.

    python tests/inventory.py              # print the inventory as JSON
    python tests/inventory.py --update     # rewrite tests/snapshots/inventory.json
"""
import asyncio
import contextlib
import inspect
import json
import os
import socket
import sqlite3
import sys
import tempfile
from pathlib import Path

import discord

REPO = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO / "tests" / "snapshots" / "inventory.json"

STUB_CONFIG = '''
token = "stub"
twitter_subscriptions = {}
gemini_keys = ["stub"]
wotd_whitelist = []
github_copilot_token_path = "data/github-copilot.token.json"
github_copilot_auth_profile_path = "config/auth-profiles.json"

def __getattr__(name):
    return "stub"
'''


# data/clues.db comes from the jeopardy-parser project, not from the bot, so it
# is seeded here with just the tables trivia queries and left out of the snapshot.
EXTERNAL_DB = "clues.db"
CLUES_SCHEMA = """
CREATE TABLE clues (id INTEGER PRIMARY KEY, game INTEGER, round INTEGER, value INTEGER);
CREATE TABLE airdates (game INTEGER PRIMARY KEY, airdate TEXT);
CREATE TABLE documents (id INTEGER PRIMARY KEY, clue TEXT, answer TEXT, links TEXT);
CREATE TABLE categories (id INTEGER PRIMARY KEY, category TEXT);
CREATE TABLE classifications (clue_id INTEGER, category_id INTEGER);
"""


class NetworkDisabled(RuntimeError):
    pass


def _block_network():
    def deny(*args, **kwargs):
        raise NetworkDisabled("network access is disabled during inventory")
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    socket.getaddrinfo = deny
    socket.create_connection = deny


class _StubSession:
    """Stands in for the bot's aiohttp ClientSession; every request fails."""
    closed = False

    def __init__(self, *args, **kwargs):
        pass

    def _deny(self, *args, **kwargs):
        raise NetworkDisabled("network access is disabled during inventory")

    get = post = put = patch = delete = head = request = ws_connect = _deny

    async def close(self):
        self.closed = True


def _make_sandbox():
    tmp = Path(tempfile.mkdtemp(prefix="palbot-inventory-"))
    for name in ("modules", "utils"):
        (tmp / name).symlink_to(REPO / name, target_is_directory=True)
    for name in ("data", "logfiles", "config"):
        (tmp / name).mkdir()
    (tmp / "config" / "__init__.py").write_text("")
    (tmp / "config" / "config.py").write_text(STUB_CONFIG)
    # Trivia reads a prebuilt j-archive database it never creates itself.
    conn = sqlite3.connect(tmp / "data" / EXTERNAL_DB)
    conn.executescript(CLUES_SCHEMA)
    conn.close()
    return tmp


def _import_palbot(root):
    # After the sandbox on sys.path, so its stub config wins over any real one.
    sys.path.append(str(REPO))
    import palbot
    config_file = Path(palbot.config.__file__).resolve()
    if config_file != (root / "config" / "config.py").resolve():
        raise RuntimeError(f"refusing to run with a non-stub config: {config_file}")
    palbot.ClientSession = _StubSession
    return palbot


def _check_names(checks):
    return sorted(getattr(c, "__qualname__", repr(c)) for c in checks)


def _cooldown(cmd):
    buckets = getattr(cmd, "_buckets", None)
    cd = getattr(buckets, "_cooldown", None)
    if cd is None:
        return None
    return {"rate": cd.rate, "per": cd.per, "type": str(buckets.type)}


def _max_concurrency(cmd):
    mc = getattr(cmd, "_max_concurrency", None)
    if mc is None:
        return None
    return {"number": mc.number, "per": str(mc.per), "wait": mc.wait}


def _prefix_command(cmd):
    from discord.ext import commands
    entry = {
        "cog": cmd.cog_name,
        "aliases": sorted(cmd.aliases),
        "signature": cmd.signature,
        "help": cmd.help,
        "brief": cmd.brief,
        "hidden": cmd.hidden,
        "enabled": cmd.enabled,
        "checks": _check_names(cmd.checks),
        "cooldown": _cooldown(cmd),
        "max_concurrency": _max_concurrency(cmd),
        "callback": f"{cmd.callback.__module__}.{cmd.callback.__qualname__}",
    }
    if isinstance(cmd, commands.Group):
        entry["group"] = {
            "invoke_without_command": cmd.invoke_without_command,
            "case_insensitive": cmd.case_insensitive,
        }
    return entry


def _app_command(cmd):
    entry = {"kind": type(cmd).__name__,
             "description": getattr(cmd, "description", None)}
    if isinstance(cmd, discord.app_commands.ContextMenu):
        entry["menu_type"] = str(cmd.type)
    params = getattr(cmd, "parameters", None)
    if params is not None:
        entry["parameters"] = [
            {"name": p.name, "type": str(p.type), "required": p.required,
             "description": p.description}
            for p in params
        ]
    children = getattr(cmd, "commands", None)
    if children is not None:
        entry["subcommands"] = {c.name: _app_command(c) for c in children}
    return entry


def _loops(cog):
    from discord.ext import tasks
    found = {}
    for name, value in inspect.getmembers(type(cog)):
        loop = getattr(cog, name, None)
        if isinstance(loop, tasks.Loop):
            times = loop._time if loop._time is not tasks.MISSING else None
            found[name] = {
                "seconds": loop.seconds,
                "minutes": loop.minutes,
                "hours": loop.hours,
                "time": [str(t) for t in times] if times else None,
                "count": loop.count,
                "started_on_load": name in _started_loops.get(type(cog).__name__, set()),
            }
    return found


_started_loops = {}


def _record_loop_starts():
    from discord.ext import tasks
    original_start = tasks.Loop.start

    def start(self, *args, **kwargs):
        owner = args[0] if args else None
        if owner is not None:
            for name, value in inspect.getmembers(type(owner)):
                if value is self or getattr(owner, name, None) is self:
                    _started_loops.setdefault(type(owner).__name__, set()).add(name)
        # Don't actually run loops: they would only hit the blocked network.
        return None

    tasks.Loop.start = start
    return original_start


def _sqlite_schemas(root):
    schemas = {}
    for db in sorted(list((root / "data").glob("*")) + list((root / "logfiles").glob("*"))):
        if db.suffix not in (".sqlite", ".sqlite3", ".db") or db.name == EXTERNAL_DB:
            continue
        conn = sqlite3.connect(db)
        try:
            rows = conn.execute(
                "SELECT type, name, sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name").fetchall()
        finally:
            conn.close()
        schemas[str(db.relative_to(root))] = [
            {"type": t, "name": n, "sql": " ".join((s or "").split())} for t, n, s in rows
        ]
    return schemas


async def _collect(palbot, root):
    bot = palbot.PalBot()
    failed = []
    real_print_exception = palbot.traceback.print_exception

    def record_failure(exc_type, exc, tb, file=None, **kwargs):
        failed.append(f"{exc_type.__name__}: {exc}")
        real_print_exception(exc_type, exc, tb, file=file, **kwargs)

    palbot.traceback.print_exception = record_failure
    try:
        # Not `async with bot`: PalBot.close() calls sys.exit().
        await bot._async_setup_hook()
        await bot.setup_hook()
        # Let cog_load-spawned tasks run to completion (or fail on the network).
        await asyncio.sleep(0.2)

        prefix_commands = {c.qualified_name: _prefix_command(c)
                           for c in bot.walk_commands()}
        app_commands = {c.qualified_name: _app_command(c)
                        for c in bot.tree.get_commands()}
        cogs = {}
        for name, cog in sorted(bot.cogs.items()):
            cogs[name] = {
                "module": type(cog).__module__,
                "listeners": sorted(f"{event}:{fn.__name__}"
                                    for event, fn in cog.get_listeners()),
                "loops": _loops(cog),
            }
        bot_listeners = sorted(
            name for name in dir(type(bot))
            if name.startswith("on_") and name in type(bot).__dict__)
        extensions = sorted(bot.extensions)
        if bot.cc_conn:
            await bot.cc_conn.close()
        for cog in list(bot.cogs.values()):
            for attr in vars(cog).values():
                close = getattr(attr, "close", None)
                if type(attr).__module__.startswith("aiosqlite") and close:
                    await close()
        await discord.Client.close(bot)
    finally:
        palbot.traceback.print_exception = real_print_exception

    return {
        "bot": {
            "command_prefix": bot.command_prefix,
            "case_insensitive": bot.case_insensitive,
            "description": bot.description,
            "help_command": type(bot.help_command).__name__,
            "intents": bot.intents.value,
            "listeners": bot_listeners,
        },
        "extensions": extensions,
        "load_failures": failed,
        "cogs": cogs,
        "prefix_commands": dict(sorted(prefix_commands.items())),
        "app_commands": dict(sorted(app_commands.items())),
        "sqlite_schemas": _sqlite_schemas(root),
    }


def collect():
    """Return the inventory dict. Changes cwd/sys.path; meant for a fresh process."""
    root = _make_sandbox()
    os.chdir(root)
    sys.path.insert(0, str(root))
    _block_network()
    _record_loop_starts()
    # The bot and cogs print freely; keep stdout for the JSON.
    with contextlib.redirect_stdout(sys.stderr):
        palbot = _import_palbot(root)
        return asyncio.run(_collect(palbot, root))


def main():
    try:
        inventory = collect()
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        os._exit(1)
    text = json.dumps(inventory, indent=2, sort_keys=False, default=str) + "\n"
    if "--update" in sys.argv:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(text)
        print(f"wrote {SNAPSHOT}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    sys.stdout.flush()
    sys.stderr.flush()
    # Cog threads (e.g. aiosqlite workers) can outlive the event loop; don't wait on them.
    os._exit(0)


if __name__ == "__main__":
    main()
