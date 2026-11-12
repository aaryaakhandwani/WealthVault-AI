"""Smart Liquidation Engine — Phase 1 Foundation.

Exposes validated input schemas, enumerations, pure derived-variable calculations,
min-max normalization utilities, and domain exceptions.

TODO (Phase 2 — pending Finance/Product sign-off; see docs/smart-liquidation/phase-1.md):
    - Final SellScore formula and tax/opportunity-cost signs (Spec Sections 11 & 23).
    - RISK_OFF weight sum normalization behavior (Spec Section 8).
    - Final intelligence layer adjustments & real estate Option A vs Option B (Spec Section 12).
    - Single-asset optimization score formula & override check (Spec Section 17).
    - Multi-asset allocation, shortfall fallback, and safety constraints (Spec Sections 15-16).
    - Churn control and stability check execution ordering (Spec Sections 13 & 18).
    - Confidence score formulation (Spec Section 20).
    - Final SELL / PARTIAL / HOLD decision & explanation output (Spec Section 21).
"""

from src.liquidation.calculations import (
    DerivedAssetMetrics,
    calculate_adjusted_return,
    calculate_gain,
    calculate_opportunity_cost,
    calculate_risk,
    calculate_tax,
    compute_derived_metrics,
)
from src.liquidation.enums import AssetClass, AssetType, MarketState
from src.liquidation.exceptions import (
    LiquidationError,
    LiquidationValidationError,
    NoEligibleAssetsError,
    NormalizationError,
    PendingDecisionLogicError,
)
from src.liquidation.normalization import (
    NEUTRAL_NORMALIZED_VALUE,
    min_max_normalize,
    min_max_normalize_mapping,
)
from src.liquidation.schemas import (
    LiquidationRequest,
    PortfolioAsset,
    RebalanceInfo,
)

__all__ = [
    "AssetClass",
    "AssetType",
    "DerivedAssetMetrics",
    "LiquidationError",
    "LiquidationRequest",
    "LiquidationValidationError",
    "MarketState",
    "NEUTRAL_NORMALIZED_VALUE",
    "NoEligibleAssetsError",
    "NormalizationError",
    "PendingDecisionLogicError",
    "PortfolioAsset",
    "RebalanceInfo",
    "calculate_adjusted_return",
    "calculate_gain",
    "calculate_opportunity_cost",
    "calculate_risk",
    "calculate_tax",
    "compute_derived_metrics",
    "min_max_normalize",
    "min_max_normalize_mapping",
]
