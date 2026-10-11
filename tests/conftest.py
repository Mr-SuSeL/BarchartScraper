import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def data_dir(tmp_path):
    """Copy tracked root fixtures into an isolated data/ directory."""
    fixture_data_dir = tmp_path / "data"
    fixture_data_dir.mkdir()
    for filename in (
        "kc_futures.json",
        "kc_options.json",
        "kc_futures.csv",
        "kc_options.csv",
    ):
        shutil.copy2(ROOT / "data" / filename, fixture_data_dir / filename)
    return fixture_data_dir


@pytest.fixture
def kc_futures_json_path(data_dir):
    return data_dir / 'kc_futures.json'


@pytest.fixture
def kc_options_json_path(data_dir):
    return data_dir / 'kc_options.json'


@pytest.fixture
def kc_options_csv_path(data_dir):
    return data_dir / 'kc_options.csv'


@pytest.fixture
def kc_futures_df(kc_futures_json_path):
    with kc_futures_json_path.open('r', encoding='utf-8') as fh:
        payload = json.load(fh)
    return pd.DataFrame(payload)


@pytest.fixture
def kc_options_df(kc_options_csv_path):
    return pd.read_csv(kc_options_csv_path)
