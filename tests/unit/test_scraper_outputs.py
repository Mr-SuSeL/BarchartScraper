import asyncio
import json

import pytest

import futures_scraper
import options_scraper


class _FakeResponse:
    status = 200

    def __init__(self, url, payload):
        self.url = url
        self.payload = payload

    async def json(self):
        return self.payload


class _FakePage:
    def __init__(self, payload):
        self.payload = payload
        self.response_handler = None

    async def route(self, *_args, **_kwargs):
        pass

    def on(self, _event, handler):
        self.response_handler = handler

    async def goto(self, url, **_kwargs):
        await self.response_handler(_FakeResponse(url, self.payload))


class _FakeBrowser:
    def __init__(self, page):
        self.page = page

    async def new_context(self, **_kwargs):
        return self

    async def new_page(self):
        return self.page

    async def close(self):
        pass


class _FakePlaywright:
    def __init__(self, payload):
        self.browser = _FakeBrowser(_FakePage(payload))
        self.chromium = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def launch(self, **_kwargs):
        return self.browser


@pytest.mark.parametrize(
    ("module", "scrape", "filename", "payload"),
    [
        (
            options_scraper,
            options_scraper.scrape_options,
            "sb_options",
            {
                "data": [
                    {
                        "raw": {
                            "optionType": "CALL",
                            "strikePrice": 100,
                            "openInterest": 5,
                        }
                    }
                ]
            },
        ),
        (
            futures_scraper,
            futures_scraper.scrape_futures,
            "sb_futures",
            {
                "data": [
                    {
                        "raw": {
                            "tradeTime": "2026-10-11",
                            "open": 100,
                            "high": 101,
                            "low": 99,
                            "lastPrice": 100.5,
                            "volume": 10,
                        }
                    }
                ]
            },
        ),
    ],
)
def test_scrapers_create_data_directory_and_write_market_files(
    monkeypatch, tmp_path, module, scrape, filename, payload
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        module, "async_playwright", lambda: _FakePlaywright(payload)
    )

    asyncio.run(scrape("SB"))

    data_dir = tmp_path / "data"
    json_file = data_dir / f"{filename}.json"
    csv_file = data_dir / f"{filename}.csv"
    assert json_file.is_file()
    assert csv_file.is_file()
    assert json.loads(json_file.read_text(encoding="utf-8")) == payload
