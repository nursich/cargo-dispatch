"""Allocation strategies that distribute cargo requests between carriers.

Both strategies solve the same problem: each carrier takes at most one request
per dispatch round, each request goes to at most one carrier, and the goal is
to maximise the sum of priority-weighted pair scores (see :mod:`scoring`).

* :class:`GreedyAllocator` - fast baseline. Requests are processed from the
  most urgent to the least urgent, and each one takes the best still-free
  carrier. ``O(n * m)`` but not guaranteed to be optimal.
* :class:`OptimalAllocator` - formulates the task as a linear assignment
  problem and solves it exactly with the Hungarian algorithm
  (:func:`scipy.optimize.linear_sum_assignment`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from cargo_dispatch.models import Assignment, CargoRequest, Carrier
from cargo_dispatch.scoring import (
    PairMatrices,
    ScoringWeights,
    build_matrices,
    priority_weights,
)

#: Benefit used for infeasible pairs so the solver never prefers them.
_INFEASIBLE = -1e9


@dataclass
class AllocationResult:
    """Outcome of one allocation run, with summary metrics."""

    strategy: str
    assignments: list[Assignment] = field(default_factory=list)
    unassigned: list[str] = field(default_factory=list)
    objective: float = 0.0

    @property
    def n_assigned(self) -> int:
        return len(self.assignments)

    @property
    def assignment_rate(self) -> float:
        total = self.n_assigned + len(self.unassigned)
        return self.n_assigned / total if total else 0.0

    @property
    def total_cost(self) -> float:
        return float(sum(a.cost for a in self.assignments))

    @property
    def total_km(self) -> float:
        return float(sum(a.total_km for a in self.assignments))

    @property
    def empty_km_share(self) -> float:
        """Share of driven kilometres that were driven without cargo."""
        total = self.total_km
        return float(sum(a.empty_km for a in self.assignments) / total) if total else 0.0

    @property
    def mean_score(self) -> float:
        return float(np.mean([a.score for a in self.assignments])) if self.assignments else 0.0

    def summary(self) -> dict[str, float | int | str]:
        return {
            "strategy": self.strategy,
            "assigned": self.n_assigned,
            "unassigned": len(self.unassigned),
            "assignment_rate": round(self.assignment_rate, 3),
            "objective": round(self.objective, 4),
            "mean_score": round(self.mean_score, 4),
            "total_cost_kzt": round(self.total_cost, 2),
            "total_km": round(self.total_km, 1),
            "empty_km_share": round(self.empty_km_share, 3),
        }

    def to_dataframe(self) -> pd.DataFrame:
        columns = ["request_id", "carrier_id", "empty_km", "loaded_km", "cost", "score"]
        rows = [
            {
                "request_id": a.request_id,
                "carrier_id": a.carrier_id,
                "empty_km": round(a.empty_km, 1),
                "loaded_km": round(a.loaded_km, 1),
                "cost": round(a.cost, 2),
                "score": round(a.score, 4),
            }
            for a in self.assignments
        ]
        return pd.DataFrame(rows, columns=columns)


class Allocator(Protocol):
    """Interface shared by all allocation strategies."""

    name: str

    def allocate(
        self, requests: Sequence[CargoRequest], carriers: Sequence[Carrier]
    ) -> AllocationResult: ...


def _make_assignment(
    i: int, j: int, requests: Sequence[CargoRequest], carriers: Sequence[Carrier], mx: PairMatrices
) -> Assignment:
    return Assignment(
        request_id=requests[i].id,
        carrier_id=carriers[j].id,
        empty_km=float(mx.empty_km[i, j]),
        loaded_km=float(mx.loaded_km[i, j]),
        cost=float(mx.cost[i, j]),
        score=float(mx.score[i, j]),
    )


def _check_unique_ids(requests: Sequence[CargoRequest], carriers: Sequence[Carrier]) -> None:
    for label, ids in (
        ("request", [r.id for r in requests]),
        ("carrier", [c.id for c in carriers]),
    ):
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {label} ids are not allowed")


class GreedyAllocator:
    """Assign requests one by one (most urgent first) to the best free carrier."""

    name = "greedy"

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = weights or ScoringWeights()

    def allocate(
        self, requests: Sequence[CargoRequest], carriers: Sequence[Carrier]
    ) -> AllocationResult:
        _check_unique_ids(requests, carriers)
        result = AllocationResult(strategy=self.name)
        if not requests:
            return result
        mx = build_matrices(requests, carriers, self.weights)
        prio = priority_weights(requests).ravel()
        free = np.ones(len(carriers), dtype=bool)

        # Most urgent first; among equals, heavier (harder to place) loads first.
        order = sorted(
            range(len(requests)), key=lambda i: (-requests[i].priority, -requests[i].weight_kg)
        )
        for i in order:
            candidates = np.where(mx.feasible[i] & free)[0]
            if candidates.size == 0:
                result.unassigned.append(requests[i].id)
                continue
            j = int(candidates[np.argmax(mx.score[i, candidates])])
            free[j] = False
            result.assignments.append(_make_assignment(i, j, requests, carriers, mx))
            result.objective += float(prio[i] * mx.score[i, j])
        return result


class OptimalAllocator:
    """Solve the assignment exactly with the Hungarian algorithm."""

    name = "optimal"

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = weights or ScoringWeights()

    def allocate(
        self, requests: Sequence[CargoRequest], carriers: Sequence[Carrier]
    ) -> AllocationResult:
        _check_unique_ids(requests, carriers)
        result = AllocationResult(strategy=self.name)
        if not requests:
            return result
        if not carriers:
            result.unassigned = [r.id for r in requests]
            return result

        mx = build_matrices(requests, carriers, self.weights)
        benefit = np.where(mx.feasible, mx.score * priority_weights(requests), _INFEASIBLE)
        rows, cols = linear_sum_assignment(benefit, maximize=True)

        assigned_rows: set[int] = set()
        for i, j in zip(rows, cols, strict=True):
            if mx.feasible[i, j]:
                result.assignments.append(_make_assignment(int(i), int(j), requests, carriers, mx))
                result.objective += float(benefit[i, j])
                assigned_rows.add(int(i))
        result.unassigned = [r.id for k, r in enumerate(requests) if k not in assigned_rows]
        result.assignments.sort(key=lambda a: a.request_id)
        return result


STRATEGIES: dict[str, type[GreedyAllocator] | type[OptimalAllocator]] = {
    GreedyAllocator.name: GreedyAllocator,
    OptimalAllocator.name: OptimalAllocator,
}


def get_allocator(name: str, weights: ScoringWeights | None = None) -> Allocator:
    """Create an allocator by strategy name (``"greedy"`` or ``"optimal"``)."""
    try:
        return STRATEGIES[name](weights)
    except KeyError:
        raise ValueError(f"Unknown strategy {name!r}; choose one of {sorted(STRATEGIES)}") from None
