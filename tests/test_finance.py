"""
!stock behaviour with Yahoo's HTTP calls faked out.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules import finance  # noqa: E402

QUOTE = {
    "symbol": "AAPL", "shortName": "Apple Inc.", "regularMarketPrice": 200.5,
    "currency": "USD", "marketCap": 3_000_000_000_000,
    "regularMarketChange": 1.25, "regularMarketChangePercent": 0.63,
    "marketState": "REGULAR",
}


class FakeResponse:
    def __init__(self, status_code=200, text="", json_data=None):
        self.status_code = status_code
        self.text = text  # a property on curl_cffi responses, not a coroutine
        self._json = json_data

    def json(self):
        return self._json


class FakeSession:
    """Routes curl_cffi AsyncSession.get calls by URL substring."""
    routes = {}

    def __init__(self, *args, **kwargs):
        self.cookies = {"B": "cookie"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kwargs):
        for fragment, response in self.routes.items():
            if fragment in url:
                return response
        raise AssertionError(f"unexpected request {url}")


class FakeCtx:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, **kwargs):
        self.sent.append(content)


def _cog(monkeypatch, routes):
    FakeSession.routes = routes
    monkeypatch.setattr(finance, "AsyncSession", FakeSession)
    cog = finance.Finance(bot=None)
    cog.yahoo_crumb = None
    cog.yahoo_cookies = None
    return cog


async def test_stock_reports_quote(monkeypatch):
    cog = _cog(monkeypatch, {
        "//finance.yahoo.com/": FakeResponse(),
        "getcrumb": FakeResponse(200, text="crumb123"),
        "finance/search": FakeResponse(json_data={"quotes": [{"symbol": "AAPL"}]}),
        "finance/quote": FakeResponse(json_data={"quoteResponse": {"result": [QUOTE]}}),
    })
    ctx = FakeCtx()
    await finance.Finance.stock.callback(cog, ctx, name="apple")
    assert ctx.sent == [
        "AAPL (Apple Inc.): 200.5 USD :: Cap: 3.00 T :: Today's change: 1.25 (0.63%) "
        "\N{CHART WITH UPWARDS TREND}"
    ]
    assert cog.yahoo_crumb == "crumb123"


async def test_stock_survives_failed_crumb_request(monkeypatch, capsys):
    # The crumb error path used to `await resp.text`, a str, and crash with TypeError.
    cog = _cog(monkeypatch, {
        "//finance.yahoo.com/": FakeResponse(),
        "getcrumb": FakeResponse(429, text="Too Many Requests"),
        "finance/search": FakeResponse(json_data={"quotes": [{"symbol": "AAPL"}]}),
        "finance/quote": FakeResponse(json_data={"finance": {"error": "Unauthorized"}}),
    })
    ctx = FakeCtx()
    await finance.Finance.stock.callback(cog, ctx, name="apple")
    assert ctx.sent == []
    assert cog.yahoo_crumb is None  # retried on the next call
    out = capsys.readouterr().out
    assert "y stock lookup 429" in out
    assert "Too Many Requests" in out
