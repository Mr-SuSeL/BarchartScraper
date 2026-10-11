import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def kc_futures_json_path():
    return ROOT / 'kc_futures.json'


@pytest.fixture
def kc_options_json_path():
    return ROOT / 'kc_options.json'


@pytest.fixture
def kc_options_csv_path():
    return ROOT / 'kc_options.csv'


@pytest.fixture
def kc_futures_df(kc_futures_json_path):
    with kc_futures_json_path.open('r', encoding='utf-8') as fh:
        payload = json.load(fh)
    return pd.DataFrame(payload)


@pytest.fixture
def kc_options_df(kc_options_csv_path):
    return pd.read_csv(kc_options_csv_path)
