"""Domain models: carriers, cargo requests and assignments.

All models are immutable dataclasses that validate their fields on creation,
so invalid data is rejected as early as possible (at load time) instead of
producing silently wrong allocations later.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VehicleType(str, Enum):
    """Type of vehicle operated by a carrier."""

    TENT = "tent"
    REFRIGERATOR = "refrigerator"
    TANKER = "tanker"
    FLATBED = "flatbed"


class CargoType(str, Enum):
    """Type of cargo in a transportation request."""

    GENERAL = "general"
    PERISHABLE = "perishable"
    LIQUID = "liquid"
    OVERSIZED = "oversized"


#: Which vehicle types are allowed to carry which cargo types.
CARGO_COMPATIBILITY: dict[CargoType, frozenset[VehicleType]] = {
    CargoType.GENERAL: frozenset({VehicleType.TENT, VehicleType.REFRIGERATOR, VehicleType.FLATBED}),
    CargoType.PERISHABLE: frozenset({VehicleType.REFRIGERATOR}),
    CargoType.LIQUID: frozenset({VehicleType.TANKER}),
    CargoType.OVERSIZED: frozenset({VehicleType.FLATBED}),
}


@dataclass(frozen=True)
class Location:
    """A point on the Earth's surface in decimal degrees."""

    lat: float
    lon: float
    name: str = ""

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError(f"Latitude out of range [-90, 90]: {self.lat}")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"Longitude out of range [-180, 180]: {self.lon}")


@dataclass(frozen=True)
class Carrier:
    """A transport company (or a single truck) that can take one request.

    Attributes:
        id: Unique carrier identifier.
        name: Human-readable name.
        location: Current position of the vehicle.
        vehicle_type: Vehicle body type.
        capacity_kg: Maximum payload in kilograms.
        rate_per_km: Tariff in tenge (KZT) per kilometre driven.
        rating: Customer rating on a 0-5 scale.
        on_time_rate: Historical share of on-time deliveries, 0-1.
    """

    id: str
    name: str
    location: Location
    vehicle_type: VehicleType
    capacity_kg: float
    rate_per_km: float
    rating: float = 4.0
    on_time_rate: float = 0.9

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Carrier id must not be empty")
        if self.capacity_kg <= 0:
            raise ValueError(f"Carrier {self.id}: capacity_kg must be positive")
        if self.rate_per_km <= 0:
            raise ValueError(f"Carrier {self.id}: rate_per_km must be positive")
        if not 0.0 <= self.rating <= 5.0:
            raise ValueError(f"Carrier {self.id}: rating must be within [0, 5]")
        if not 0.0 <= self.on_time_rate <= 1.0:
            raise ValueError(f"Carrier {self.id}: on_time_rate must be within [0, 1]")


@dataclass(frozen=True)
class CargoRequest:
    """A request to move cargo from an origin to a destination.

    Attributes:
        id: Unique request identifier.
        origin: Pick-up point.
        destination: Drop-off point.
        weight_kg: Cargo weight in kilograms.
        cargo_type: Kind of cargo (decides which vehicles are allowed).
        priority: 1 = normal, 2 = high, 3 = urgent.
    """

    id: str
    origin: Location
    destination: Location
    weight_kg: float
    cargo_type: CargoType = CargoType.GENERAL
    priority: int = 1

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Request id must not be empty")
        if self.weight_kg <= 0:
            raise ValueError(f"Request {self.id}: weight_kg must be positive")
        if self.priority not in (1, 2, 3):
            raise ValueError(f"Request {self.id}: priority must be 1, 2 or 3")


@dataclass(frozen=True)
class Assignment:
    """The decision to serve one request with one carrier."""

    request_id: str
    carrier_id: str
    empty_km: float
    loaded_km: float
    cost: float
    score: float

    @property
    def total_km(self) -> float:
        """Total distance driven: empty run to the pick-up plus the loaded trip."""
        return self.empty_km + self.loaded_km
