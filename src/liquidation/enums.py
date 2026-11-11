"""Enumerations for the Smart Liquidation Engine (Specification Section 1)."""

from enum import Enum


class AssetType(str, Enum):
    """Supported granular asset types in the Smart Liquidation Engine."""

    STOCK = "stock"
    MF = "MF"
    GOLD = "gold"
    FD = "FD"
    BOND = "bond"
    REAL_ESTATE = "real_estate"
    CASH = "cash"


class AssetClass(str, Enum):
    """Supported high-level asset classes for portfolio allocation and caps."""

    EQUITY = "equity"
    DEBT = "debt"
    GOLD = "gold"
    REAL_ESTATE = "real_estate"
    CASH = "cash"


class MarketState(str, Enum):
    """Macro market regime states used for liquidation weight adaptation."""

    RISK_ON = "RISK_ON"
    NEUTRAL = "NEUTRAL"
    RISK_OFF = "RISK_OFF"
