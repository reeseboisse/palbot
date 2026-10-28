"""
The server-specific checks behave as they did when their IDs were hardcoded,
and follow config overrides when set.
"""
import os
import sys
import types

import discord
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.gemini import Gemini  # noqa: E402
from modules.randomizers import Randomizers  # noqa: E402
from modules.sports import Sports  # noqa: E402

HOME = 124572142485504002
SPORTS_CHAN = 1243723119567310858
GEMINI_CHANS = [985728639981211728, 1333677981322969149, 1337293879153791036]
BRAK_USER = 167670602507747328


class FakeBot:
    def __init__(self, **config):
        self.config = types.SimpleNamespace(**config)

    async def is_owner(self, user):
        return False


class FakeMessage:
    async def delete(self):
        pass


class FakeThread(discord.Thread):
    def __init__(self, parent_id):
        self._parent_id = parent_id

    @property
    def parent(self):
        return types.SimpleNamespace(id=self._parent_id)


class FakeCtx:
    def __init__(self, bot, guild_id, channel_id, invoked_with="nhl", author_id=1):
        self.bot = bot
        self.guild = types.SimpleNamespace(id=guild_id)
        self.channel = types.SimpleNamespace(id=channel_id, guild=self.guild)
        self.author = types.SimpleNamespace(id=author_id, mention=f"<@{author_id}>")
        self.invoked_with = invoked_with
        self.sent = []

    async def send(self, content=None, **kwargs):
        self.sent.append(content)

    async def reply(self, content=None, **kwargs):
        self.sent.append(content)
        return FakeMessage()


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def instant(*args, **kwargs):
        pass
    monkeypatch.setattr("modules.gemini.asyncio.sleep", instant)


def _sports(bot):
    cog = Sports.__new__(Sports)
    cog.bot = bot
    return cog


# -- sports -----------------------------------------------------------------

async def test_sports_only_command_blocked_outside_sports_channel():
    bot = FakeBot()
    ctx = FakeCtx(bot, HOME, 1, invoked_with="ncaa")
    assert await _sports(bot).cog_check(ctx) is False
    assert ctx.sent == [f"`!ncaa` is restricted to <#{SPORTS_CHAN}>"]


async def test_sports_channel_and_other_guilds_unrestricted():
    bot = FakeBot()
    assert await _sports(bot).cog_check(FakeCtx(bot, HOME, SPORTS_CHAN, "ncaa")) is True
    assert await _sports(bot).cog_check(FakeCtx(bot, 42, 1, "ncaa")) is True


async def test_sports_follows_config_override():
    bot = FakeBot(home_guild_id=42, sports_channel_id=7)
    ctx = FakeCtx(bot, 42, 1, invoked_with="cfb")
    assert await _sports(bot).cog_check(ctx) is False
    assert ctx.sent == ["`!cfb` is restricted to <#7>"]
    assert await _sports(bot).cog_check(FakeCtx(bot, HOME, 1, "cfb")) is True


# -- gemini -----------------------------------------------------------------

async def test_gemini_chat_blocked_outside_chat_channels():
    bot = FakeBot()
    ctx = FakeCtx(bot, HOME, 1)
    assert await Gemini.chat_channel(ctx) is False
    assert ctx.sent == [
        f"`chat only works in <#{GEMINI_CHANS[0]}>. This message will self destruct."]


async def test_gemini_chat_allowed_in_chat_channels_and_elsewhere():
    bot = FakeBot()
    for chan in GEMINI_CHANS:
        assert await Gemini.chat_channel(FakeCtx(bot, HOME, chan)) is True
    assert await Gemini.chat_channel(FakeCtx(bot, 42, 1)) is True


async def test_gemini_chat_allowed_in_threads_of_chat_channels():
    bot = FakeBot()
    ctx = FakeCtx(bot, HOME, 1)
    ctx.channel = FakeThread(parent_id=GEMINI_CHANS[1])
    assert await Gemini.chat_channel(ctx) is True


async def test_gemini_silent_check_sends_nothing():
    bot = FakeBot()
    ctx = FakeCtx(bot, HOME, 1)
    assert await Gemini.chat_channel(ctx, True) is False
    assert ctx.sent == []


async def test_gemini_follows_config_override():
    bot = FakeBot(home_guild_id=42, gemini_chat_channels=[7, 8])
    ctx = FakeCtx(bot, 42, 1)
    assert await Gemini.chat_channel(ctx) is False
    assert ctx.sent == ["`chat only works in <#7>. This message will self destruct."]
    assert await Gemini.chat_channel(FakeCtx(bot, 42, 8)) is True
    assert await Gemini.chat_channel(FakeCtx(bot, HOME, 1)) is True


# -- brak -------------------------------------------------------------------

async def test_brak(monkeypatch):
    monkeypatch.setattr("modules.randomizers.random.randint", lambda a, b: 4)
    bot = FakeBot()
    cog = Randomizers(bot)
    ctx = FakeCtx(bot, HOME, 1, author_id=BRAK_USER)
    await Randomizers.brak.callback(cog, ctx)
    ctx2 = FakeCtx(bot, HOME, 1, author_id=5)
    await Randomizers.brak.callback(cog, ctx2)
    assert ctx.sent == [f"<@{BRAK_USER}> gets 4lbs of boiled beef"]
    assert ctx2.sent == ["<@5> gets 4 boiled chickens"]


async def test_brak_follows_config_override(monkeypatch):
    monkeypatch.setattr("modules.randomizers.random.randint", lambda a, b: 4)
    bot = FakeBot(brak_beef_user_id=5)
    cog = Randomizers(bot)
    ctx = FakeCtx(bot, HOME, 1, author_id=5)
    await Randomizers.brak.callback(cog, ctx)
    assert ctx.sent == ["<@5> gets 4lbs of boiled beef"]
