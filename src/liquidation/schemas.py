"""Pydantic v2 input schemas for the Smart Liquidation Engine (Spec Sections 2, 3, 4, 18, 19)."""

from datetime import datetime
from typing import Annotated, Any, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from src.liquidation.enums import AssetClass, AssetType, MarketState


def _parse_binary_flag(value: Any) -> bool:
    """Parse binary specification flags ({0, 1} or bool) without accepting arbitrary values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true"}:
            return True
        if normalized in {"0", "false"}:
            return False
    raise ValueError("Binary flag must be a boolean or integer 0/1.")


BinaryFlag = Annotated[bool, BeforeValidator(_parse_binary_flag)]


class PortfolioAsset(BaseModel):
    """Input representation of a single portfolio asset for liquidation analysis.

    Attributes map to Spec Section 3 (system inputs per asset), Section 4
    (optional target weight and ``previous_score``), and Section 18
    (optional historical churn-control fields passed in-memory without DB persistence).

    Assumptions:
        - Monetary values (``current_value``, ``purchase_value``) are non-negative
          and denominated in a single consistent portfolio currency.
        - ``expected_return`` is expressed as a decimal return over a consistent
          horizon across all assets in the portfolio (may be negative).
        - ``volatility`` and ``max_drawdown`` are non-negative magnitudes on a
          consistent scale; ``max_drawdown`` uses positive magnitude convention
          matching ``Risk = 0.5 * sigma + 0.5 * DD``.
        - ``loss_probability`` and ``tax_rate`` are decimals in ``[0.0, 1.0]``.
        - ``liquidity`` has no hardcoded upper/lower bound because the v1.0 PDF
          omits the domain bounds for ``L_i``.
        - Feature fields may be ``None`` when upstream ML or market signals are
          unavailable; downstream normalization maps missing features to ``0.5``.
    """

    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    asset_id: str = Field(..., min_length=1, description="Unique asset identifier")
    asset_type: AssetType = Field(..., description="Granular asset type")
    asset_class: AssetClass = Field(..., description="High-level asset class")
    timestamp: datetime = Field(..., description="As-of timestamp for asset valuation and signals")

    current_value: float = Field(..., ge=0.0, description="Current market value V_i")
    purchase_value: float = Field(..., ge=0.0, description="Acquisition cost basis P_i")

    liquidity: Optional[float] = Field(
        default=None,
        description="Liquidity score L_i (domain range unspecified in v1.0 spec)",
    )
    expected_return: Optional[float] = Field(
        default=None,
        description="Expected future return mu_i over consistent horizon (decimal)",
    )
    volatility: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Volatility sigma_i (non-negative)",
    )
    max_drawdown: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum drawdown magnitude DD_i (non-negative)",
    )
    loss_probability: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Predicted loss probability LP_i in [0, 1]",
    )
    tax_rate: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Effective tax rate T_i on realized gain in [0, 1]",
    )

    lock_in: BinaryFlag = Field(
        ...,
        description="Lock-in flag LC_i (True/1 = locked, cannot sell)",
    )
    maturity: BinaryFlag = Field(
        ...,
        description="Maturity flag MC_i (True/1 = not yet matured, cannot sell)",
    )
    sell_allowed: BinaryFlag = Field(
        ...,
        description="Sell allowed flag SA_i (True/1 = allowed, False/0 = blocked)",
    )

    previous_score: Optional[float] = Field(
        default=None,
        description="Last stored AdjSellScore_i for score stability checks",
    )

    # Optional historical churn-control inputs (Spec Section 18; no DB persistence in Phase 1)
    holding_period_days: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Optional holding duration in days for MinHoldingPeriod check",
    )
    days_since_last_sell: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Optional days elapsed since last sell for CooldownAfterSell check",
    )
    purchase_timestamp: Optional[datetime] = Field(
        default=None,
        description="Optional purchase timestamp used when holding_period_days is not precomputed",
    )
    last_sell_timestamp: Optional[datetime] = Field(
        default=None,
        description="Optional timestamp of the most recent sell in this asset",
    )

    # Optional per-asset rebalance target weight (Spec Section 4)
    target_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional target portfolio weight TargetWeight_i in [0, 1]",
    )


class RebalanceInfo(BaseModel):
    """Optional portfolio rebalancing parameters (Spec Sections 4 & 19).

    Target weights may be supplied for a subset of assets or asset classes,
    so individual entries are constrained to ``[0.0, 1.0]`` and map totals may
    be less than or equal to ``1.0``.
    """

    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    asset_target_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Optional target weights keyed by asset_id in [0, 1]",
    )
    asset_class_target_weights: dict[AssetClass, float] = Field(
        default_factory=dict,
        description="Optional target weights keyed by AssetClass in [0, 1]",
    )
    rebalance_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional weight-deviation threshold as a decimal fraction",
    )

    @field_validator("asset_target_weights")
    @classmethod
    def validate_asset_target_weights(cls, weights: dict[str, float]) -> dict[str, float]:
        """Validate per-asset target weight keys, bounds, and cumulative sum."""
        cleaned: dict[str, float] = {}
        for asset_id, weight in weights.items():
            key = asset_id.strip()
            if not key:
                raise ValueError("Target weight asset_id must be non-empty.")
            if weight < 0.0 or weight > 1.0:
                raise ValueError(f"Target weight for asset '{key}' must be in [0.0, 1.0].")
            cleaned[key] = weight
        if sum(cleaned.values()) > 1.0 + 1e-6:
            raise ValueError("Sum of asset_target_weights cannot exceed 1.0.")
        return cleaned

    @field_validator("asset_class_target_weights")
    @classmethod
    def validate_asset_class_target_weights(
        cls, weights: dict[AssetClass, float]
    ) -> dict[AssetClass, float]:
        """Validate per-asset-class target weight bounds and cumulative sum."""
        for asset_class, weight in weights.items():
            if weight < 0.0 or weight > 1.0:
                raise ValueError(
                    f"Target weight for asset class '{asset_class.value}' must be in [0.0, 1.0]."
                )
        if sum(weights.values()) > 1.0 + 1e-6:
            raise ValueError("Sum of asset_class_target_weights cannot exceed 1.0.")
        return weights


class LiquidationRequest(BaseModel):
    """Top-level input payload for a Smart Liquidation Engine evaluation."""

    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    required_amount: float = Field(
        ...,
        ge=0.0,
        description="Required liquidation amount R in currency units (0 allowed per Spec Section 19)",
    )
    urgency_days: int = Field(
        ...,
        ge=0,
        description="Time urgency TU in integer days",
    )
    market_state: MarketState = Field(
        ...,
        description="Current macro market state",
    )
    assets: list[PortfolioAsset] = Field(
        ...,
        description="Portfolio assets considered for liquidation",
    )
    rebalance: Optional[RebalanceInfo] = Field(
        default=None,
        description="Optional rebalancing targets and threshold",
    )

    @field_validator("urgency_days", mode="before")
    @classmethod
    def reject_boolean_urgency(cls, value: Any) -> Any:
        """Reject boolean values so True/False are not silently coerced to 1/0 days."""
        if isinstance(value, bool):
            raise ValueError("urgency_days must be an integer, not a boolean.")
        return value

    @model_validator(mode="after")
    def validate_unique_asset_ids(self) -> "LiquidationRequest":
        """Ensure all assets in a single request have distinct asset_id values."""
        seen: set[str] = set()
        for asset in self.assets:
            if asset.asset_id in seen:
                raise ValueError(f"Duplicate asset_id '{asset.asset_id}' in liquidation request.")
            seen.add(asset.asset_id)
        return self
