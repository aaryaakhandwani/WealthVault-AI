"""Domain exceptions for the Smart Liquidation Engine."""


class LiquidationError(Exception):
    """Base exception for all Smart Liquidation Engine errors."""


class LiquidationValidationError(LiquidationError, ValueError):
    """Raised when liquidation inputs fail domain validation."""


class NormalizationError(LiquidationError, ValueError):
    """Raised when feature normalization encounters invalid numeric inputs."""


class NoEligibleAssetsError(LiquidationError):
    """Raised when no portfolio assets are eligible for liquidation."""


class PendingDecisionLogicError(LiquidationError, NotImplementedError):
    """Raised when invoking Phase 2 decision logic pending product sign-off."""
