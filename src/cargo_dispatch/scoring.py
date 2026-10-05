"""Multi-criteria scoring of (request, carrier) pairs.

Every feasible pair gets a score in ``[0, 1]`` (higher is better) that combines:

* **cost** - money spent on the empty run to the pick-up point and on the
  loaded trip, normalised against the most expensive feasible pair;
* **reliability** - the carrier's historical on-time delivery rate;
* **rating** - the carrier's customer rating (0-5, rescaled to 0-1).

Infeasible pairs (cargo too heavy or vehicle type not allowed) get ``NaN``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from cargo_dispatch.geo import DEFAULT_ROAD_FACTOR, distance_matrix_km
from cargo_dispatch.models import CARGO_COMPATIBILITY, CargoRequest, Carrier


@dataclass(frozen=True)
class ScoringWeights:
    """Relative importance of each criterion. Weights are normalised to sum to 1."""

    cost: float = 0.5
    reliability: float = 0.3
    rating: float = 0.2

    def __post_init__(self) -> None:
        values = (self.cost, self.reliability, self.rating)
        if any(w < 0 for w in values):
            raise ValueError("Weights must be non-negative")
        if sum(values) == 0:
            raise ValueError("At least one weight must be positive")

    def normalised(self) -> tuple[float, float, float]:
        total = self.cost + self.reliability + self.rating
        return self.cost / total, self.reliability / total, self.rating / total


#: Multiplier applied to a request's score according to its priority, so that
#: urgent requests win scarce carriers.
PRIORITY_MULTIPLIER = {1: 1.0, 2: 1.5, 3: 2.0}


def is_feasible(carrier: Carrier, request: CargoRequest) -> bool:
    """A carrier can serve a request if the load fits and the vehicle is allowed."""
    return (
        request.weight_kg <= carrier.capacity_kg
        and carrier.vehicle_type in CARGO_COMPATIBILITY[request.cargo_type]
    )


@dataclass(frozen=True)
class PairMatrices:
    """Pre-computed matrices of shape ``(n_requests, n_carriers)``."""

    empty_km: np.ndarray
    loaded_km: np.ndarray
    cost: np.ndarray
    feasible: np.ndarray
    score: np.ndarray


def build_matrices(
    requests: Sequence[CargoRequest],
    carriers: Sequence[Carrier],
    weights: ScoringWeights | None = None,
    road_factor: float = DEFAULT_ROAD_FACTOR,
) -> PairMatrices:
    """Compute distances, costs, feasibility and scores for every pair."""
    weights = weights or ScoringWeights()
    w_cost, w_rel, w_rat = weights.normalised()
    n, m = len(requests), len(carriers)

    empty_km = distance_matrix_km(
        [r.origin for r in requests], [c.location for c in carriers], road_factor
    )
    loaded = np.array(
        [distance_matrix_km([r.origin], [r.destination], road_factor)[0, 0] for r in requests]
    ).reshape(n, 1)
    loaded_km = np.broadcast_to(loaded, (n, m)).copy() if n else np.zeros((0, m))

    rates = np.array([c.rate_per_km for c in carriers]).reshape(1, m)
    cost = (empty_km + loaded_km) * rates

    feasible = np.array(
        [[is_feasible(c, r) for c in carriers] for r in requests], dtype=bool
    ).reshape(n, m)

    score = np.full((n, m), np.nan)
    if feasible.any():
        max_cost = float(cost[feasible].max())
        cost_term = 1.0 - cost / max_cost if max_cost > 0 else np.ones_like(cost)
        reliability = np.array([c.on_time_rate for c in carriers]).reshape(1, m)
        rating = np.array([c.rating / 5.0 for c in carriers]).reshape(1, m)
        raw = w_cost * cost_term + w_rel * reliability + w_rat * rating
        score = np.where(feasible, raw, np.nan)

    return PairMatrices(
        empty_km=empty_km, loaded_km=loaded_km, cost=cost, feasible=feasible, score=score
    )


def priority_weights(requests: Sequence[CargoRequest]) -> np.ndarray:
    """Column vector of priority multipliers, shape ``(n_requests, 1)``."""
    return np.array([PRIORITY_MULTIPLIER[r.priority] for r in requests], dtype=float).reshape(-1, 1)
