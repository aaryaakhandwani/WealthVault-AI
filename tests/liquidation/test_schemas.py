"""Tests for Smart Liquidation Engine enums and Pydantic input schemas."""

from datetime import datetime, timedelta, timezone
import json

import pytest
from pydantic import ValidationError

from src.liquidation.enums import AssetClass, AssetType, MarketState
from src.liquidation.schemas import LiquidationRequest, PortfolioAsset, RebalanceInfo


def _make_asset_payload(**overrides):
    """Build a valid PortfolioAsset payload with optional field overrides."""
    payload = {
        "asset_id": "asset-1",
        "asset_type": AssetType.STOCK,
        "asset_class": AssetClass.EQUITY,
        "timestamp": datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc),
        "current_value": 100_000.0,
        "purchase_value": 80_000.0,
        "liquidity": 0.9,
        "expected_return": 0.12,
        "volatility": 0.18,
        "max_drawdown": 0.25,
        "loss_probability": 0.2,
        "tax_rate": 0.15,
        "lock_in": 0,
        "maturity": 0,
        "sell_allowed": 1,
        "previous_score": 0.45,
        "holding_period_days": 120.0,
        "days_since_last_sell": 30.0,
    }
    payload.update(overrides)
    return payload


class TestEnums:
    """Tests for enum values and JSON/string serialization."""

    def test_asset_type_values_and_serialization(self):
        expected = {
            AssetType.STOCK: "stock",
            AssetType.MF: "MF",
            AssetType.GOLD: "gold",
            AssetType.FD: "FD",
            AssetType.BOND: "bond",
            AssetType.REAL_ESTATE: "real_estate",
            AssetType.CASH: "cash",
        }
        assert len(AssetType) == len(expected)
        for member, raw in expected.items():
            assert member.value == raw
            assert json.loads(json.dumps(member)) == raw
            assert AssetType(raw) is member

    def test_asset_class_values_and_serialization(self):
        expected = {
            AssetClass.EQUITY: "equity",
            AssetClass.DEBT: "debt",
            AssetClass.GOLD: "gold",
            AssetClass.REAL_ESTATE: "real_estate",
            AssetClass.CASH: "cash",
        }
        assert len(AssetClass) == len(expected)
        for member, raw in expected.items():
            assert member.value == raw
            assert json.loads(json.dumps(member)) == raw
            assert AssetClass(raw) is member

    def test_market_state_values_and_serialization(self):
        expected = {
            MarketState.RISK_ON: "RISK_ON",
            MarketState.NEUTRAL: "NEUTRAL",
            MarketState.RISK_OFF: "RISK_OFF",
        }
        assert len(MarketState) == len(expected)
        for member, raw in expected.items():
            assert member.value == raw
            assert json.loads(json.dumps(member)) == raw
            assert MarketState(raw) is member


