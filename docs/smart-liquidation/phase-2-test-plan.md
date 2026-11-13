# Smart Liquidation Engine — Phase 2 Test Plan & Verification Matrix

**Specification Source:** `finance/liquidation engine _slight imporve (1).pdf` (v1.0 Refined)  
**Status:** Architectural Blueprint & Test Design  
**Branch:** `feature/liquidation-scoring-architecture`

---

## 1. Overview & Test Architecture

This test plan defines the complete verification suite required for **Phase 2 (Scoring, Adjustments, Explainability, and Orchestration)** of the Smart Liquidation Engine.

The suite comprises **43 test scenarios** categorized across 5 verification domains:
- **Unit Tests:** 18 scenarios
- **Boundary Tests:** 10 scenarios
- **Market Regime & Urgency Tests:** 6 scenarios
- **Explainability & Attribution Tests:** 4 scenarios
- **Error Handling & Negative Tests:** 5 scenarios
- **Total Scenarios:** **43**

In accordance with quantitative financial software engineering standards, tests are strictly partitioned between:
1. **Confirmed Invariants:** Ground-truth mathematical behaviors unambiguously established by the specification.
2. **Pending Invariants:** Tests whose numerical assertions depend on decisions recorded in [`phase-2-business-decisions.md`](./phase-2-business-decisions.md).

Tests avoid hardcoding unapproved scores. Instead, they assert architectural invariants, conservation of factor contributions, monotonic sensitivities, bounded adjustments, and error containment.

---

## 2. Test Matrix

### 2.1 Unit Tests

