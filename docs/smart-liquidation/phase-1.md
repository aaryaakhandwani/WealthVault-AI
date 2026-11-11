# Smart Liquidation Engine — Phase 1 Foundation

**Specification Source:** `finance/liquidation engine _slight imporve (1).pdf` (v1.0 Refined)  
**Branch:** `feature/smart-liquidation-engine` (branched from `main` after PR #2 merge)

---

## 1. Implemented Components

Phase 1 implements only the foundational domain contracts and pure mathematical primitives whose behavior is unambiguously specified:

- **Enumerations (`src/liquidation/enums.py`):**
  - `AssetType`: `stock`, `MF`, `gold`, `FD`, `bond`, `real_estate`, `cash`
  - `AssetClass`: `equity`, `debt`, `gold`, `real_estate`, `cash`
  - `MarketState`: `RISK_ON`, `NEUTRAL`, `RISK_OFF`
- **Validated Input Schemas (`src/liquidation/schemas.py`):**
  - `PortfolioAsset` (system per-asset inputs, optional `previous_score`, optional churn-control history fields, optional per-asset `target_weight`)
  - `RebalanceInfo` (optional per-asset and per-asset-class target weights and optional threshold)
  - `LiquidationRequest` (required amount `R`, urgency `TU`, `market_state`, `assets`, optional `rebalance`)
- **Pure Derived Calculations (`src/liquidation/calculations.py`):**
  - `calculate_gain`, `calculate_tax`, `calculate_opportunity_cost`, `calculate_adjusted_return`, `calculate_risk`
  - `DerivedAssetMetrics` and `compute_derived_metrics`
- **Min-Max Normalization (`src/liquidation/normalization.py`):**
  - `min_max_normalize` (sequence normalization)
  - `min_max_normalize_mapping` (keyed mapping normalization)
- **Domain Exceptions (`src/liquidation/exceptions.py`):**
  - `LiquidationError`, `LiquidationValidationError`, `NormalizationError`, `NoEligibleAssetsError`, `PendingDecisionLogicError`

---

## 2. Module Architecture

```text
src/liquidation/
├── __init__.py        # Public package exports & Phase 2 TODO checklist
├── exceptions.py      # Domain exception hierarchy
├── enums.py           # String-backed Enums (Spec Section 1)
├── schemas.py         # Pydantic v2 request/asset/rebalance input models
├── calculations.py    # Pure Spec Section 5 derived-variable functions
└── normalization.py   # Pure Spec Section 6 min-max feature normalization

tests/liquidation/
├── __init__.py
├── test_schemas.py
├── test_calculations.py
└── test_normalization.py
```

No FastAPI routes, database models, or external service calls are introduced in Phase 1.

---

## 3. Formulas Implemented

### 3.1 Derived Variables (Spec Section 5)

- **Gain:** `G = V - P` (`calculate_gain`)
- **Tax:** `Tax = max(0, G) * T` (`calculate_tax`) — losses incur zero tax (no tax credit by default)
- **Opportunity Cost:** `OC = mu * V` (`calculate_opportunity_cost`)
- **Adjusted Return:** `AdjReturn = mu * (1 - LP)` (`calculate_adjusted_return`)
- **Risk:** `Risk = 0.5 * sigma + 0.5 * DD` (`calculate_risk`)

### 3.2 Min-Max Feature Normalization (Spec Section 6)

For each feature vector `x`:

- Empty input `[]` or `{}` returns `[]` or `{}` safely.
- Missing entries (`None`) map to `0.5` (neutral) and are excluded when computing `min` and `max`.
- If `max == min` across all present entries (including single-element inputs), all entries map to `0.5`.
- Otherwise: `norm(x_i) = (x_i - min) / (max - min)`.
- Input collections are never mutated.

---

## 4. Validation Rules

- **Finite numbers only:** `NaN`, `+inf`, `-inf`, and `bool` values passed as numeric fields are rejected (`allow_inf_nan=False` in schemas; `LiquidationValidationError` / `NormalizationError` in pure functions).
- **Monetary values (`current_value`, `purchase_value`, `required_amount`):** Must be `>= 0.0`. `required_amount = 0.0` is permitted because Spec Section 19 allows rebalance-triggered liquidation when `R` is small or zero.
- **Urgency (`urgency_days`):** Integer `>= 0` (booleans rejected).
- **Non-negative risk/duration fields:** `volatility`, `max_drawdown`, `holding_period_days`, `days_since_last_sell` must be `>= 0.0` when provided.
- **Unit-interval rates/probabilities/weights:** `loss_probability`, `tax_rate`, `target_weight`, `rebalance_threshold`, and rebalance weight map values must lie in `[0.0, 1.0]`.
- **Rebalance target weight sums:** Partial target weights are supported per Spec Section 19 ("provided for some assets or asset_class"); each map's total must be `<= 1.0 + 1e-6`.
- **Binary flags (`lock_in`, `maturity`, `sell_allowed`):** Accept `bool` or integers `0`/`1` (and `"0"`/`"1"`/`"true"`/`"false"` strings), rejecting other numbers such as `2` or `-1`.
- **Asset ID uniqueness:** `asset_id` must be non-empty after whitespace trimming and unique across `LiquidationRequest.assets`.

---

## 5. Assumptions

1. **Consistent Currency & Horizon:** `current_value`, `purchase_value`, and `required_amount` share a single currency; `expected_return` (`mu`) uses a consistent decimal return horizon across all assets in a request.
2. **Decimal Conventions:** `tax_rate` (`T`) and `loss_probability` (`LP`) are decimal fractions in `[0.0, 1.0]` (e.g., `0.15` for 15%), directly matching `max(0, G) * T` and `mu * (1 - LP)` without `/ 100` scaling.
3. **Drawdown Sign Convention:** `max_drawdown` (`DD`) is passed as a non-negative magnitude (e.g., `0.25` for a 25% drawdown) so `Risk = 0.5 * sigma + 0.5 * DD` increases monotonically with drawdown severity.
4. **Unbounded `liquidity` and `previous_score`:** Because the PDF spec (`L_i ∈`) omits explicit bounds for liquidity score and `AdjSellScore` can fall outside `[0, 1]` due to negative return terms and intelligence adjustments, neither field enforces artificial `[0, 1]` caps in Phase 1.
5. **Missing Signal Representation:** Optional feature fields on `PortfolioAsset` default to `None` so missing upstream ML/market signals propagate cleanly to `0.5` during normalization.
6. **In-Memory Historical Churn Inputs:** `previous_score`, `holding_period_days`, `days_since_last_sell`, `purchase_timestamp`, and `last_sell_timestamp` are optional request-level fields with no database persistence in Phase 1.

---

## 6. Unresolved Business Decisions (Deferred to Phase 2)

The following items from the specification contain ambiguities or require Finance/Product sign-off and are intentionally **not implemented** in Phase 1:

1. **Final `SellScore` Formula & Tax/Opportunity-Cost Signs (Sections 11 & 23):** Section 11 lists positive terms for `Tax_i_norm` and `OC_i_norm` with `Higher SellScore_i -> more attractive to sell`, whereas Section 23 states `Decision = Future Potential (AdjReturn) - Risk - Liquidity cost - Tax impact ...`. Sign conventions must be confirmed.
2. **`RISK_OFF` Weight Normalization (Section 8):** Base weights (`1.00`) and `RISK_ON` weights (`1.00`) sum to `1.00`, whereas `RISK_OFF` weights (`0.30 + 0.30 + 0.15 + 0.20 + 0.15 + 0.05 = 1.15`) exceed `1.00` when `TU > 7`. Confirm whether Section 9 weight re-normalization runs unconditionally.
3. **Intelligence Layer Adjustments & Tunables (Section 12 / 12A):** Confirm production values and applicability of `0.05` modifiers, `LP > 0.6` threshold, and `±0.15` adjustment cap.
4. **Real Estate Philosophy — Option A vs. Option B (Section 12):** Product/Finance must choose whether illiquid real estate is protected (`Option A`, default) or prioritized as a single big-ticket liquidation (`Option B`).
5. **Single-Asset Optimization Formula & Override (Section 17):** `SingleScore_i` omits `w_P` and `w_OC`, uses `+ w_L * L_i_norm` while minimizing (`argmin`), and is compared (`SingleCost + delta < MultiCost`) against `MultiCost` weighted over `SellScore`. Reconcile directionality and scale compatibility.
6. **Multi-Asset Allocation, Shortfall & Safety Constraints (Sections 15 & 16):** Define shortfall handling (relaxed re-run vs. advisor flag), handling of residual `ExcessSell` when all non-capped assets hit `V_i * alpha_i`, and reconciliation if Section 16.3 survival reduction causes total liquidation `< R`.
7. **Churn Control & Stability Decision Ordering (Sections 13 & 18):** Clarify exact pipeline ordering between Section 10 eligibility, Section 13 `STABLE` deprioritization, Section 15–17 allocation/override, and Section 18 `MinHoldingPeriod` (14d) / `CooldownAfterSell` (7d) forced `HOLD` rules.
8. **Confidence Score Formulation (Section 20):** Current `1 - variance(AdjReturn_i, LP_i, Risk_i)` mixes heterogeneous units/scales and is marked as a placeholder in the spec.
9. **Final `SELL` / `PARTIAL` / `HOLD` Output Contract (Section 21):** Clarify whether `HOLD` assets (`SellAmount_i = 0`) are included in the output list alongside `SellAmount_i > 0` items and finalize `SellPercentage` band boundaries.

---

## 7. Test Results

Command executed after all Phase 1 code edits:

```text
.venv\Scripts\python.exe -m pytest -v
```

Result: **68 passed, 1 warning in 1.86s**

- `tests/liquidation/test_calculations.py`: 13 passed
- `tests/liquidation/test_normalization.py`: 17 passed
- `tests/liquidation/test_schemas.py`: 36 passed
- `tests/test_health.py`: 2 passed (existing FastAPI health checks)

---

## 8. Next Implementation Phase

Once Finance/Product resolves the 9 pending decisions above, Phase 2 will implement:

1. Eligibility filtering (`S`) and market/urgency weight adaptation.
2. Confirmed `SellScore`, intelligence adjustments (`AdjSellScore`), and real estate policy.
3. Stability & churn-control ordering, dynamic sell fractions (`alpha_i`), multi-asset allocation, safety layer, and single-asset override.
4. Confidence scoring, explanation engine (`Reason_i`), and FastAPI endpoint wiring under `src/api/v1/`.
