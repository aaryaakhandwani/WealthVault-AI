"""Reusable min-max normalization utilities (Spec Section 6)."""

import math
from typing import Mapping, Optional, Sequence, TypeVar

from src.liquidation.exceptions import NormalizationError

NEUTRAL_NORMALIZED_VALUE: float = 0.5

K = TypeVar("K")


def _validate_optional_number(value: Optional[float], index_or_key: object) -> Optional[float]:
    """Validate an optional feature value, returning None or a finite float."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NormalizationError(
            f"Feature value for '{index_or_key}' must be numeric or None, got {type(value).__name__}."
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise NormalizationError(f"Feature value for '{index_or_key}' must be finite.")
    return numeric


def _normalize_validated(validated: list[Optional[float]]) -> list[float]:
    """Apply min-max normalization to a pre-validated list of optional floats."""
    if not validated:
        return []

    present = [v for v in validated if v is not None]
    if not present:
        return [NEUTRAL_NORMALIZED_VALUE] * len(validated)

    min_val = min(present)
    max_val = max(present)
    span = max_val - min_val

    if span == 0.0:
        return [NEUTRAL_NORMALIZED_VALUE] * len(validated)

    return [
        NEUTRAL_NORMALIZED_VALUE if v is None else (v - min_val) / span
        for v in validated
    ]


def min_max_normalize(values: Sequence[Optional[float]]) -> list[float]:
    """Normalize a sequence of feature values to ``[0.0, 1.0]`` via min-max scaling.

    Follows Spec Section 6:
        - Missing entries (``None``) map to ``0.5`` (neutral) and do not affect min/max.
        - If ``max == min`` across present entries, all entries map to ``0.5``.
        - Empty sequences return ``[]``.
        - Input sequences are never mutated.

    Args:
        values: Sequence of numeric feature values or ``None`` for missing features.

    Returns:
        New list of normalized floats in ``[0.0, 1.0]``.

    Raises:
        NormalizationError: If any non-``None`` entry is non-numeric, ``bool``, ``NaN``, or infinite.
    """
    validated = [_validate_optional_number(value, idx) for idx, value in enumerate(values)]
    return _normalize_validated(validated)


def min_max_normalize_mapping(values: Mapping[K, Optional[float]]) -> dict[K, float]:
    """Normalize a mapping of ``{key: feature_value}`` without mutating the input mapping.

    Uses the same Spec Section 6 semantics as :func:`min_max_normalize`.

    Args:
        values: Mapping of identifiers (e.g. ``asset_id``) to optional numeric values.

    Returns:
        New dictionary preserving input key order with normalized float values.
    """
    if not values:
        return {}

    keys = list(values.keys())
    validated = [_validate_optional_number(values[key], key) for key in keys]
    normalized = _normalize_validated(validated)
    return dict(zip(keys, normalized))
