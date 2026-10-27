# WealthVault-AI

AI-powered portfolio intelligence platform for risk analysis, portfolio optimization, financial calculations, smart liquidation, and personalized investment recommendations.

---

## Architecture & Project Structure

The project follows a clean, modular Python package architecture separating core configuration, API presentation, and quantitative financial computation domains:

```text
WealthVault-AI/
├── src/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py          # GET /health and GET /api/v1/health
│   │       └── router.py              # API v1 endpoint aggregator
│   ├── core/
│   │   └── config.py                  # Pydantic Settings & environment config
│   ├── financial/                     # (Planned) Equity financial statements & scoring engine
│   ├── liquidation/                   # (Planned) Smart liquidation & churn control engine
│   ├── portfolio/                     # (Planned) Portfolio aggregation & Mutual Fund engine
│   ├── recommendations/               # (Planned) Cross-asset decision & recommendation engine
│   ├── risk/                          # (Planned) Volatility, VaR, CVaR & stress-testing engine
│   └── main.py                        # FastAPI application entry point
├── finance/                           # Quantitative mathematical specifications (Word/PDF)
├── notebooks/                         # ML research, forecasting prototypes, and exploration
├── tests/                             # Automated test suite (Pytest)
├── .env.example                       # Documented environment configuration template
├── pyproject.toml                     # Modern Python build and project configuration
├── requirements.txt                   # Production runtime dependencies
└── requirements-dev.txt               # Testing and development dependencies
```

---

## Getting Started

### Prerequisites

* **Python 3.10+** (Tested on Python 3.10)
* **Git**

### 1. Environment Setup

Clone the repository and set up an isolated virtual environment:

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS (bash)
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Dependency Installation

Install the development and testing dependencies:

```bash
# Windows
.venv\Scripts\pip install -r requirements-dev.txt

# Linux / macOS
pip install -r requirements-dev.txt
```

### 3. Configuration

Copy the example environment configuration file to create your local `.env`:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Review and adjust variables in `.env` as needed:
* `ENVIRONMENT`: `development` | `staging` | `production`
* `DEBUG`: `true` | `false`
* `API_V1_STR`: `/api/v1`
* `ALLOWED_ORIGINS`: JSON list of allowed CORS origins

---

## Running the Backend Application

Start the FastAPI application using Uvicorn:

```bash
# Using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or using the Python module runner
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Once running:
* **Health Check:** [http://localhost:8000/health](http://localhost:8000/health) or [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **OpenAPI Specification:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Running Automated Tests

Execute the automated test suite with `pytest`:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run with test coverage
pytest --tb=short
```

---

## Development Status & Roadmap

* **Phase 1 (Complete):** Core backend foundation established (FastAPI, Pydantic v2 settings, health check endpoint, test suite, and virtual environment dependency management).
* **Phase 2 (Upcoming):** Implementation of standalone financial logic modules under `src/` following the specifications in `finance/`:
  * `src/financial/`: Multi-factor equity scoring engine.
  * `src/liquidation/`: 23-step smart liquidation algorithm.
  * `src/portfolio/`: 12-layer mutual fund scoring and portfolio diversification.
  * `src/recommendations/`: Gold LSTM model extraction and ONNX inference runtime.
* **Phase 3 (Upcoming):** Database persistence layer (PostgreSQL / SQLAlchemy) and market data ingestion pipelines.
