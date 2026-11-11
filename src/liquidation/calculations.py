"""Pure derived-variable calculations for the Smart Liquidation Engine (Spec Section 5).

All functions in this module are pure: they perform no database calls, network I/O,
or hidden state mutations.

Units and Assumptions:
    - ``current_value`` (V) and ``purchase_value`` (P) are non-negative monetary amounts
      in a consistent portfolio currency.
    - ``gain`` (G), ``tax`` (Tax), and ``opportunity_cost`` (OC) are returned in the
      same currency unit as V and P.
    - ``tax_rate`` (T) is a decimal effective tax rate in ``[0.0, 1.0]`` (e.g., ``0.15``
      for 15%). Losses incur zero tax by default (no tax credit).
    - ``expected_return`` (mu) is a decimal expected return over a consistent horizon
      across all assets (can be negative, zero, or positive).
    - ``loss_probability`` (LP) is a decimal probability in ``[0.0, 1.0]``.
    - ``volatility`` (sigma) and ``max_drawdown`` (DD) are non-negative magnitudes
      expressed on the same scale (e.g., decimal ``0.20`` for 20%).
"""

from dataclasses import dataclass
import math
from typing import Optional

from src.liquidation.exceptions import LiquidationValidationError
from src.liquidation.schemas import PortfolioAsset


def _require_finite(value: float, field_name: str) -> float:
    """Validate that a numeric input is a finite real number (not bool, NaN, or inf)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LiquidationValidationError(f"{field_name} must be a real number.")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise LiquidationValidationError(f"{field_name} must be finite.")
    return numeric


def _require_non_negative(value: float, field_name: str) -> float:
    """Validate that a numeric input is finite and >= 0."""
    numeric = _require_finite(value, field_name)
    if numeric < 0.0:
        raise LiquidationValidationError(f"{field_name} must be non-negative.")
    return numeric


def _require_unit_interval(value: float, field_name: str) -> float:
    """Validate that a numeric input is finite and within [0.0, 1.0]."""
    numeric = _require_finite(value, field_name)
    if numeric < 0.0 or numeric > 1.0:
        raise LiquidationValidationError(f"{field_name} must be in [0.0, 1.0].")
    return numeric


def calculate_gain(current_value: float, purchase_value: float) -> float:
    """Compute unrealized gain or loss: ``G = V - P``.

    Args:
        current_value: Current market value ``V`` (>= 0, in currency units).
        purchase_value: Acquisition cost basis ``P`` (>= 0, in currency units).

    Returns:
        Realized/unrealized gain ``G`` in currency units (negative indicates loss).
    """
    v = _require_non_negative(current_value, "current_value")
    p = _require_non_negative(purchase_value, "purchase_value")
    return v - p


def calculate_tax(gain: float, tax_rate: float) -> float:
    """Compute tax on realized gain: ``Tax = max(0, G) * T``.

    No tax credit is applied to negative gains (losses) by default per Spec Section 5.

    Args:
        gain: Gain ``G`` in currency units (may be negative).
        tax_rate: Effective decimal tax rate ``T`` in ``[0.0, 1.0]``.

    Returns:
        Non-negative tax liability in currency units.
    """
    g = _require_finite(gain, "gain")
    t = _require_unit_interval(tax_rate, "tax_rate")
    return max(0.0, g) * t


def calculate_opportunity_cost(expected_return: float, current_value: float) -> float:
    """Compute opportunity cost of selling: ``OC = mu * V``.

    Represents the expected absolute value change over the return horizon if held.

    Args:
        expected_return: Expected decimal return ``mu`` over a consistent horizon.
        current_value: Current market value ``V`` (>= 0, in currency units).

    Returns:
        Expected opportunity cost in currency units (negative if ``mu < 0``).
    """
    mu = _require_finite(expected_return, "expected_return")
    v = _require_non_negative(current_value, "current_value")
    return mu * v


def calculate_adjusted_return(expected_return: float, loss_probability: float) -> float:
    """Compute risk-adjusted expected return: ``AdjReturn = mu * (1 - LP)``.

    Args:
        expected_return: Expected decimal return ``mu`` over a consistent horizon.
        loss_probability: Probability of loss ``LP`` in ``[0.0, 1.0]``.

    Returns:
        Risk-adjusted expected return (same unit/horizon as ``expected_return``).
    """
    mu = _require_finite(expected_return, "expected_return")
    lp = _require_unit_interval(loss_probability, "loss_probability")
    return mu * (1.0 - lp)


def calculate_risk(volatility: float, max_drawdown: float) -> float:
    """Compute composite asset risk: ``Risk = 0.5 * sigma + 0.5 * DD``.

    Args:
        volatility: Volatility ``sigma`` (>= 0).
        max_drawdown: Maximum drawdown magnitude ``DD`` (>= 0).

    Returns:
        Equal-weighted composite risk on the same scale as inputs.
    """
    sigma = _require_non_negative(volatility, "volatility")
    dd = _require_non_negative(max_drawdown, "max_drawdown")
    return 0.5 * sigma + 0.5 * dd


@dataclass(frozen=True)
class DerivedAssetMetrics:
    """Derived variables computed for a single ``PortfolioAsset`` (Spec Section 5).

    Fields evaluate to ``None`` when any underlying optional asset input is missing,
    allowing downstream min-max normalization to map missing features to ``0.5``.
    """

    asset_id: str
    gain: float
    tax: Optional[float]
    opportunity_cost: Optional[float]
    adjusted_return: Optional[float]
    risk: Optional[float]


def compute_derived_metrics(asset: PortfolioAsset) -> DerivedAssetMetrics:
    """Compute all available Spec Section 5 derived variables for a ``PortfolioAsset``."""
    gain = calculate_gain(asset.current_value, asset.purchase_value)
    tax = calculate_tax(gain, asset.tax_rate) if asset.tax_rate is not None else None
    opportunity_cost = (
        calculate_opportunity_cost(asset.expected_return, asset.current_value)
        if asset.expected_return is not None
        else None
    )
    adjusted_return = (
        calculate_adjusted_return(asset.expected_return, asset.loss_probability)
        if asset.expected_return is not None and asset.loss_probability is not None
        else None
    )
    risk = (
        calculate_risk(asset.volatility, asset.max_drawdown)
        if asset.volatility is not None and asset.max_drawdown is not None
        else None
    )

    return DerivedAssetMetrics(
        asset_id=asset.asset_id,
        gain=gain,
        tax=tax,
        opportunity_cost=opportunity_cost,
        adjusted_return=adjusted_return,
        risk=risk,
    )
