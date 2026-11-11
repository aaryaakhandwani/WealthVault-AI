"""Tests for min-max feature normalization (Spec Section 6)."""

import pytest

from src.liquidation.exceptions import NormalizationError
from src.liquidation.normalization import (
    NEUTRAL_NORMALIZED_VALUE,
    min_max_normalize,
    min_max_normalize_mapping,
)


class TestMinMaxNormalize:
    """Tests for sequence min-max normalization."""

    def test_normal_values_and_boundaries(self):
        result = min_max_normalize([10.0, 20.0, 30.0, 40.0])
        assert result == pytest.approx([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0])

    def test_negative_and_mixed_sign_values(self):
        result = min_max_normalize([-10.0, 0.0, 10.0])
        assert result == pytest.approx([0.0, 0.5, 1.0])

    def test_equal_minimum_and_maximum_returns_neutral(self):
        assert min_max_normalize([5.0, 5.0, 5.0]) == [0.5, 0.5, 0.5]

    def test_single_value_returns_neutral(self):
        assert min_max_normalize([42.0]) == [NEUTRAL_NORMALIZED_VALUE]

    def test_missing_values_mapped_to_neutral_without_affecting_bounds(self):
        result = min_max_normalize([10.0, None, 30.0, None])
        assert result == pytest.approx([0.0, 0.5, 1.0, 0.5])

    def test_all_missing_values_return_neutral(self):
        assert min_max_normalize([None, None, None]) == [0.5, 0.5, 0.5]

    def test_single_present_with_missing_values(self):
        assert min_max_normalize([None, 7.5, None]) == [0.5, 0.5, 0.5]

    def test_empty_input_returns_empty_list(self):
        assert min_max_normalize([]) == []
        assert min_max_normalize(()) == []

    def test_input_sequence_is_not_mutated(self):
        original = [10.0, None, 20.0, 30.0]
        snapshot = list(original)
        result = min_max_normalize(original)
        assert original == snapshot
        assert result is not original

    @pytest.mark.parametrize(
        "bad_values",
        [
            [1.0, float("nan"), 2.0],
            [1.0, float("inf"), 2.0],
            [1.0, float("-inf"), 2.0],
            [True, 1.0],
            ["1.0", 2.0],
        ],
    )
    def test_invalid_values_raise_normalization_error(self, bad_values):
        with pytest.raises(NormalizationError):
            min_max_normalize(bad_values)


class TestMinMaxNormalizeMapping:
    """Tests for dictionary/mapping min-max normalization."""

    def test_mapping_normalization_preserves_keys_and_order(self):
        raw = {"a1": 100.0, "a2": None, "a3": 200.0, "a4": 150.0}
        snapshot = dict(raw)
        result = min_max_normalize_mapping(raw)

        assert list(result.keys()) == ["a1", "a2", "a3", "a4"]
        assert result["a1"] == pytest.approx(0.0)
        assert result["a2"] == pytest.approx(0.5)
        assert result["a3"] == pytest.approx(1.0)
        assert result["a4"] == pytest.approx(0.5)
        assert raw == snapshot

    def test_empty_mapping_returns_empty_dict(self):
        assert min_max_normalize_mapping({}) == {}

    def test_equal_values_mapping_returns_neutral(self):
        assert min_max_normalize_mapping({"a": 3.0, "b": 3.0}) == {"a": 0.5, "b": 0.5}
