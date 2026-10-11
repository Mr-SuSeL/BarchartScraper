import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def coffee_futures_json_path():
    return ROOT / 'coffee_futures.json'


@pytest.fixture
def coffee_options_json_path():
    return ROOT / 'coffee_options.json'


@pytest.fixture
def coffee_options_csv_path():
    return ROOT / 'coffee_options.csv'


@pytest.fixture
def coffee_futures_df(coffee_futures_json_path):
    with coffee_futures_json_path.open('r', encoding='utf-8') as fh:
        payload = json.load(fh)
    return pd.DataFrame(payload)


@pytest.fixture
def coffee_options_df(coffee_options_csv_path):
    return pd.read_csv(coffee_options_csv_path)
