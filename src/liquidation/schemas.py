"""Pydantic v2 input schemas for the Smart Liquidation Engine (Spec Sections 2, 3, 4, 18, 19)."""

from datetime import datetime
import math
from typing import Annotated, Any, Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

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


def _reject_bool_numeric(value: Any) -> Any:
    """Reject boolean values on numeric fields while preserving int-to-float coercion."""
    if isinstance(value, bool):
        raise ValueError("Numeric field must not be a boolean.")
    return value


def _require_aware_datetime(value: datetime) -> datetime:
    """Require timezone-aware datetimes to prevent naive/aware subtraction errors."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            "Timestamp must be timezone-aware (include an explicit UTC offset or 'Z')."
        )
    return value


BinaryFlag = Annotated[bool, BeforeValidator(_parse_binary_flag)]
StrictFloat = Annotated[float, BeforeValidator(_reject_bool_numeric)]
AwareTimestamp = Annotated[datetime, AfterValidator(_require_aware_datetime)]


class _LiquidationBaseModel(BaseModel):
    """Shared Pydantic v2 configuration for Smart Liquidation Engine schemas."""

    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)


class PortfolioAsset(_LiquidationBaseModel):
    """Input representation of a single portfolio asset for liquidation analysis.

    Attributes map to Spec Section 3 (system inputs per asset), Section 4
    (optional target weight and ``previous_score``), and Section 18
    (optional historical churn-control fields passed in-memory without DB persistence).

    Unresolved Conventions & Assumptions:
        - Monetary values (``current_value``, ``purchase_value``) are non-negative
          and assumed to share a single consistent portfolio currency.
        - ``expected_return`` is expressed over a consistent horizon across all assets
          in the portfolio (may be negative).
        - ``volatility`` is non-negative (``>= 0.0``). The sign and unit convention for
          ``max_drawdown`` (positive magnitude vs. negative drawdown) is unresolved in
          the v1.0 PDF, so negative values are not rejected at schema validation.
        - ``loss_probability`` is in ``[0.0, 1.0]`` as implied by ``1 - LP``.
        - ``tax_rate`` is non-negative (``>= 0.0``); whether external feeds pass
          decimals (``0.15``) or percentages (``15.0``) is unresolved, so no upper
          bound ``<= 1.0`` or automatic ``/ 100`` conversion is applied.
        - ``liquidity`` has no hardcoded upper/lower bound because the v1.0 PDF
          omits the domain bounds for ``L_i``.
        - Feature fields may be ``None`` when upstream ML or market signals are
          unavailable; downstream normalization maps missing features to ``0.5``.
        - All timestamps must be timezone-aware; ``purchase_timestamp`` and
          ``last_sell_timestamp`` cannot be later than ``timestamp``.
    """

    asset_id: str = Field(..., min_length=1, description="Unique asset identifier")
    asset_type: AssetType = Field(..., description="Granular asset type")
    asset_class: AssetClass = Field(..., description="High-level asset class")
    timestamp: AwareTimestamp = Field(
        ...,
        description="Timezone-aware as-of timestamp for asset valuation and signals",
    )

    current_value: StrictFloat = Field(..., ge=0.0, description="Current market value V_i")
    purchase_value: StrictFloat = Field(..., ge=0.0, description="Acquisition cost basis P_i")

    liquidity: Optional[StrictFloat] = Field(
        default=None,
        description="Liquidity score L_i (domain range unspecified in v1.0 spec)",
    )
    expected_return: Optional[StrictFloat] = Field(
        default=None,
        description="Expected future return mu_i over consistent horizon",
    )
    volatility: Optional[StrictFloat] = Field(
        default=None,
        ge=0.0,
        description="Volatility sigma_i (non-negative)",
    )
    max_drawdown: Optional[StrictFloat] = Field(
        default=None,
        description="Maximum drawdown DD_i (sign/unit convention unresolved in v1.0 spec)",
    )
    loss_probability: Optional[StrictFloat] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Predicted loss probability LP_i in [0, 1]",
    )
    tax_rate: Optional[StrictFloat] = Field(
        default=None,
        ge=0.0,
        description="Effective tax rate T_i on realized gain (>= 0; unit convention unresolved)",
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

    previous_score: Optional[StrictFloat] = Field(
        default=None,
        description="Last stored AdjSellScore_i for score stability checks",
    )

    # Optional historical churn-control inputs (Spec Section 18; no DB persistence in Phase 1)
    holding_period_days: Optional[StrictFloat] = Field(
        default=None,
        ge=0.0,
        description="Optional holding duration in days for MinHoldingPeriod check",
    )
    days_since_last_sell: Optional[StrictFloat] = Field(
        default=None,
        ge=0.0,
        description="Optional days elapsed since last sell for CooldownAfterSell check",
    )
    purchase_timestamp: Optional[AwareTimestamp] = Field(
        default=None,
        description="Optional timezone-aware purchase timestamp",
    )
    last_sell_timestamp: Optional[AwareTimestamp] = Field(
        default=None,
        description="Optional timezone-aware timestamp of the most recent sell",
    )

    # Optional per-asset rebalance target weight (Spec Section 4)
    target_weight: Optional[StrictFloat] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional target portfolio weight TargetWeight_i in [0, 1]",
    )

    @model_validator(mode="after")
    def validate_timestamp_chronology(self) -> "PortfolioAsset":
        """Ensure historical purchase/sell timestamps do not post-date asset valuation."""
        if self.purchase_timestamp is not None and self.purchase_timestamp > self.timestamp:
            raise ValueError("purchase_timestamp cannot be later than asset timestamp.")
        if self.last_sell_timestamp is not None and self.last_sell_timestamp > self.timestamp:
            raise ValueError("last_sell_timestamp cannot be later than asset timestamp.")
        return self


class RebalanceInfo(_LiquidationBaseModel):
    """Optional portfolio rebalancing parameters (Spec Sections 4 & 19).

    Target weights may be supplied for a subset of assets or asset classes,
    so individual entries are constrained to ``[0.0, 1.0]`` and map totals may
    be less than or equal to ``1.0``.

    Note:
        Spec Section 19 describes ``RebalanceThreshold`` as ``5-10 percentage points``.
        Because decimal (``0.05``) vs. percentage-point (``5.0``) input units are not
        finalized, ``rebalance_threshold`` only enforces ``>= 0.0`` and performs no
        automatic percentage conversion.
    """

    asset_target_weights: dict[str, StrictFloat] = Field(
        default_factory=dict,
        description="Optional target weights keyed by asset_id in [0, 1]",
    )
    asset_class_target_weights: dict[AssetClass, StrictFloat] = Field(
        default_factory=dict,
        description="Optional target weights keyed by AssetClass in [0, 1]",
    )
    rebalance_threshold: Optional[StrictFloat] = Field(
        default=None,
        ge=0.0,
        description="Optional weight-deviation threshold (>= 0; unit convention unresolved)",
    )

    @field_validator("asset_target_weights", mode="before")
    @classmethod
    def check_asset_target_weight_key_collisions(cls, weights: Any) -> Any:
        """Detect empty or whitespace-colliding keys before Pydantic strips dict keys."""
        if not isinstance(weights, dict):
            return weights
        seen: set[str] = set()
        for asset_id in weights:
            if not isinstance(asset_id, str):
                raise ValueError("Target weight asset_id must be a string.")
            key = asset_id.strip()
            if not key:
                raise ValueError("Target weight asset_id must be non-empty.")
            if key in seen:
                raise ValueError(
                    f"Duplicate asset_id '{key}' in asset_target_weights after whitespace normalization."
                )
            seen.add(key)
        return weights

    @field_validator("asset_target_weights")
    @classmethod
    def validate_asset_target_weights(cls, weights: dict[str, float]) -> dict[str, float]:
        """Validate per-asset target weight keys, bounds, and cumulative sum."""
        cleaned: dict[str, float] = {}
        for asset_id, weight in weights.items():
            key = asset_id.strip()
            if not key:
                raise ValueError("Target weight asset_id must be non-empty.")
            if key in cleaned:
                raise ValueError(
                    f"Duplicate asset_id '{key}' in asset_target_weights after whitespace normalization."
                )
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


class LiquidationRequest(_LiquidationBaseModel):
    """Top-level input payload for a Smart Liquidation Engine evaluation."""

    required_amount: StrictFloat = Field(
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
    def validate_request_consistency(self) -> "LiquidationRequest":
        """Validate unique asset_ids and cross-location target weight consistency."""
        seen: set[str] = set()
        combined_asset_targets: dict[str, float] = (
            dict(self.rebalance.asset_target_weights) if self.rebalance is not None else {}
        )

        for asset in self.assets:
            if asset.asset_id in seen:
                raise ValueError(f"Duplicate asset_id '{asset.asset_id}' in liquidation request.")
            seen.add(asset.asset_id)

            if asset.target_weight is not None:
                existing = combined_asset_targets.get(asset.asset_id)
                if existing is not None and not math.isclose(
                    asset.target_weight, existing, rel_tol=0.0, abs_tol=1e-9
                ):
                    raise ValueError(
                        f"Conflicting target_weight for asset '{asset.asset_id}': "
                        f"asset.target_weight={asset.target_weight} vs "
                        f"rebalance.asset_target_weights={existing}."
                    )
                combined_asset_targets[asset.asset_id] = asset.target_weight

        if sum(combined_asset_targets.values()) > 1.0 + 1e-6:
            raise ValueError("Combined per-asset target weights cannot exceed 1.0.")

        return self
