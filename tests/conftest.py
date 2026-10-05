"""Shared fixtures: a small, hand-checkable world with three cities."""

from __future__ import annotations

from pathlib import Path

import pytest

from cargo_dispatch.models import CargoRequest, CargoType, Carrier, Location, VehicleType

ASTANA = Location(51.1694, 71.4491, "Astana")
KARAGANDA = Location(49.8047, 73.1094, "Karaganda")
ALMATY = Location(43.2389, 76.8897, "Almaty")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def make_carrier(
    cid: str,
    location: Location = ASTANA,
    vehicle: VehicleType = VehicleType.TENT,
    capacity: float = 20_000,
    rate: float = 300,
    rating: float = 4.5,
    on_time: float = 0.9,
) -> Carrier:
    return Carrier(cid, f"Carrier {cid}", location, vehicle, capacity, rate, rating, on_time)


def make_request(
    rid: str,
    origin: Location = ASTANA,
    destination: Location = KARAGANDA,
    weight: float = 10_000,
    cargo: CargoType = CargoType.GENERAL,
    priority: int = 1,
) -> CargoRequest:
    return CargoRequest(rid, origin, destination, weight, cargo, priority)


@pytest.fixture
def data_dir() -> Path:
    return DATA_DIR
