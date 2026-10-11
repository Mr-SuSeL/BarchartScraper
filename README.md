# Greeks Analytics — Options Microstructure & Dealer Exposure Engine

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Framework](https://img.shields.io/badge/testing-pytest-orange.svg)
![AI Agents](https://img.shields.io/badge/agentic-GitHub%20Copilot-purple.svg)

**Greeks Analytics** is an options microstructure analysis and dealer-exposure engine for commodity and index futures. It retrieves Barchart options and futures data, calculates Black-76 prices and Greeks, and presents exposure profiles for Coffee, Sugar, Cocoa, Crude Oil, and E-mini S&P 500 futures.

## Key Features

- **Live market data:** Playwright-based scrapers retrieve options-chain and futures-history data.
- **Black-76 analytics:** Calculate Delta, Gamma, Vanna, Vomma/Volga, Charm, and implied volatility for futures options.
- **Dealer exposure profiles:** Calculate GEX, VEX, VOEX, CHEX, and Vanna Flow using contract-specific multipliers.
- **Multiple markets:** Contract specifications and ticker routing support `KC`, `SB`, `CC`, `CL`, and `ES`.
- **Responsive dashboard:** Matplotlib displays a symmetric 2 × 3 dashboard in dark mode. Strike-based `bar_width` is derived from the smallest positive gap between strikes, so bars adapt to dense and sparse option chains.
- **Persistent IV state:** Per-ticker `iv_state_{ticker}.json` files in `data/` support local IV-change calculations between cycles.

## Project Structure

```text
BarchartScrapper/
├── .github/
│   └── agents/
│       ├── architect-agent.agent.md
│       ├── math-auditor.agent.md
│       ├── python-test-agent.agent.md
│       ├── quant-engineer.agent.md
│       ├── readme-updater.agent.md
│       └── ui-ux-agent.agent.md
├── data/                       # Per-ticker JSON/CSV data and iv_state_{ticker}.json
├── dashboards/                 # Saved {ticker}_exposures_dashboard.png images
├── tests/
│   ├── e2e/                    # Pipeline and multi-cycle tests
│   ├── unit/                   # Pricing, exposure, routing, and visualization tests
│   └── conftest.py             # Shared pytest fixtures
├── black76.py                  # Black-76 pricing and Greeks
├── contract_specs.py           # Supported ticker and contract specifications
├── exposure_engine.py          # GEX, VEX, VOEX, CHEX, and Vanna Flow calculations
├── futures_parser.py           # Futures JSON parser
├── futures_scraper.py          # Futures-history scraper
├── options_parser.py           # Generic options JSON parser
├── options_scraper.py          # Options-chain scraper
├── run_pipeline.py             # CLI and continuous live pipeline
├── visualize_exposures.py      # Matplotlib 2 × 3 exposure dashboard
└── pytest.ini                  # Pytest configuration
```

Scraped data and generated dashboards are stored under `data/` and `dashboards/`, respectively. Example filenames include `kc_options.json`, `kc_options.csv`, `kc_futures.json`, `kc_futures.csv`, `iv_state_KC.json`, and `kc_exposures_dashboard.png`.

## Quick Start

Create and activate a virtual environment, install the project dependencies (`pandas`, `numpy`, `matplotlib`, `playwright`, and `pytest`), and install the Chromium browser used by Playwright:

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

pip install pandas numpy matplotlib playwright pytest
playwright install chromium
```

Run the live pipeline with a supported ticker:

```bash
python run_pipeline.py --ticker KC
python run_pipeline.py --ticker SB
python run_pipeline.py --ticker CC
python run_pipeline.py --ticker CL
python run_pipeline.py --ticker ES
```

The default ticker is `KC` if `--ticker` is omitted. The pipeline runs continuously and refreshes data and the dashboard every 15 minutes. Stop it with `Ctrl+C`.

## AI Agent Team

The repository's custom agents are defined in `.github/agents/`:

| Agent | Role |
| :--- | :--- |
| `@python-test-agent` | Creates and maintains unit, integration, and end-to-end tests with `pytest`. |
| `@quant-engineer` | Works on Black-76 pricing, Greeks, exposure calculations, and quantitative visualization. |
| `@architect-agent` | Guides architecture refactors, ticker-agnostic interfaces, and project file organization. |
| `@ui-ux-agent` | Improves Matplotlib responsiveness, strike-based dynamic `bar_width`, and dark-mode presentation. |
| `@readme-updater` | Keeps the repository README, architecture description, and usage documentation current. |
| `@math-auditor` | Audits Black-76 formulas, analytical derivatives, exposure definitions, and units. |

## Dashboard

The dashboard uses a symmetric 2 × 3 layout:

1. GEX — Gamma Exposure
2. VEX — Vanna Exposure
3. VOEX — Vomma/Volga Exposure
4. CHEX — Charm Exposure
5. Vanna Flow
6. Implied-volatility curve with local ΔIV

Bar widths are calculated from the strike spacing rather than using a fixed width, with a fallback for a single available strike. Dashboard images are saved as `dashboards/{ticker}_exposures_dashboard.png` (ticker in lowercase).

## Tests

Run the complete test suite from the repository root:

```bash
pytest
```

The latest project test status is **37 passed**.

## License

Distributed under the MIT License.
