"""Tests for pure derived calculations in Smart Liquidation Engine (Spec Section 5)."""

from datetime import datetime, timezone
import math

import pytest

import src.liquidation as liquidation_pkg
from src.liquidation.calculations import (
    calculate_adjusted_return,
    calculate_gain,
    calculate_opportunity_cost,
    calculate_risk,
    calculate_tax,
    compute_derived_metrics,
)
from src.liquidation.enums import AssetClass, AssetType
from src.liquidation.exceptions import (
    LiquidationError,
    LiquidationValidationError,
    NoEligibleAssetsError,
    NormalizationError,
    PendingDecisionLogicError,
)
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

    def test_calculate_tax_does_not_auto_convert_or_cap_unconfirmed_units(self):
        assert calculate_tax(1_000.0, 15.0) == pytest.approx(15_000.0)

    def test_calculate_tax_rejects_negative_tax_rate(self):
        with pytest.raises(LiquidationValidationError):
            calculate_tax(1_000.0, -0.01)

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

    def test_calculate_risk_preserves_formula_when_max_drawdown_negative(self):
        # Unresolved DD sign convention: formula 0.5*sigma + 0.5*DD is kept verbatim.
        assert calculate_risk(0.20, -0.10) == pytest.approx(0.05)

    def test_calculate_risk_rejects_negative_volatility(self):
        with pytest.raises(LiquidationValidationError):
            calculate_risk(-0.01, 0.2)

    def test_non_finite_and_boolean_inputs_rejected(self):
        with pytest.raises(LiquidationValidationError):
            calculate_gain(float("nan"), 10.0)
        with pytest.raises(LiquidationValidationError):
            calculate_opportunity_cost(float("inf"), 10.0)
        with pytest.raises(LiquidationValidationError):
            calculate_risk(True, 0.2)
        with pytest.raises(LiquidationValidationError):
            calculate_tax("100", 0.1)
        with pytest.raises(LiquidationValidationError):
            calculate_adjusted_return(None, 0.2)

    def test_arithmetic_overflow_raises_validation_error(self):
        with pytest.raises(LiquidationValidationError):
            calculate_opportunity_cost(1e200, 1e200)
        with pytest.raises(LiquidationValidationError):
            calculate_tax(1e308, 10.0)

    def test_negative_zero_canonicalized_to_positive_zero(self):
        oc = calculate_opportunity_cost(-0.05, 0.0)
        adj = calculate_adjusted_return(-0.0, 0.5)
        tax = calculate_tax(-0.0, 0.2)
        assert oc == 0.0 and math.copysign(1.0, oc) == 1.0
        assert adj == 0.0 and math.copysign(1.0, adj) == 1.0
        assert tax == 0.0 and math.copysign(1.0, tax) == 1.0


class TestPackageExportsAndExceptions:
    """Tests for domain exception hierarchy and public package exports."""

    def test_exception_inheritance(self):
        assert issubclass(LiquidationValidationError, LiquidationError)
        assert issubclass(LiquidationValidationError, ValueError)
        assert issubclass(NormalizationError, LiquidationError)
        assert issubclass(NormalizationError, ValueError)
        assert issubclass(NoEligibleAssetsError, LiquidationError)
        assert issubclass(PendingDecisionLogicError, LiquidationError)
        assert issubclass(PendingDecisionLogicError, NotImplementedError)

    def test_public_exports_match_all(self):
        for symbol in liquidation_pkg.__all__:
            assert hasattr(liquidation_pkg, symbol)


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