class TestPortfolioAssetSchema:
    """Tests for PortfolioAsset validation rules and optional fields."""

    def test_valid_full_asset_and_json_roundtrip(self):
        asset = PortfolioAsset(**_make_asset_payload())
        assert asset.asset_id == "asset-1"
        assert asset.asset_type is AssetType.STOCK
        assert asset.asset_class is AssetClass.EQUITY
        assert asset.lock_in is False
        assert asset.maturity is False
        assert asset.sell_allowed is True

        dumped = asset.model_dump(mode="json")
        assert dumped["asset_type"] == "stock"
        assert dumped["asset_class"] == "equity"
        restored = PortfolioAsset.model_validate(dumped)
        assert restored == asset

    def test_missing_optional_fields_default_to_none(self):
        minimal_payload = {
            "asset_id": "fd-01",
            "asset_type": "FD",
            "asset_class": "debt",
            "timestamp": "2026-11-01T10:00:00Z",
            "current_value": 50_000.0,
            "purchase_value": 50_000.0,
            "lock_in": True,
            "maturity": 1,
            "sell_allowed": 0,
        }
        asset = PortfolioAsset(**minimal_payload)
        assert asset.asset_type is AssetType.FD
        assert asset.asset_class is AssetClass.DEBT
        assert asset.liquidity is None
        assert asset.expected_return is None
        assert asset.volatility is None
        assert asset.max_drawdown is None
        assert asset.loss_probability is None
        assert asset.tax_rate is None
        assert asset.previous_score is None
        assert asset.holding_period_days is None
        assert asset.days_since_last_sell is None
        assert asset.purchase_timestamp is None
        assert asset.last_sell_timestamp is None
        assert asset.target_weight is None
        assert asset.lock_in is True
        assert asset.maturity is True
        assert asset.sell_allowed is False

    def test_negative_expected_return_and_previous_score_allowed(self):
        asset = PortfolioAsset(
            **_make_asset_payload(expected_return=-0.08, previous_score=-0.05)
        )
        assert asset.expected_return == -0.08
        assert asset.previous_score == -0.05

    def test_unbounded_liquidity_and_unconfirmed_conventions_not_over_locked(self):
        # Negative max_drawdown, tax_rate > 1 (e.g. percentage feed), and unbounded liquidity
        # are not rejected or auto-converted while conventions remain unresolved.
        asset = PortfolioAsset(
            **_make_asset_payload(liquidity=85.0, max_drawdown=-0.25, tax_rate=15.0)
        )
        assert asset.liquidity == 85.0
        assert asset.max_drawdown == -0.25
        assert asset.tax_rate == 15.0

    def test_integer_values_coerce_to_float(self):
        asset = PortfolioAsset(
            **_make_asset_payload(
                current_value=100_000,
                purchase_value=80_000,
                liquidity=1,
                expected_return=0,
                volatility=0,
                max_drawdown=0,
                loss_probability=0,
                tax_rate=0,
                previous_score=1,
                holding_period_days=14,
                days_since_last_sell=7,
                target_weight=1,
            )
        )
        assert asset.current_value == 100_000.0
        assert isinstance(asset.current_value, float)
        assert asset.target_weight == 1.0

    @pytest.mark.parametrize(
        "field",
        [
            "current_value",
            "purchase_value",
            "liquidity",
            "expected_return",
            "volatility",
            "max_drawdown",
            "loss_probability",
            "tax_rate",
            "previous_score",
            "holding_period_days",
            "days_since_last_sell",
            "target_weight",
        ],
    )
    @pytest.mark.parametrize("bool_val", [True, False])
    def test_boolean_rejected_in_all_asset_float_fields(self, field, bool_val):
        with pytest.raises(ValidationError):
            PortfolioAsset(**_make_asset_payload(**{field: bool_val}))

    @pytest.mark.parametrize("field", ["current_value", "purchase_value"])
    def test_negative_monetary_values_rejected(self, field):
        with pytest.raises(ValidationError):
            PortfolioAsset(**_make_asset_payload(**{field: -0.01}))

    @pytest.mark.parametrize(
        "missing_field",
        [
            "asset_id",
            "asset_type",
            "asset_class",
            "timestamp",
            "current_value",
            "purchase_value",
            "lock_in",
            "maturity",
            "sell_allowed",
        ],
    )
    def test_missing_required_asset_fields_rejected(self, missing_field):
        payload = _make_asset_payload()
        del payload[missing_field]
        with pytest.raises(ValidationError):
            PortfolioAsset(**payload)

    def test_naive_timestamps_rejected(self):
        naive = datetime(2026, 11, 1, 12, 0)
        with pytest.raises(ValidationError):
            PortfolioAsset(**_make_asset_payload(timestamp=naive))
        with pytest.raises(ValidationError):
            PortfolioAsset(**_make_asset_payload(purchase_timestamp=naive))
        with pytest.raises(ValidationError):
            PortfolioAsset(**_make_asset_payload(last_sell_timestamp=naive))

    def test_timestamp_chronology_validation(self):
        as_of = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
        earlier = as_of - timedelta(days=10)
        later = as_of + timedelta(minutes=1)
        ist_offset = timezone(timedelta(hours=5, minutes=30))

        # Valid chronology across mixed timezone offsets
        valid = PortfolioAsset(
            **_make_asset_payload(
                timestamp=as_of,
                purchase_timestamp=earlier.astimezone(ist_offset),
                last_sell_timestamp=as_of.astimezone(ist_offset),
            )
        )
        assert valid.purchase_timestamp is not None

        with pytest.raises(ValidationError):
            PortfolioAsset(**_make_asset_payload(timestamp=as_of, purchase_timestamp=later))
        with pytest.raises(ValidationError):
            PortfolioAsset(**_make_asset_payload(timestamp=as_of, last_sell_timestamp=later))

    @pytest.mark.parametrize(
        "overrides",
        [
            {"asset_id": ""},
            {"asset_id": "   "},
            {"asset_type": "crypto"},
            {"asset_class": "derivatives"},
            {"volatility": -0.1},
            {"loss_probability": -0.01},
            {"loss_probability": 1.01},
            {"tax_rate": -0.01},
            {"lock_in": 2},
            {"maturity": -1},
            {"sell_allowed": "maybe"},
            {"holding_period_days": -1.0},
            {"days_since_last_sell": -0.5},
            {"target_weight": -0.1},
            {"target_weight": 1.1},
            {"current_value": float("nan")},
            {"purchase_value": float("inf")},
        ],
    )
    def test_invalid_asset_inputs_rejected(self, overrides):
        with pytest.raises(ValidationError):
            PortfolioAsset(**_make_asset_payload(**overrides))


