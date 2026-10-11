import pytest

from contract_specs import get_contract_spec
from futures_scraper import build_futures_url
from options_scraper import build_options_url
from run_pipeline import parse_args


@pytest.mark.parametrize("ticker", ["KC", "SB", "CC", "CL", "ES"])
def test_scraper_urls_use_contract_spec_symbols(ticker):
    symbol = get_contract_spec(ticker).barchart_symbol

    assert build_options_url(ticker) == (
        f"https://www.barchart.com/futures/quotes/{symbol}/options?mode=d&view=stacked"
    )
    assert build_futures_url(ticker) == (
        f"https://www.barchart.com/futures/quotes/{symbol}/price-history/historical"
    )


def test_cli_defaults_to_kc_and_accepts_ticker_case_insensitively():
    assert parse_args([]).ticker == "KC"
    assert parse_args(["--ticker", "sb"]).ticker == "SB"


def test_cli_rejects_unsupported_ticker():
    with pytest.raises(SystemExit):
        parse_args(["--ticker", "XX"])
