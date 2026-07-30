"""SQLAlchemy models. Importing this package registers every table on ``Base.metadata``."""

from ..db.base import Base
from .appraisal import Appraisal, CostItem, MarketComparable, RiskAssessment
from .audit import AuditLog
from .catalogue import (
    AuctionFeeBand,
    AuctionHouse,
    AuctionListing,
    Vehicle,
    VehicleHistory,
)
from .organisation import Dealership, RefreshToken, User
from .storefront import BuyerBrief, Enquiry, SaleListing
from .trading import PreparationCost, Purchase, Sale

__all__ = [
    "Base",
    "Dealership",
    "User",
    "RefreshToken",
    "AuctionHouse",
    "AuctionFeeBand",
    "Vehicle",
    "VehicleHistory",
    "AuctionListing",
    "Appraisal",
    "CostItem",
    "RiskAssessment",
    "MarketComparable",
    "Purchase",
    "PreparationCost",
    "Sale",
    "AuditLog",
    "SaleListing",
    "Enquiry",
    "BuyerBrief",
]
