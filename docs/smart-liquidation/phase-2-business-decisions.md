# Smart Liquidation Engine — Phase 2 Business Decision Register

**Specification Source:** `finance/liquidation engine _slight imporve (1).pdf` (v1.0 Refined)  
**Status:** Under Finance & Product Review  
**Branch:** `feature/liquidation-scoring-architecture`  
**Base Commit:** `e74be1fe1706c8fcc34086083f682cb064d7d5d5` (Merge PR #4)

---

## Executive Summary

Phase 1 established validated input schemas, pure derived calculations, min-max normalization, and error handling. However, Phase 2 scoring and execution cannot be implemented safely without resolving **10 core architectural and mathematical ambiguities** in the primary specification.

This register formally documents each ambiguity, its technical and financial implications, possible interpretations, and the concrete question submitted to the Finance and Product teams for binding sign-off. **No mathematical formula or policy will be assumed or hardcoded prior to explicit approval.**

---

## Decision Table of Contents

- [DEC-A01: SellScore Directionality and Factor Contribution Signs](#dec-a01-sellscore-directionality-and-factor-contribution-signs)
- [DEC-B01: Market Regime Weight Normalization and Sum Discrepancy](#dec-b01-market-regime-weight-normalization-and-sum-discrepancy)
- [DEC-B02: Urgency Weight Adjustment Interaction with Regime Weights](#dec-b02-urgency-weight-adjustment-interaction-with-regime-weights)
- [DEC-C01: Intelligence Layer Context Adjustments and Thresholds](#dec-c01-intelligence-layer-context-adjustments-and-thresholds)
- [DEC-D01: Real Estate Liquidation Strategy (Option A vs. Option B)](#dec-d01-real-estate-liquidation-strategy-option-a-vs-option-b)
- [DEC-E01: Single-Asset Optimization Formula and Override Comparability](#dec-e01-single-asset-optimization-formula-and-override-comparability)
- [DEC-F01: Safety Layer Allocation, Caps, Redistribution, and Shortfall](#dec-f01-safety-layer-allocation-caps-redistribution-and-shortfall)
- [DEC-G01: Stability Check and Churn Control Ordering](#dec-g01-stability-check-and-churn-control-ordering)
- [DEC-H01: Confidence Score Metric and Scale Consistency](#dec-h01-confidence-score-metric-and-scale-consistency)
- [DEC-I01: Output Contract, Action Bands, and Empty Portfolio Semantics](#dec-i01-output-contract-action-bands-and-empty-portfolio-semantics)
- [DEC-J01: Input Convention Standardization (Drawdown, Tax Rate, Horizon)](#dec-j01-input-convention-standardization-drawdown-tax-rate-horizon)

---

### DEC-A01: SellScore Directionality and Factor Contribution Signs

- **Specification Reference:** Section 11 (page 3), Section 21A (page 8), Section 23 (page 9)
- **Exact Ambiguity:**
  Section 11 states:
  $$\text{Higher } \text{SellScore}_i \to \text{more attractive to sell}$$
  It lists positive terms:
  $$+ (w_L \times L_{\text{norm}}) + (w_R \times \text{Risk}_{\text{norm}}) + (w_T \times \text{Tax}_{\text{norm}}) + (w_P \times LP_{\text{norm}}) + (w_{OC} \times OC_{\text{norm}}) - (w_E \times \text{AdjReturn}_{\text{norm}})$$
  Section 21A mirrors these positive signs for Tax and Opportunity Cost contributions.
  However, Section 23 ("CORE PRINCIPLE") states:
  $$\text{Decision} = \text{Future Potential} (\text{AdjReturn}) - \text{Risk} - \text{Liquidity cost} - \text{Tax impact} \dots$$
  If a higher `SellScore` means "sell this asset first", adding $+ (w_T \times \text{Tax}_{\text{norm}})$ and $+ (w_{OC} \times OC_{\text{norm}})$ **penalizes low-tax and low-opportunity-cost assets**, prioritizing assets with *highest* capital gains tax liability and *highest* lost future earnings.
- **Why It Matters:** Sign reversal fundamentally changes liquidation recommendations. An inverted tax sign will cause high-tax-liability assets to be liquidated before zero-tax assets, triggering unnecessary capital gains tax for clients.
- **Possible Interpretations:**
  - *Interpretation A (Tax & OC Penalize Selling — Economically Rational):* High tax and high opportunity cost make an asset *less* desirable to sell. The formula should subtract them:
    $$\text{SellScore}_i = w_L L_{\text{norm}} + w_R \text{Risk}_{\text{norm}} + w_P LP_{\text{norm}} - w_T \text{Tax}_{\text{norm}} - w_{OC} OC_{\text{norm}} - w_E \text{AdjReturn}_{\text{norm}}$$
  - *Interpretation B (Section 11 Literal):* The engine literally treats high tax and high opportunity cost as positive contributors to selling (e.g. interpreting `Tax` as "tax harvesting priority" or assuming Section 11 overrides Section 23).
  - *Interpretation C (Inverted SellScore Minimization):* `SellScore` represents retention desirability (higher = keep), so the engine should minimize `SellScore` when liquidating.
- **Consequences:** Interpretation B leads to severe tax inefficiency. Interpretation C requires inverting all sort orders in Section 15.1. Interpretation A aligns with wealth management fiduciary standards but contradicts the literal text of Section 11.
- **Architectural Solution:** The `SellScoreCalculator` establishes a `SellScoreFormulaStrategy` protocol parameterizing factor signs:
  $$C_{i,k} = s_k \times w_k \times X_{i,k,\text{norm}}, \quad s_k \in \{+1, -1\}$$
  $$\text{BaseSellScore}_i = \sum_k C_{i,k}$$
  The engine supports interchangeable strategies (`Section11LiteralStrategy` vs. `FiduciaryCostPenaltyStrategy`) via configuration, ensuring the architecture is completely formula-agnostic until Finance provides binding sign-off.
- **Recommended Clarification Question:** "Should `Tax_i_norm` and `OC_i_norm` have negative signs in `SellScore` so that assets with higher tax liabilities and higher opportunity costs are protected from liquidation, or does the desk intend a positive sign for tax-loss harvesting / another objective?"
- **Approval Status:** PENDING FINANCE SIGN-OFF

---

### DEC-B01: Market Regime Weight Normalization and Sum Discrepancy

- **Specification Reference:** Section 7 (page 2), Section 8 (page 2-3)
- **Exact Ambiguity:**
  - Base weights (Section 7):
    $$w_L (0.25) + w_R (0.20) + w_T (0.15) + w_P (0.15) + w_{OC} (0.15) + w_E (0.10) = 1.00$$
  - `RISK_ON` regime (Section 8):
    $$w_L (0.20) + w_R (0.15) + w_T (0.15) + w_P (0.10) + w_{OC} (0.15) + w_E (0.25) = 1.00$$
  - `RISK_OFF` regime (Section 8):
    $$w_L (0.30) + w_R (0.30) + w_T (0.15) + w_P (0.20) + w_{OC} (0.15) + w_E (0.05) = 1.15$$
  The `RISK_OFF` weights sum to **1.15**, not 1.00. The specification states in Section 9 that re-normalization occurs *if TU <= 7*, but does not specify whether `RISK_OFF` base weights must be re-normalized when $TU > 7$.
- **Why It Matters:** If weights sum to 1.15 in `RISK_OFF` while summing to 1.00 in `NEUTRAL` and `RISK_ON`, scores across regimes cannot be compared, threshold boundaries in Section 14 ($\alpha_i$ bands: $\ge 0.70, 0.40, < 0.40$) are distorted, and intelligence adjustment caps ($\pm 0.15$) have unequal relative power.
- **Possible Interpretations:**
  - *Interpretation A (Unconditional Re-normalization):* Normalize regime weights to sum to 1.00 across all regimes and urgency levels:
    $$w_k \leftarrow \frac{w_k}{\sum w}$$
    In `RISK_OFF`, $w_L \approx 0.2609, w_R \approx 0.2609, w_T \approx 0.1304, w_P \approx 0.1739, w_{OC} \approx 0.1304, w_E \approx 0.0435$.
  - *Interpretation B (Revised Weight Profile):* The PDF values for $w_T$ and $w_{OC}$ in `RISK_OFF` were meant to be reduced (e.g. $w_T = 0.075, w_{OC} = 0.075$, summing to 1.00).
  - *Interpretation C (Literal Specification As-Is):* Retain raw weights summing to 1.15 whenever $TU > 7$, re-normalizing only when $TU \le 7$ as specified in Section 9.
- **Consequences:** Interpretation C violates weight convexity and corrupts score-based dynamic allocation. Interpretation A preserves factor proportions deterministically. Interpretation B requires quantitative research calibration.
- **Architectural Solution:** To prevent software implementation from hardcoding an unapproved financial rule, the scoring engine establishes a `WeightNormalizationPolicy` strategy:
  - `WeightNormalizationPolicy.UNCONDITIONAL`: Re-normalizes weights across all regimes to sum to 1.00.
  - `WeightNormalizationPolicy.CONDITIONAL_ON_URGENCY`: Re-normalizes *only* when $TU \le 7$, retaining raw specification weights (summing to 1.15 in `RISK_OFF`) when $TU > 7$.
  - `WeightNormalizationPolicy.EXPLICIT_REVISION`: Ingests an externally approved revised weight matrix.
  The engine parameterizes this policy via configuration and selects no default until Finance confirms.
- **Recommended Clarification Question:** "Should `RISK_OFF` weights be normalized to sum to 1.00 unconditionally across all urgency levels (`WeightNormalizationPolicy.UNCONDITIONAL`), or should specific individual factor weights ($w_T, w_{OC}$) be revised for the `RISK_OFF` regime, or should raw 1.15 weights be retained when $TU > 7$?"
- **Approval Status:** PENDING QUANT / FINANCE SIGN-OFF

---

### DEC-B02: Urgency Weight Adjustment Interaction with Regime Weights

- **Specification Reference:** Section 9 (page 3)
- **Exact Ambiguity:**
  Section 9 defines:
  $$\text{If } TU \le 7: w_L \mathrel{+}= 0.10, \quad w_E \mathrel{-}= 0.05$$
  $$\text{Then re-normalize all weights to sum to 1: } w_k = \frac{w_k}{\sum w}$$
  In `RISK_OFF`, $w_E$ is already $0.05$. Applying $w_E \mathrel{-}= 0.05$ drives $w_E$ to **$0.00$**, completely eliminating expected return from consideration during urgent risk-off liquidations.
- **Why It Matters:** Zeroing out $w_E$ means two assets with identical risk/liquidity but drastically different expected returns (e.g. 2% vs 25%) will receive identical return consideration.
- **Possible Interpretations:**
  - *Interpretation A:* Allow $w_E = 0.00$ in high-urgency `RISK_OFF` (liquidity and risk dominate completely).
  - *Interpretation B:* Impose a floor on $w_E$ (e.g. $\min w_E = 0.02$).
  - *Interpretation C:* Urgency adjustment applies as a multiplicative tilt rather than additive increments.
- **Consequences:** Needs confirmation so test expectations for $TU \le 7$ in `RISK_OFF` are deterministic.
- **Recommended Clarification Question:** "Is driving the expected return weight $w_E$ to exactly 0.00 in high-urgency `RISK_OFF` ($TU \le 7$) intended behavior, or should a non-zero floor be enforced?"
- **Approval Status:** PENDING FINANCE SIGN-OFF

---

### DEC-C01: Intelligence Layer Context Adjustments and Thresholds

- **Specification Reference:** Section 12 (page 3-4), Section 12A (page 4)
- **Exact Ambiguity:**
  The intelligence layer adds context-based increments to $\text{SellScore}_i$:
  1. Urgency: $\text{If } TU \le 7 \implies \Delta \mathrel{+}= 0.05 \times L_{\text{norm}}$
  2. Loss Probability: $\text{If } LP_i > 0.6 \implies \Delta \mathrel{+}= 0.05 \times LP_{\text{norm}}$
  3. Regime: $\text{If } \text{MarketState} = \text{RISK\_OFF} \implies \Delta \mathrel{+}= 0.05 \times \text{Risk}_{\text{norm}}$
  4. Real Estate: Option A vs. Option B (see DEC-D01).
  5. Cap: $|\Delta_i| \le 0.15$.
  Ambiguities:
  - Are these adjustments additive on top of base weights that *already* account for urgency (Section 9) and regime (Section 8)?
  - Is $LP_i > 0.6$ checked on raw $LP_i$ (decimal in $[0, 1]$) or normalized $LP_{i,\text{norm}}$?
  - Does the cap $\pm 0.15$ clip symmetrically before or after stability checks?
- **Why It Matters:** Double-counting urgency and risk-off regime (both in factor weights and in the intelligence layer) can overly penalize equities during brief market dips.
- **Possible Interpretations:**
  - *Interpretation A:* Literal implementation: apply adjustments additively on top of adjusted weights, check raw $LP_i > 0.6$, clip at $\pm 0.15$.
  - *Interpretation B:* The intelligence layer was intended as an alternative overlay when dynamic weights are disabled.
- **Recommended Clarification Question:** "Confirm whether the intelligence layer adjustments in Section 12 should apply concurrently with the weight adjustments in Section 8 and 9, and confirm that the $LP_i > 0.6$ condition evaluates raw $LP_i$."
- **Approval Status:** PENDING PRODUCT SIGN-OFF

---

### DEC-D01: Real Estate Liquidation Strategy (Option A vs. Option B)

- **Specification Reference:** Section 12 (page 4)
- **Exact Ambiguity:**
  The specification explicitly presents two mutually exclusive philosophies and directs engineering to choose one:
  > *Option A — Avoid forced selling of illiquid real estate (default):*
  > $\text{If } \text{asset\_class} = \text{real\_estate} \implies \text{AdjSellScore} \mathrel{-}= 0.05 \times (1 - L_{\text{norm}})$
  > *(Illiquid real estate is slightly protected; you sell it only if really necessary.)*
  >
  > *Option B — Use real estate as "one big ticket" when needed:*
  > $\text{If } \text{asset\_class} = \text{real\_estate} \implies \text{AdjSellScore} \mathrel{+}= 0.05 \times (1 - L_{\text{norm}})$
  > *(Illiquid real estate becomes more likely to be sold in one shot.)*
  >
  > *Choose ONE option for production and keep it consistent.*
- **Why It Matters:** Real estate transactions take weeks/months to close and carry high transaction friction. Option A treats real estate as a last resort; Option B treats it as a primary cash-raising mechanism for large amounts.
- **Possible Interpretations:**
  - *Interpretation A (Protect Illiquid Real Estate):* Adopt Option A (`RealEstateStrategyPolicy.PROTECT_ILLIQUID`). Real estate has low liquidity on short horizons ($TU \le 7$); illiquid property is protected with a negative score penalty $\Delta = -0.05 \times (1 - L_{\text{norm}})$.
  - *Interpretation B (Big-Ticket Liquidation):* Adopt Option B (`RealEstateStrategyPolicy.BIG_TICKET_LIQUIDATION`). Real estate is prioritized to satisfy large cash requirements in a single trade via $\Delta = +0.05 \times (1 - L_{\text{norm}})$.
  - *Interpretation C (Configurable Policy — Recommended Architecture):* Establish an explicit `RealEstateStrategyPolicy` enum (`PROTECT_ILLIQUID`, `BIG_TICKET_LIQUIDATION`, `NEUTRAL`), passed via portfolio mandate configuration, with no production default hardcoded until Product confirms.
- **Consequences:** Adopting Option B without an operational real estate disposition desk would recommend liquidating illiquid property within days. Adopting Option A prevents large single-ticket real estate sales even when appropriate for high-net-worth real estate mandates.
- **Architectural Solution:** The `IntelligenceAdjustmentService` accepts a `RealEstateStrategyPolicy` configuration parameter. It does not hardcode Option A as an approved default, ensuring the engine remains neutral until Product signs off.
- **Recommended Clarification Question:** "Which real estate liquidation policy should be established as the mandate default (`PROTECT_ILLIQUID` / Option A vs. `BIG_TICKET_LIQUIDATION` / Option B), or should it remain mandate-configurable?"
- **Approval Status:** PENDING PRODUCT & DESK SIGN-OFF

---

### DEC-E01: Single-Asset Optimization Formula and Override Comparability

- **Specification Reference:** Section 17 (page 6), Section 17.1 (page 6-7)
- **Exact Ambiguity:**
  If an asset exists with $V_i \ge R$:
  $$\text{SingleScore}_i = (w_L \times L_{\text{norm}}) + (w_T \times \text{Tax}_{\text{norm}}) + (w_R \times \text{Risk}_{\text{norm}}) - (w_E \times \text{AdjReturn}_{\text{norm}})$$
  Let $i^* = \operatorname{argmin}_i \text{SingleScore}_i$.
  Override condition:
  $$\text{If } \text{SingleCost} + \delta < \text{MultiCost} \implies \text{Override with single asset } i^*$$
  where $\text{MultiCost} = \sum_{i} \frac{\text{SellAmount}_i}{R} \times \text{SellScore}_i$.
  Ambiguities:
  1. In Section 11, higher `SellScore` means *more attractive to sell*. In Section 17, `SingleScore` uses $\operatorname{argmin}$ (lowest score is chosen!). If both use positive terms for liquidity and risk, $\operatorname{argmin}$ selects the asset with *lowest* liquidity and *lowest* risk!
  2. `SingleScore` omits $w_P \times LP_{\text{norm}}$ and $w_{OC} \times OC_{\text{norm}}$, making `SingleCost` numerically non-comparable to `MultiCost`.
  3. $\delta = 0.05$ is compared directly against dimensionally incompatible score aggregates.
- **Why It Matters:** Recommending a single-asset override based on an inverted, truncated formula can liquidate an illiquid, low-return asset and cancel a well-diversified multi-asset liquidation plan.
- **Possible Interpretations:**
  - *Interpretation A:* `SingleScore` should use identical factor terms and directionality as `AdjSellScore`, choosing $i^* = \operatorname{argmax}_i \text{AdjSellScore}_i$, and overriding when $\text{AdjSellScore}_{i^*} > \text{MultiScore} - \delta$.
  - *Interpretation B:* The specification's "Cost" terminology implies that higher cost is bad, so $\operatorname{argmin}$ was intended for a cost-minimization function, but the factor signs in Section 17 were copy-pasted without inversion.
- **Recommended Clarification Question:** "Should single-asset optimization select the asset maximizing `AdjSellScore` (highest liquidation score) among assets with $V_i \ge R$, and evaluate override via comparable score weighted averages?"
- **Approval Status:** PENDING QUANT SIGN-OFF

---

### DEC-F01: Safety Layer Allocation, Caps, Redistribution, and Shortfall

- **Specification Reference:** Section 15.2 (page 5), Section 16.1–16.3 (page 5-6)
- **Exact Ambiguity:**
  - Section 16.1 caps any asset class at $80\%$ of $\text{TotalSell}$:
    $$\text{ClassSell}_c \le 0.80 \times \text{TotalSell}$$
  - Section 16.2 attempts to redistribute $\text{ExcessSell}$ to remaining eligible assets up to $V_i \times \alpha_i$.
  - Ambiguity 1: If remaining candidate assets cannot absorb $\text{ExcessSell}$ without breaching their dynamic fraction $\alpha_i$ or their own 80% cap, does the engine violate the 80% cap, relax $\alpha_i$, or declare a cash shortfall?
  - Ambiguity 2: Section 16.3 mandates portfolio survival: at least 2 asset classes must have $V_{\text{after\_sell}} > 0$. If an asset sale would wipe out the penultimate class, the sale amount is curtailed. Does this reduction cause an allowed cash shortfall below $R$?
  - Ambiguity 3: Section 15.2 notes: "If Remaining > 0: re-run with relaxed constraints, or flag to advisor/user". Which strategy is automated?
- **Why It Matters:** An engine that silently generates $\sum \text{SellAmount}_i < R$ without structured shortfall notification leaves the user with insufficient cash for their obligation.
- **Possible Interpretations:**
  - *Interpretation A (Strict Target, Advisory Fallback):* Enforce caps strictly. If shortfall occurs, return the partial plan with a structured `ShortfallWarning(requested=R, allocated=TotalSell, shortfall=R - TotalSell)` and do not auto-relax constraints without user consent.
  - *Interpretation B (Auto-Relax):* Incrementally relax $\alpha_i$ (e.g. up to 1.0) before failing.
- **Recommended Clarification Question:** "When safety caps (80% concentration cap, 2-class survival) prevent raising the full required amount $R$, should the engine output a partial liquidation with an explicit `SHORTFALL` status, or automatically relax $\alpha_i$ bands?"
- **Approval Status:** PENDING PRODUCT & RISK SIGN-OFF

---

### DEC-G01: Stability Check and Churn Control Ordering

- **Specification Reference:** Section 13 (page 4), Section 18 (page 7)
- **Exact Ambiguity:**
  - Section 13: If $|\text{AdjSellScore}_i - \text{previous\_score}_i| < 0.10$, mark asset as `STABLE`. STABLE assets are deprioritized into a second-tier bucket during allocation.
  - Section 18:
    - If holding period $< 14$ days $\implies$ force `HOLD` ($\text{SellAmount}_i = 0$).
    - If last sell $< 7$ days ago $\implies$ force `HOLD`.
    - If score change $< 0.10 \implies$ treat as `STABLE`.
  - Ambiguity: Does Section 18 churn filtering occur:
    - *At eligibility (Section 10):* Exclude from eligible set $S$ completely?
    - *At sorting (Section 15.1):* Place in a zero-allocation bucket?
    - *Post-allocation:* Zero out $\text{SellAmount}_i$ after allocation (which would cause immediate shortfall)?
- **Why It Matters:** Filtering churn-blocked assets *after* multi-asset allocation creates artificial cash shortfalls and corrupts proportional redistribution. Filtering them *before* allocation ensures the allocation loop solves for $R$ over genuinely tradable assets.
- **Possible Interpretations:**
  - *Interpretation A (Upfront Eligibility Filter — Recommended):* Assets with holding period $< 14$ days or last sell $< 7$ days are excluded in Section 10 ($SA_i = 0$), so they never consume allocation quotas.
  - *Interpretation B (Post-Allocation Filter):* Zero out amounts post-allocation as written in Section 18 ("before final SellAmount is confirmed").
- **Recommended Clarification Question:** "Should churn controls (`MinHoldingPeriod < 14d`, `CooldownAfterSell < 7d`) filter assets upfront in Section 10 eligibility so that the allocation engine plans over available assets, or apply as a post-allocation override?"
- **Approval Status:** PENDING RISK & COMPLIANCE SIGN-OFF

---

### DEC-H01: Confidence Score Metric and Scale Consistency

- **Specification Reference:** Section 20 (page 7)
- **Exact Ambiguity:**
  $$\text{raw\_conf}_i = 1 - \operatorname{variance}(\text{AdjReturn}_i, LP_i, \text{Risk}_i)$$
  $$\text{Confidence}_i = \max(0, \min(1, \text{raw\_conf}_i))$$
  The specification explicitly flags:
  > *(Exact formula can be refined later with ML; this version is a simple placeholder.)*
  Problem: $\text{AdjReturn}_i$ is an annualized decimal return (e.g. $0.12$), $LP_i$ is a probability in $[0, 1]$ (e.g. $0.20$), and $\text{Risk}_i = 0.5 \sigma + 0.5 DD$ is a composite volatility metric (e.g. $0.25$). Calculating sample variance across 3 heterogeneous financial quantities with different dimensions has no statistical meaning.
- **Why It Matters:** Variance of 3 values in $[0, 1]$ is bounded by $\le 0.25$, meaning $\text{raw\_conf}_i \ge 0.75$ always, making the confidence score clustered in $[0.75, 1.0]$ without discriminative power.
- **Possible Interpretations:**
  - *Interpretation A:* Implement the literal formula as a documented baseline placeholder until ML replacement.
  - *Interpretation B:* Compute variance over *normalized* factors ($\text{AdjReturn}_{\text{norm}}, LP_{\text{norm}}, \text{Risk}_{\text{norm}}$).
  - *Interpretation C:* Replace with data completeness / signal dispersion metric.
- **Recommended Clarification Question:** "Should the Phase 2 baseline confidence score compute variance over normalized metrics $\operatorname{variance}(\text{AdjReturn}_{\text{norm}}, LP_{\text{norm}}, \text{Risk}_{\text{norm}})$, or does the quantitative research team have an updated confidence formulation?"
- **Approval Status:** PENDING QUANT RESEARCH SIGN-OFF

---

### DEC-I01: Output Contract, Action Bands, and Empty Portfolio Semantics

- **Specification Reference:** Section 10 (page 3), Section 21 (page 8)
- **Exact Ambiguity:**
  - Section 21 header: "For each asset i with $\text{SellAmount}_i > 0$, output: [asset_id, class, SellAmount, SellPercentage, Action, AdjSellScore, Confidence, Reason]"
  - Action definition in Section 21:
    $$\text{Action}_i \in \{\text{SELL}, \text{PARTIAL}, \text{HOLD}\}$$
    $$\ge 0.70 = \text{SELL}, \quad 0 < x < 0.70 = \text{PARTIAL}, \quad 0 = \text{HOLD}$$
  - Conflict: If the output only includes assets with $\text{SellAmount}_i > 0$, no asset will ever have $\text{Action}_i = \text{HOLD}$ in the returned list.
  - Ambiguity 2: What should the engine return when the portfolio has 0 assets, or when eligible set $S = \emptyset$? Section 10 says "Return: HOLD (no eligible assets to liquidate)".
- **Why It Matters:** Client frontend UIs and downstream trade execution order-routing systems need a deterministic schema: either a list of trades to execute, or a comprehensive portfolio state showing actions for all holdings.
- **Possible Interpretations:**
  - *Interpretation A (Execution Output + Summary):* Return a plan containing `allocations` (only non-zero trades: `SELL` and `PARTIAL`) plus an optional `hold_holdings` list or summary metadata (`total_liquidated`, `shortfall`, `status`).
  - *Interpretation B (Full Portfolio View):* Return every portfolio asset with its computed action (`SELL`, `PARTIAL`, `HOLD`).
- **Recommended Clarification Question:** "Should the output payload return all portfolio assets including `HOLD` holdings, or only active execution allocations ($\text{SellAmount} > 0$) with portfolio-level summary metadata?"
- **Approval Status:** PENDING PRODUCT & FRONTEND SIGN-OFF

---

### DEC-J01: Input Convention Standardization (Drawdown, Tax Rate, Horizon)

- **Specification Reference:** Section 3 (page 1), Section 19 (page 7)
- **Exact Ambiguity:**
  1. `max_drawdown`: Is it positive magnitude ($0.25$) or negative drawdown ($-0.25$)?
  2. `tax_rate`: Decimal fraction ($0.15$) or percentage ($15.0$)?
  3. `rebalance_threshold`: Decimal fraction ($0.05$) or percentage points ($5.0$)?
  4. `expected_return` horizon: Is it annualized, monthly, or horizon-matched to urgency $TU$?
- **Why It Matters:** Phase 1 relaxed input validation to avoid prematurely locking assumptions. However, calculation formulas like $0.5 \sigma + 0.5 DD$ and $G \times T$ will yield wildly incorrect results if percentage numbers are passed into decimal formulas.
- **Possible Interpretations:**
  - Standardize on **strict decimal units** across all internal calculation boundaries:
    - `max_drawdown`: Non-negative magnitude $\in [0, 1]$ or decimal scale.
    - `tax_rate`: Decimal fraction $\in [0, 1]$.
    - `rebalance_threshold`: Decimal fraction $\in [0, 1]$.
    - `expected_return`: Annualized decimal fraction.
- **Recommended Clarification Question:** "Can Finance and Data Engineering formally confirm that all upstream financial feeds will provide `tax_rate`, `rebalance_threshold`, and `max_drawdown` as non-negative decimal fractions (e.g. 0.15 for 15%)?"
- **Approval Status:** PENDING DATA ENGINEERING & FINANCE SIGN-OFF

---

## Decision Status Summary Matrix

| ID | Topic | Primary Stakeholder | Current Status | Blocker for Phase 2 Implementation? |
|---|---|---|---|---|
| **DEC-A01** | SellScore Factor Signs | Head of Quantitative Research | **PENDING** | **YES — Direct Blocker for Scoring** |
| **DEC-B01** | Regime Weight Sum (RISK_OFF) | Quant Finance Team | **PENDING** | **YES — Blocker for Weight Config** |
| **DEC-B02** | Urgency Weight Zero Floor | Quant Finance Team | **PENDING** | Minor (Can support floor configuration) |
| **DEC-C01** | Intelligence Layer Interaction | Product Lead | **PENDING** | Moderate (Affects scoring overlay) |
| **DEC-D01** | Real Estate Option A vs B | Wealth Product Lead | **PENDING** | Moderate (Recommend Option A default) |
| **DEC-E01** | Single-Asset Formula Consistency | Quant Finance Team | **PENDING** | **YES — Blocker for Override Logic** |
| **DEC-F01** | Allocation Shortfall & Safety Caps | Risk Management | **PENDING** | **YES — Blocker for Allocation** |
| **DEC-G01** | Stability / Churn Ordering | Compliance & Operations | **PENDING** | Moderate (Recommend upfront filter) |
| **DEC-H01** | Confidence Score Definition | Data Science / ML Team | **PENDING** | Minor (Can use normalized placeholder) |
| **DEC-I01** | Output Schema & HOLD Semantics | Frontend & API Gateway Lead | **PENDING** | Moderate (Affects response DTO) |
| **DEC-J01** | Upstream Decimal Units | Data Engineering | **PENDING** | **YES — Blocker for Engine Inputs** |