| Test Identifier | Category / Component | Scenario | Test Input Summary | Expected Behavior | Status / Authority |
|---|---|---|---|---|---|
| `test_factor_prep_all_features_present` | Factor Preparation | All 6 raw features present across portfolio assets | Asset with $L=0.8, \sigma=0.2, DD=0.3, T=0.15, \mu=0.10, LP=0.20, V=10^5, P=8\times 10^4$ | Computes raw $G, \text{Tax}, OC, \text{AdjReturn}, \text{Risk}$ and min-max normalizes each feature across $S$ to $[0, 1]$. | **Confirmed by PDF (Sec 5 & 6)** |
| `test_factor_prep_missing_features_neutral` | Factor Preparation | Asset with missing ML loss probability and liquidity | Asset with $LP=\text{None}, L=\text{None}$ | Normalization assigns neutral $0.5$ to $LP_{\text{norm}}$ and $L_{\text{norm}}$ without failing other factors. | **Confirmed by PDF (Sec 6)** |
| `test_factor_prep_single_eligible_asset` | Factor Preparation | Single eligible asset in portfolio ($|S|=1$) | Single asset meeting eligibility criteria | All normalized factors map to $0.5$ (neutral); no divide-by-zero occurs. | **Confirmed by PDF (Sec 6)** |
| `test_weight_config_neutral_regime` | Weight Configuration | Default NEUTRAL market regime without high urgency | `MarketState.NEUTRAL`, $TU = 14$ | Factor weights equal base weights: $w_L=0.25, w_R=0.20, w_T=0.15, w_P=0.15, w_{OC}=0.15, w_E=0.10$; sum is exactly $1.00$. | **Confirmed by PDF (Sec 7 & 8)** |
| `test_weight_config_risk_on_regime` | Weight Configuration | RISK_ON market regime without high urgency | `MarketState.RISK_ON`, $TU = 14$ | Weights adapt to: $w_L=0.20, w_R=0.15, w_T=0.15, w_P=0.10, w_{OC}=0.15, w_E=0.25$; sum is exactly $1.00$. | **Confirmed by PDF (Sec 8)** |
| `test_weight_config_risk_off_policy` | Weight Configuration | RISK_OFF market regime ($TU > 7$) under configurable normalization policies | `MarketState.RISK_OFF`, $TU = 14$, parameterized across `WeightNormalizationPolicy` | Under `UNCONDITIONAL`, weights sum to $1.00$ ($w_L \approx 0.2609, w_R \approx 0.2609 \dots$); under `CONDITIONAL_ON_URGENCY`, weights retain literal PDF sum of $1.15$. | **Requires Approval (DEC-B01)** |
| `test_weight_config_urgency_adjustment` | Weight Configuration | High urgency ($TU \le 7$) in NEUTRAL regime | `MarketState.NEUTRAL`, $TU = 3$ | $w_L \mathrel{+}= 0.10, w_E \mathrel{-}= 0.05$; all weights re-normalized to sum to $1.00$. | **Confirmed by PDF (Sec 9)** |
| `test_sell_score_calculation_invariants` | SellScore Calculator | Linear combination of normalized factors and weights | Pre-normalized factor vector $[L_n, R_n, T_n, P_n, OC_n, E_n]$, normalized weight vector | Computes deterministic base SellScore and factor contribution breakdown vector. | **Requires Approval (DEC-A01 signs)** |
| `test_intelligence_urgency_boost` | Intelligence Layer | Urgent liquidation ($TU \le 7$) | $TU = 5$, asset with $L_{\text{norm}} = 0.9$ | Adds $+ (0.05 \times 0.9) = +0.045$ to asset's score; reason logged as urgency liquidity preference. | **Confirmed by PDF (Sec 12)** |
| `test_intelligence_loss_prob_penalty` | Intelligence Layer | Asset with high loss probability ($LP > 0.6$) | $LP = 0.75, LP_{\text{norm}} = 0.8$ | Adds $+ (0.05 \times 0.8) = +0.040$ to score (penalizes holding high-loss-risk asset). | **Confirmed by PDF (Sec 12)** |
| `test_intelligence_real_estate_protect_policy` | Intelligence Layer | Real estate asset under Option A policy (`PROTECT_ILLIQUID`) | `asset_class = REAL_ESTATE`, $L_{\text{norm}} = 0.2$, policy = `PROTECT_ILLIQUID` | Subtracts $- 0.05 \times (1 - 0.2) = -0.040$ from score (protects illiquid real estate). | **Requires Approval (DEC-D01)** |
| `test_intelligence_real_estate_big_ticket_policy` | Intelligence Layer | Real estate asset under Option B policy (`BIG_TICKET_LIQUIDATION`) | `asset_class = REAL_ESTATE`, $L_{\text{norm}} = 0.2$, policy = `BIG_TICKET_LIQUIDATION` | Adds $+ 0.05 \times (1 - 0.2) = +0.040$ to score (prioritizes one big-ticket sale). | **Requires Approval (DEC-D01)** |
| `test_intelligence_regime_risk_off` | Intelligence Layer | Market regime is RISK_OFF | `MarketState.RISK_OFF`, $\text{Risk}_{\text{norm}} = 0.7$ | Adds $+ (0.05 \times 0.7) = +0.035$ to score (de-risks portfolio). | **Confirmed by PDF (Sec 12)** |
| `test_intelligence_cap_upper_bound` | Intelligence Layer | Multiple adjustments summing to $> +0.15$ | $TU=3, LP=0.8, \text{Risk}=0.9, \text{RISK\_OFF}$ | Total delta $\Delta_i$ is strictly clipped at $+0.15$; final score equals $\text{SellScore} + 0.15$. | **Confirmed by PDF (Sec 12A)** |
| `test_intelligence_cap_lower_bound` | Intelligence Layer | Multiple adjustments summing to $< -0.15$ | Cumulative negative adjustments $< -0.15$ | Total delta $\Delta_i$ is strictly clipped at $-0.15$; final score equals $\text{SellScore} - 0.15$. | **Confirmed by PDF (Sec 12A)** |
| `test_factor_contributions_sum_integrity` | Explainability Layer | Factor contributions decomposition | Computed base score and contributions | $\sum \text{FactorContributions}_k$ identically equals base SellScore within $10^{-9}$. | **Confirmed by PDF (Sec 21A)** |
| `test_explanation_top_contributors_filter` | Explainability Layer | Ranking top 2-3 contributors with $|\text{contrib}| \ge 0.02$ | Contributions vector with values $[0.22, 0.15, 0.04, 0.01, -0.08]$ | Selects top 2-3 factors by absolute magnitude; factors with magnitude $< 0.02$ ignored. | **Confirmed by PDF (Sec 21A)** |
| `test_scoring_orchestrator_end_to_end` | Scoring Orchestrator | Full scoring pipeline over multi-asset request | Valid `LiquidationRequest` with 5 diverse assets | Emits structured `PortfolioScoringResult` containing per-asset scores, contributions, adjustments, and explanations. | **Confirmed by PDF (Sec 22)** |

---

### 2.2 Boundary Tests