class TestLiquidationRequestSchema:
    """Tests for LiquidationRequest and RebalanceInfo schemas."""

    def test_valid_request_without_rebalance(self):
        request = LiquidationRequest(
            required_amount=25_000.0,
            urgency_days=5,
            market_state="RISK_OFF",
            assets=[PortfolioAsset(**_make_asset_payload())],
        )
        assert request.market_state is MarketState.RISK_OFF
        assert request.rebalance is None
        assert request.model_dump(mode="json")["market_state"] == "RISK_OFF"

    def test_valid_request_with_partial_rebalance_targets(self):
        rebalance = RebalanceInfo(
            asset_target_weights={"asset-1": 0.40},
            asset_class_target_weights={AssetClass.EQUITY: 0.60, AssetClass.DEBT: 0.30},
            rebalance_threshold=0.05,
        )
        request = LiquidationRequest(
            required_amount=0.0,
            urgency_days=0,
            market_state=MarketState.NEUTRAL,
            assets=[
                PortfolioAsset(**_make_asset_payload(asset_id="asset-1")),
                PortfolioAsset(
                    **_make_asset_payload(
                        asset_id="asset-2",
                        asset_type=AssetType.MF,
                        asset_class=AssetClass.DEBT,
                    )
                ),
            ],
            rebalance=rebalance,
        )
        assert request.required_amount == 0.0
        assert request.rebalance is not None
        assert request.rebalance.rebalance_threshold == 0.05

    def test_negative_required_amount_rejected(self):
        with pytest.raises(ValidationError):
            LiquidationRequest(
                required_amount=-100.0,
                urgency_days=3,
                market_state=MarketState.RISK_ON,
                assets=[PortfolioAsset(**_make_asset_payload())],
            )

    @pytest.mark.parametrize("urgency", [-1, True, 3.5])
    def test_invalid_urgency_days_rejected(self, urgency):
        with pytest.raises(ValidationError):
            LiquidationRequest(
                required_amount=1_000.0,
                urgency_days=urgency,
                market_state=MarketState.RISK_ON,
                assets=[PortfolioAsset(**_make_asset_payload())],
            )

    def test_duplicate_asset_ids_rejected(self):
        with pytest.raises(ValidationError):
            LiquidationRequest(
                required_amount=1_000.0,
                urgency_days=3,
                market_state=MarketState.NEUTRAL,
                assets=[
                    PortfolioAsset(**_make_asset_payload(asset_id="dup-1")),
                    PortfolioAsset(**_make_asset_payload(asset_id=" dup-1 ")),
                ],
            )

    def test_rebalance_duplicate_stripped_asset_keys_rejected(self):
        with pytest.raises(ValidationError):
            RebalanceInfo(asset_target_weights={"a1": 0.4, " a1 ": 0.3})

        raw_json = json.dumps({"asset_target_weights": {"a1": 0.4, " a1 ": 0.3}})
        with pytest.raises(ValidationError):
            RebalanceInfo.model_validate_json(raw_json)

    def test_rebalance_boolean_and_invalid_values_rejected(self):
        with pytest.raises(ValidationError):
            RebalanceInfo(asset_target_weights={"a1": True})
        with pytest.raises(ValidationError):
            RebalanceInfo(asset_class_target_weights={AssetClass.EQUITY: False})
        with pytest.raises(ValidationError):
            RebalanceInfo(rebalance_threshold=True)
        with pytest.raises(ValidationError):
            RebalanceInfo(rebalance_threshold=-0.01)
        with pytest.raises(ValidationError):
            RebalanceInfo(asset_target_weights={"   ": 0.2})
        with pytest.raises(ValidationError):
            RebalanceInfo(asset_target_weights={"a1": -0.1})
        with pytest.raises(ValidationError):
            RebalanceInfo(asset_target_weights={"a1": 1.1})

    def test_rebalance_threshold_accepts_unconfirmed_percentage_point_units(self):
        # Spec Section 19 mentions "5-10 percentage points" without fixing decimal vs pp.
        rebalance = RebalanceInfo(rebalance_threshold=5.0)
        assert rebalance.rebalance_threshold == 5.0

    def test_rebalance_weight_sum_exceeding_one_rejected(self):
        with pytest.raises(ValidationError):
            RebalanceInfo(asset_target_weights={"a1": 0.7, "a2": 0.4})

        with pytest.raises(ValidationError):
            RebalanceInfo(
                asset_class_target_weights={
                    AssetClass.EQUITY: 0.8,
                    AssetClass.GOLD: 0.3,
                }
            )

    def test_boolean_required_amount_rejected_and_int_accepted(self):
        with pytest.raises(ValidationError):
            LiquidationRequest(
                required_amount=True,
                urgency_days=3,
                market_state=MarketState.RISK_ON,
                assets=[PortfolioAsset(**_make_asset_payload())],
            )

        req = LiquidationRequest(
            required_amount=5_000,
            urgency_days=3,
            market_state=MarketState.RISK_ON,
            assets=[PortfolioAsset(**_make_asset_payload())],
        )
        assert req.required_amount == 5_000.0
        assert isinstance(req.required_amount, float)

    def test_conflicting_target_weights_rejected_and_matching_accepted(self):
        with pytest.raises(ValidationError):
            LiquidationRequest(
                required_amount=1_000.0,
                urgency_days=3,
                market_state=MarketState.NEUTRAL,
                assets=[PortfolioAsset(**_make_asset_payload(asset_id="a1", target_weight=0.25))],
                rebalance=RebalanceInfo(asset_target_weights={"a1": 0.50}),
            )

        with pytest.raises(ValidationError):
            LiquidationRequest(
                required_amount=1_000.0,
                urgency_days=3,
                market_state=MarketState.NEUTRAL,
                assets=[
                    PortfolioAsset(**_make_asset_payload(asset_id="a1", target_weight=0.60)),
                    PortfolioAsset(**_make_asset_payload(asset_id="a2")),
                ],
                rebalance=RebalanceInfo(asset_target_weights={"a2": 0.50}),
            )

        valid = LiquidationRequest(
            required_amount=1_000.0,
            urgency_days=3,
            market_state=MarketState.NEUTRAL,
            assets=[PortfolioAsset(**_make_asset_payload(asset_id="a1", target_weight=0.40))],
            rebalance=RebalanceInfo(asset_target_weights={"a1": 0.40}),
        )
        assert valid.assets[0].target_weight == 0.40

    def test_empty_portfolio_schema_accepted_pending_phase_2_decision(self):
        # Empty portfolio handling (HOLD vs validation error) is a Phase 2 decision;
        # Phase 1 schema accepts an explicit empty list without imposing an undocumented rule.
        request = LiquidationRequest(
            required_amount=1_000.0,
            urgency_days=3,
            market_state=MarketState.NEUTRAL,
            assets=[],
        )
        assert request.assets == []

    @pytest.mark.parametrize(
        "missing_field",
        ["required_amount", "urgency_days", "market_state", "assets"],
    )
    def test_missing_required_request_fields_rejected(self, missing_field):
        payload = {
            "required_amount": 1_000.0,
            "urgency_days": 3,
            "market_state": "NEUTRAL",
            "assets": [_make_asset_payload()],
        }
        del payload[missing_field]
        with pytest.raises(ValidationError):
            LiquidationRequest(**payload)

    def test_json_model_validation_roundtrip_and_json_boolean_rejection(self):
        raw_json = json.dumps(
            {
                "required_amount": 10_000,
                "urgency_days": 2,
                "market_state": "RISK_ON",
                "assets": [
                    {
                        "asset_id": "eq-1",
                        "asset_type": "stock",
                        "asset_class": "equity",
                        "timestamp": "2026-11-01T12:00:00Z",
                        "current_value": 50_000,
                        "purchase_value": 40_000,
                        "lock_in": 0,
                        "maturity": 0,
                        "sell_allowed": 1,
                    }
                ],
            }
        )
        parsed = LiquidationRequest.model_validate_json(raw_json)
        assert parsed.required_amount == 10_000.0
        assert parsed.assets[0].asset_type is AssetType.STOCK

        bad_json = raw_json.replace('"current_value": 50000', '"current_value": true')
        with pytest.raises(ValidationError):
            LiquidationRequest.model_validate_json(bad_json)

