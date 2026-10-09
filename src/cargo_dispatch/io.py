"""Reading carriers and requests from CSV files and writing results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from cargo_dispatch.allocator import AllocationResult
from cargo_dispatch.models import CargoRequest, CargoType, Carrier, Location, VehicleType

CARRIER_COLUMNS = (
    "id",
    "name",
    "lat",
    "lon",
    "vehicle_type",
    "capacity_kg",
    "rate_per_km",
    "rating",
    "on_time_rate",
)
REQUEST_COLUMNS = (
    "id",
    "origin_lat",
    "origin_lon",
    "dest_lat",
    "dest_lon",
    "weight_kg",
    "cargo_type",
    "priority",
)


def _read_csv(path: str | Path, required: tuple[str, ...]) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"id": str})
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
    if df[list(required)].isna().any().any():
        raise ValueError(f"{path}: required columns contain empty values")
    return df


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Rows as plain dicts. Values are typed ``Any`` on purpose: pandas-stubs types
    cells as a wide union that ``float()``/``int()`` do not accept, and the values are
    validated by the model classes anyway."""
    return [{str(k): v for k, v in rec.items()} for rec in df.to_dict(orient="records")]


def load_carriers(path: str | Path) -> list[Carrier]:
    """Load carriers from a CSV file (see ``data/carriers.csv`` for the format)."""
    df = _read_csv(path, CARRIER_COLUMNS)
    return [
        Carrier(
            id=str(row["id"]),
            name=str(row["name"]),
            location=Location(float(row["lat"]), float(row["lon"]), str(row.get("city", ""))),
            vehicle_type=VehicleType(str(row["vehicle_type"]).strip().lower()),
            capacity_kg=float(row["capacity_kg"]),
            rate_per_km=float(row["rate_per_km"]),
            rating=float(row["rating"]),
            on_time_rate=float(row["on_time_rate"]),
        )
        for row in _records(df)
    ]


def load_requests(path: str | Path) -> list[CargoRequest]:
    """Load cargo requests from a CSV file (see ``data/requests.csv``)."""
    df = _read_csv(path, REQUEST_COLUMNS)
    return [
        CargoRequest(
            id=str(row["id"]),
            origin=Location(
                float(row["origin_lat"]), float(row["origin_lon"]), str(row.get("origin_city", ""))
            ),
            destination=Location(
                float(row["dest_lat"]), float(row["dest_lon"]), str(row.get("dest_city", ""))
            ),
            weight_kg=float(row["weight_kg"]),
            cargo_type=CargoType(str(row["cargo_type"]).strip().lower()),
            priority=int(row["priority"]),
        )
        for row in _records(df)
    ]


def save_assignments(result: AllocationResult, path: str | Path) -> Path:
    """Write assignments to CSV; unassigned requests get an empty carrier_id."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = result.to_dataframe()
    if result.unassigned:
        missing = pd.DataFrame({"request_id": result.unassigned, "carrier_id": ""})
        df = pd.concat([df, missing], ignore_index=True)
    df.to_csv(path, index=False)
    return path