| Test Identifier | Category / Component | Scenario | Test Input Summary | Expected Behavior | Status / Authority |
|---|---|---|---|---|---|
| `test_boundary_zero_liquidity` | Boundary | Asset with lowest possible liquidity | $L = 0.0$ in universe where $\max L = 1.0$ | $L_{\text{norm}} = 0.0$; contributes $0.0$ to liquidity score component; handled without math errors. | **Confirmed by PDF** |
| `test_boundary_maximum_liquidity` | Boundary | Asset with highest possible liquidity | $L = 100.0$ in universe where $\min L = 10.0$ | $L_{\text{norm}} = 1.0$; contributes full $w_L$ to liquidity component. | **Confirmed by PDF** |
| `test_boundary_zero_loss_probability` | Boundary | Riskless asset with $LP = 0.0$ | $LP = 0.0, \mu = 0.08$ | $\text{AdjReturn} = 0.08 \times (1 - 0) = 0.08$; $LP_{\text{norm}}$ properly evaluated. | **Confirmed by PDF** |
| `test_boundary_max_loss_probability` | Boundary | Asset with certain loss $LP = 1.0$ | $LP = 1.0, \mu = 0.15$ | $\text{AdjReturn} = 0.0$; triggers $LP > 0.6$ intelligence adjustment if applicable. | **Confirmed by PDF** |
| `test_boundary_zero_expected_return` | Boundary | Asset with zero expected return | $\mu = 0.0, V = 10^5$ | $OC = 0.0$; $\text{AdjReturn} = 0.0$; canonicalized to $+0.0$; no negative zero artifact. | **Confirmed by PDF** |
| `test_boundary_negative_expected_return` | Boundary | Depreciating asset with negative return | $\mu = -0.12, V = 50000$ | $OC = -6000.0$; $\text{AdjReturn} = -0.12 \times (1 - LP)$; min-max handles negative values cleanly. | **Confirmed by PDF** |
| `test_boundary_missing_feature_isolation` | Boundary | One asset missing tax rate, others present | Asset A: $T=\text{None}$; Asset B: $T=0.15$; Asset C: $T=0.20$ | Asset A tax norm is $0.5$; Asset B is $0.0$; Asset C is $1.0$; missing value isolated cleanly. | **Confirmed by PDF (Sec 6)** |
| `test_boundary_equal_feature_values` | Boundary | All assets in portfolio have identical volatility | Assets A, B, C all have $\sigma = 0.18$ | Feature span is $0.0$; all assets receive neutral $0.5$ for $\text{Risk}_{\text{norm}}$. | **Confirmed by PDF (Sec 6)** |
| `test_boundary_extreme_float_values` | Boundary | Assets with astronomical values | Assets with $V_1 = 10^{14}, V_2 = 10^{14} + 10^5$ | Normalization uses half-scale arithmetic; calculations do not overflow or emit NaN. | **Confirmed by Architecture** |
| `test_boundary_zero_required_amount` | Boundary | Rebalance-triggered request with $R = 0.0$ | `required_amount = 0.0`, valid rebalance targets | Request passes validation; scoring executes normally; allocation identifies rebalance sales. | **Confirmed by PDF (Sec 19)** |

---

### 2.3 Market Regime & Urgency Tests

| Test Identifier | Category / Component | Scenario | Test Input Summary | Expected Behavior | Status / Authority |
|---|---|---|---|---|---|
| `test_regime_risk_on_high_urgency` | Regime & Urgency | RISK_ON regime with $TU \le 7$ | `MarketState.RISK_ON`, $TU = 2$ | $w_L: 0.20 \to 0.30$, $w_E: 0.25 \to 0.20$; re-normalized sum equals $1.00$; liquid equities favored. | **Confirmed by PDF (Sec 8 & 9)** |
| `test_regime_risk_on_low_urgency` | Regime & Urgency | RISK_ON regime with $TU > 7$ | `MarketState.RISK_ON`, $TU = 30$ | No urgency shift; returns maintain high weight ($w_E = 0.25$); high-return assets protected. | **Confirmed by PDF (Sec 8)** |
| `test_regime_neutral_high_urgency` | Regime & Urgency | NEUTRAL regime with $TU \le 7$ | `MarketState.NEUTRAL`, $TU = 5$ | $w_L: 0.25 \to 0.35$, $w_E: 0.10 \to 0.05$; re-normalized sum equals $1.00$. | **Confirmed by PDF (Sec 9)** |
| `test_regime_neutral_low_urgency` | Regime & Urgency | NEUTRAL regime with $TU > 7$ | `MarketState.NEUTRAL`, $TU = 15$ | Base weights remain exactly unchanged ($w_L=0.25 \dots w_E=0.10$). | **Confirmed by PDF (Sec 8)** |
| `test_regime_risk_off_high_urgency` | Regime & Urgency | RISK_OFF regime with $TU \le 7$ | `MarketState.RISK_OFF`, $TU = 1$ | $w_L$ and $w_R$ dominate; $w_E$ shifts to $0.00$; intelligence layer applies $+0.05 \text{Risk}_{\text{norm}}$ and $+0.05 L_{\text{norm}}$. | **Requires Approval (DEC-B01/B02)** |
| `test_regime_risk_off_low_urgency` | Regime & Urgency | RISK_OFF regime with $TU > 7$ | `MarketState.RISK_OFF`, $TU = 20$ | Risk mitigation prioritized ($w_R$ high); urgency boost not triggered; risk-off intelligence boost active. | **Requires Approval (DEC-B01)** |

