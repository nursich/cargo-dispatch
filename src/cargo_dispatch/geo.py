"""Geographic helpers based on the haversine (great-circle) formula."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from cargo_dispatch.models import Location

#: Mean Earth radius in kilometres (IUGG).
EARTH_RADIUS_KM = 6371.0088

#: Road distance is longer than the straight line; 1.25 is a common
#: empirical detour factor for intercity roads.
DEFAULT_ROAD_FACTOR = 1.25


def haversine_km(a: Location, b: Location) -> float:
    """Great-circle distance between two locations in kilometres."""
    lat1, lon1, lat2, lon2 = map(np.radians, (a.lat, a.lon, b.lat, b.lon))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return float(2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(h)))


def road_distance_km(a: Location, b: Location, factor: float = DEFAULT_ROAD_FACTOR) -> float:
    """Approximate road distance: great-circle distance times a detour factor."""
    if factor < 1.0:
        raise ValueError("Road factor must be >= 1.0")
    return haversine_km(a, b) * factor


def distance_matrix_km(
    sources: Sequence[Location],
    targets: Sequence[Location],
    factor: float = DEFAULT_ROAD_FACTOR,
) -> np.ndarray:
    """Vectorised road-distance matrix of shape ``(len(sources), len(targets))``."""
    if factor < 1.0:
        raise ValueError("Road factor must be >= 1.0")
    if not sources or not targets:
        return np.zeros((len(sources), len(targets)))
    src = np.radians(np.array([[s.lat, s.lon] for s in sources]))
    dst = np.radians(np.array([[t.lat, t.lon] for t in targets]))
    lat1 = src[:, 0][:, None]
    lon1 = src[:, 1][:, None]
    lat2 = dst[:, 0][None, :]
    lon2 = dst[:, 1][None, :]
    h = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0))) * factor
