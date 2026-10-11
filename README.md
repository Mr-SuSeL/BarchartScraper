# Greeks Analytics — Options Microstructure & Dealer Exposure Engine

![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Framework](https://img.shields.io/badge/testing-pytest-orange.svg)
![AI Agents](https://img.shields.io/badge/agentic-GitHub%20Copilot-purple.svg)

**Greeks Analytics** is an advanced options microstructure analysis engine and dealer exposure profiler (GEX, VEX, VOEX, CHEX) tailored for commodity and index futures (Coffee, Sugar, Cocoa, Crude Oil, S&P 500). The system combines automated live data retrieval via Playwright, quantitative Black-76 options pricing, and a multi-agent AI software factory powered by custom VS Code Copilot Agents.

---

## Key Features

* **Live Market Data Scraping:** Asynchronous Playwright scrapers intercepting options chain ladders and futures history directly from Barchart APIs.
* **Black-76 Quantitative Options Engine:**
  * Precise analytical pricing and Greeks calculation for futures options: Delta, Gamma, Vanna, Vomma/Volga, Charm, and Implied Volatility (IV) solver.
  * Rigorous calendar time decay handling in Charm (*Delta Bleed*) with separate analytical expressions for Call and Put options.
* **USD-Denominated Dealer Exposure Profiling:**
  * **GEX (Gamma Exposure):** Re-hedging exposure relative to underlying Spot price movement ($ / +1% Spot).
  * **VEX (Vanna Exposure):** Delta sensitivity to Implied Volatility shifts ($ / +1% IV) for detecting Vanna Cascades.
  * **VOEX (Volga/Vomma Exposure):** Vega sensitivity to Implied Volatility changes.
  * **CHEX (Charm Exposure):** Delta drift over calendar time ($ Drift / 1 Day).
  * **VANNA FLOW:** Real-time estimation of dealer dollar flows driven by localized Delta IV shifts between scraping cycles.
* **Market-Agnostic Ticker Specification:** Built-in contract mapper (`KC`, `SB`, `CC`, `CL`, `ES`) that automatically adjusts contract multipliers and tick sizes.
* **Interactive Live Visualization:** A symmetrical 6-panel dashboard (2x3 grid) built with Matplotlib, featuring automatic background cycle refreshes.

---

## Agentic QA & Development Architecture (VS Code Custom Agents)

The repository integrates an AI-driven **Software Factory** pattern utilizing custom agents located in `.github/agents/`:

| Agent | Role & Responsibility |
| :--- | :--- |
| `@python-test-agent` | Automated creation and maintenance of unit, integration, and E2E test suites in `pytest`. |
| `@quant-engineer` | Refactoring core production logic, pricing models, exposure engine calculations, and Matplotlib visualizations. |
| `@math-auditor` | Quantitative audit of financial formulas and analytical derivatives via numerical finite differences verification. |

---

## Project Structure

```text
BarchartScrapper/
├── .github/
│   └── agents/                 # Custom GitHub Copilot Agents
│       ├── python-test-agent.agent.md
│       ├── quant-engineer.agent.md
│       └── math-auditor.agent.md
├── cache/                      # Persistent IV states and market data cache
├── tests/
│   ├── unit/                   # Unit tests (black76, exposure, multi-market)
│   ├── e2e/                    # E2E tests (pipeline execution, multi-cycle refresh)
│   └── conftest.py             # Fixtures and test dataset configuration
├── black76.py                  # Black-76 options pricing engine & Greeks calculator
├── contract_specs.py           # Contract specification mapper & multiplier lookup
├── exposure_engine.py          # Exposure calculation engine (GEX, VEX, VOEX, CHEX, Vanna Flow)
├── visualize_exposures.py      # Live visualization module (Matplotlib 2x3 Grid)
├── options_scraper.py          # Async Playwright options scraper
├── options_parser.py           # Generic options data parser
├── futures_scraper.py          # Async Playwright futures scraper
├── run_pipeline.py             # Main interactive execution pipeline
├── pytest.ini                  # Strict pytest configuration & logging options
└── requirements.txt            # Project dependencies

## Quick Start

### 1. Prerequisites & Installation

```bash
# Clone repository
git clone [https://github.com/](https://github.com/)<YOUR_USERNAME>/BarchartScrapper.git
cd BarchartScrapper

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.\.venv\Scripts\Activate.ps1

# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium

### 2. Running the Live Engine

```bash
python run_pipeline.py
python run_pipeline.py --ticker SB
python run_pipeline.py --ticker CL

The default ticker is `KC`. The script runs a continuous 15-minute background loop, fetching live market data and updating the ticker-specific interactive dashboard.

## Running Test Suites

The project features a 100% passing test suite covering options pricing mathematics, multi-market specs, and state persistence.

```bash
# Run all tests with verbose logging
pytest

# Run specific test layers
pytest tests/unit/
pytest tests/e2e/

## Dashboard Layout

The live Matplotlib window renders 6 key market microstructure metrics in a 2x3 grid:
1. **GEX** — Gamma Exposure (M USD)
2. **VEX** — Vanna Exposure (M USD)
3. **VOEX** — Volga/Vomma Exposure (K USD)
4. **CHEX** — Charm Exposure (M USD)
5. **VANNA FLOW** — Realized dealer capital flow (M USD)
6. **REAL IV CURVE** — Implied Volatility smile profile with localized Delta IV overlay

---

## License

Distributed under the MIT License.