---

### 2.4 Explainability Tests

| Test Identifier | Category / Component | Scenario | Test Input Summary | Expected Behavior | Status / Authority |
|---|---|---|---|---|---|
| `test_explain_contribution_reconciliation` | Explainability | Exact numerical audit trail | Asset scored through base + intelligence layers | $\text{TotalSellScore} \equiv \sum \text{BaseContributions} + \Delta_{\text{intelligence}}$ within floating-point tolerance ($10^{-9}$). | **Confirmed by Architecture** |
| `test_explain_traceable_reasons` | Explainability | Natural language reason generation | High-risk, high-liquidity stock under high urgency | Explanations state: "High liquidity", "Higher risk relative to alternatives", "Urgent timeline favors cash availability"; no generic or contradictory text. | **Confirmed by PDF (Sec 21A)** |
| `test_explain_no_fabricated_factors` | Explainability | Factor with near-zero contribution | Asset where $w_T \times \text{Tax}_{\text{norm}} = 0.005 < 0.02$ | Factor omitted from top reasons; only statistically significant drivers cited. | **Confirmed by PDF (Sec 21A)** |
| `test_explain_deterministic_output` | Explainability | Idempotency under identical inputs | Same asset scored in separate engine runs | Produces identical score, identical contribution floats, and identical reason strings. | **Confirmed by Architecture** |

---

### 2.5 Error Handling & Negative Tests

| Test Identifier | Category / Component | Scenario | Test Input Summary | Expected Behavior | Status / Authority |
|---|---|---|---|---|---|
| `test_error_empty_portfolio_scoring` | Error Handling | Request with empty portfolio list | `LiquidationRequest(assets=[])` | Returns empty scoring result or raises `NoEligibleAssetsError` deterministically without crashing. | **Requires Approval (DEC-I01)** |
| `test_error_no_eligible_assets` | Error Handling | All assets in portfolio locked ($LC=1$) or unapproved ($SA=0$) | Portfolio where every asset has $LC=1$ or $MC=1$ | Identifies eligible set $S = \emptyset$; terminates scoring early with structured `HOLD` status. | **Confirmed by PDF (Sec 10)** |
| `test_error_invalid_weight_configuration` | Error Handling | Custom weight dictionary with negative weight | Config with $w_L = -0.10$ | Raises `LiquidationValidationError`; rejects malformed configuration before scoring. | **Confirmed by Architecture** |
| `test_error_weight_sum_non_positive` | Error Handling | All weights configured as zero | Config with all $w = 0.0$ | Raises `LiquidationValidationError` during normalization; prevents division by zero. | **Confirmed by Architecture** |
| `test_error_non_finite_signal_propagation` | Error Handling | Unvalidated NaN injected into factor preparation | Upstream signal containing `float('nan')` | Caught at schema or calculation layer; raises `LiquidationValidationError` / `NormalizationError`. | **Confirmed by Phase 1** |

---

## 3. Test Execution Guidelines

1. **Isolation:** All tests in this plan are pure in-memory tests. They must not require a running database, network connection, or external ML service.
2. **Determinism:** Tests must use fixed timestamps and reproducible asset configurations.
3. **Execution Command:**
   ```bash
   pytest tests/liquidation/scoring/ -v --strict-markers
   ```
4. **Acceptance Criteria:** 100% pass rate across confirmed invariants; pending invariants parameterized to run once decision register sign-offs are obtained.

