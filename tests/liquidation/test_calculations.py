"""Tests for pure derived calculations in Smart Liquidation Engine (Spec Section 5)."""

from datetime import datetime, timezone

import pytest

from src.liquidation.calculations import (
    calculate_adjusted_return,
    calculate_gain,
    calculate_opportunity_cost,
    calculate_risk,
    calculate_tax,
    compute_derived_metrics,
)
from src.liquidation.enums import AssetClass, AssetType
from src.liquidation.exceptions import LiquidationValidationError
from src.liquidation.schemas import PortfolioAsset


class TestDerivedCalculations:
    """Unit tests for individual pure Spec Section 5 functions."""

    def test_calculate_gain_positive_zero_and_negative(self):
        assert calculate_gain(120_000.0, 100_000.0) == pytest.approx(20_000.0)
        assert calculate_gain(100_000.0, 100_000.0) == pytest.approx(0.0)
        assert calculate_gain(75_000.0, 100_000.0) == pytest.approx(-25_000.0)

    def test_calculate_gain_rejects_negative_monetary_values(self):
        with pytest.raises(LiquidationValidationError):
            calculate_gain(-1.0, 100.0)
        with pytest.raises(LiquidationValidationError):
            calculate_gain(100.0, -1.0)

    def test_calculate_tax_only_applies_to_positive_gains(self):
        assert calculate_tax(20_000.0, 0.15) == pytest.approx(3_000.0)
        assert calculate_tax(0.0, 0.20) == pytest.approx(0.0)
        assert calculate_tax(-15_000.0, 0.30) == pytest.approx(0.0)

    def test_calculate_tax_rejects_invalid_tax_rate(self):
        with pytest.raises(LiquidationValidationError):
            calculate_tax(1_000.0, -0.01)
        with pytest.raises(LiquidationValidationError):
            calculate_tax(1_000.0, 1.01)

    def test_calculate_opportunity_cost(self):
        assert calculate_opportunity_cost(0.12, 50_000.0) == pytest.approx(6_000.0)
        assert calculate_opportunity_cost(0.0, 50_000.0) == pytest.approx(0.0)
        assert calculate_opportunity_cost(-0.05, 50_000.0) == pytest.approx(-2_500.0)

    def test_calculate_opportunity_cost_rejects_negative_value(self):
        with pytest.raises(LiquidationValidationError):
            calculate_opportunity_cost(0.10, -500.0)

    def test_calculate_adjusted_return(self):
        assert calculate_adjusted_return(0.10, 0.25) == pytest.approx(0.075)
        assert calculate_adjusted_return(0.10, 0.0) == pytest.approx(0.10)
        assert calculate_adjusted_return(0.10, 1.0) == pytest.approx(0.0)
        assert calculate_adjusted_return(-0.08, 0.25) == pytest.approx(-0.06)

    def test_calculate_adjusted_return_rejects_invalid_loss_probability(self):
        with pytest.raises(LiquidationValidationError):
            calculate_adjusted_return(0.10, -0.1)
        with pytest.raises(LiquidationValidationError):
            calculate_adjusted_return(0.10, 1.1)

    def test_calculate_risk(self):
        assert calculate_risk(0.20, 0.30) == pytest.approx(0.25)
        assert calculate_risk(0.0, 0.0) == pytest.approx(0.0)

    def test_calculate_risk_rejects_negative_inputs(self):
        with pytest.raises(LiquidationValidationError):
            calculate_risk(-0.01, 0.2)
        with pytest.raises(LiquidationValidationError):
            calculate_risk(0.2, -0.01)

    def test_non_finite_and_boolean_inputs_rejected(self):
        with pytest.raises(LiquidationValidationError):
            calculate_gain(float("nan"), 10.0)
        with pytest.raises(LiquidationValidationError):
            calculate_opportunity_cost(float("inf"), 10.0)
        with pytest.raises(LiquidationValidationError):
            calculate_risk(True, 0.2)


class TestComputeDerivedMetrics:
    """Tests for asset-level derived metrics helper."""

    def test_compute_derived_metrics_complete_asset(self):
        asset = PortfolioAsset(
            asset_id="eq-1",
            asset_type=AssetType.STOCK,
            asset_class=AssetClass.EQUITY,
            timestamp=datetime(2026, 11, 1, tzinfo=timezone.utc),
            current_value=120_000.0,
            purchase_value=100_000.0,
            expected_return=0.12,
            volatility=0.20,
            max_drawdown=0.30,
            loss_probability=0.25,
            tax_rate=0.15,
            lock_in=0,
            maturity=0,
            sell_allowed=1,
        )
        metrics = compute_derived_metrics(asset)
        assert metrics.asset_id == "eq-1"
        assert metrics.gain == pytest.approx(20_000.0)
        assert metrics.tax == pytest.approx(3_000.0)
        assert metrics.opportunity_cost == pytest.approx(14_400.0)
        assert metrics.adjusted_return == pytest.approx(0.09)
        assert metrics.risk == pytest.approx(0.25)

    def test_compute_derived_metrics_with_missing_optional_inputs(self):
        asset = PortfolioAsset(
            asset_id="gold-1",
            asset_type=AssetType.GOLD,
            asset_class=AssetClass.GOLD,
            timestamp=datetime(2026, 11, 1, tzinfo=timezone.utc),
            current_value=40_000.0,
            purchase_value=50_000.0,
            lock_in=0,
            maturity=0,
            sell_allowed=1,
        )
        metrics = compute_derived_metrics(asset)
        assert metrics.gain == pytest.approx(-10_000.0)
        assert metrics.tax is None
        assert metrics.opportunity_cost is None
        assert metrics.adjusted_return is None
        assert metrics.risk is None
