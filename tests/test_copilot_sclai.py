"""
!sclai end to end with its collaborators (settings, context, search, LLM) stubbed.
"""
import contextlib
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules import copilot  # noqa: E402

SETTINGS = {"answer_model": "test-model", "search_max_tokens": 100,
            "max_output_tokens": 500, "context": "on", "image_lookback": 10}
IMAGE = {"url": "data:image/png;base64,AAAA"}
IMAGE_PART = {"type": "image_url", "image_url": {"url": IMAGE["url"]}}


class FakeCtx:
    def __init__(self):
        self.guild = types.SimpleNamespace(id=1)
        self.author = types.SimpleNamespace(id=2, display_name="asker", roles=[])
        self.channel = types.SimpleNamespace(id=3, typing=contextlib.nullcontext)
        self.bot = types.SimpleNamespace(is_owner=self._is_owner)
        self.sent = []

    async def _is_owner(self, user):
        return True

    async def send(self, content=None, **kwargs):
        self.sent.append(content)


def _cog(images, custom_prompt=""):
    cog = copilot.Copilot.__new__(copilot.Copilot)
    cog.bot = types.SimpleNamespace(
        user=types.SimpleNamespace(display_name="palbot", id=99),
        logger=types.SimpleNamespace(error=lambda *a: None))
    payloads = []

    async def get_all_settings(guild_id, channel_id):
        return dict(SETTINGS, system_prompt=custom_prompt)

    async def none(*args, **kwargs):
        return None

    async def build_full_context(*args, **kwargs):
        return {"channel_context": "", "user_context": "", "stable_prefix_tokens": 0,
                "debug_parts": []}

    async def chat(payload):
        payloads.append(payload)
        return {"choices": [{"message": {"content": "the answer"}}], "usage": {}}

    async def collect_recent_images(ctx, lookback):
        return list(images)

    async def get_provider_auth():
        return "token", "https://example.invalid"

    async def should_debug(ctx, settings):
        return False

    async def send_with_debug(ctx, output, debug_parts, show_debug):
        await ctx.send(output)

    cog.ai_cache = types.SimpleNamespace(
        get_all_settings=get_all_settings, get_user_prompt=none, log_usage=none)
    cog.context_gatherer = types.SimpleNamespace(
        resolve_mentions=lambda ctx, ask: ask,
        restore_mentions=lambda ctx, text: text,
        build_full_context=build_full_context,
        wrap_context=lambda channel, user: "")
    cog.provider = types.SimpleNamespace(
        chat=chat, estimate_tokens=lambda text: len(text) // 4,
        calculate_cost=lambda *a: 0)
    cog.get_provider_auth = get_provider_auth
    cog._web_search = none
    cog._collect_recent_images = collect_recent_images
    cog._should_debug = should_debug
    cog._send_with_debug = send_with_debug
    return cog, payloads


async def test_sclai_answers_without_images():
    cog, payloads = _cog(images=[])
    ctx = FakeCtx()
    await copilot.Copilot.sclai.callback(cog, ctx, ask="what's new?")
    assert ctx.sent == ["the answer"]
    system = payloads[0]["messages"][0]["content"]
    assert system.startswith("You are palbot (Discord user ID: 99)")
    assert copilot._IMAGE_HINT not in system


async def test_sclai_answers_with_recent_images():
    # Used to raise UnboundLocalError (system_prompt += before assignment).
    cog, payloads = _cog(images=[IMAGE])
    ctx = FakeCtx()
    await copilot.Copilot.sclai.callback(cog, ctx, ask="what's new?")
    assert ctx.sent == ["the answer"]
    system = payloads[0]["messages"][0]["content"]
    assert system.startswith("You are palbot (Discord user ID: 99)")
    assert system.endswith(copilot._IMAGE_HINT)
    assert IMAGE_PART in payloads[0]["messages"][1]["content"]


async def test_sclai_custom_prompt_gets_image_hint_like_clai():
    cog, payloads = _cog(images=[IMAGE], custom_prompt="Be terse.")
    ctx = FakeCtx()
    await copilot.Copilot.sclai.callback(cog, ctx, ask="hi")
    assert payloads[0]["messages"][0]["content"] == "Be terse." + copilot._IMAGE_HINT
