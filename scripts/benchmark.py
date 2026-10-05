"""Compare greedy and optimal allocation on random instances.

Usage::

    python scripts/benchmark.py --instances 100 --out results/benchmark.csv

For every random instance the script records the objective value, total cost,
number of assigned requests and the run time of both strategies. The fixed
seed makes the experiment reproducible.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from cargo_dispatch import (
    CargoRequest,
    CargoType,
    Carrier,
    GreedyAllocator,
    Location,
    OptimalAllocator,
    VehicleType,
)


def random_instance(
    rng: np.random.Generator, n_requests: int, n_carriers: int
) -> tuple[list[CargoRequest], list[Carrier]]:
    """Random requests and carriers inside the bounding box of Kazakhstan."""

    def loc() -> Location:
        return Location(float(rng.uniform(42, 54)), float(rng.uniform(50, 83)))

    cargo = list(CargoType)
    vehicles = list(VehicleType)
    requests = [
        CargoRequest(
            id=f"R{i}",
            origin=loc(),
            destination=loc(),
            weight_kg=float(rng.uniform(1_000, 24_000)),
            cargo_type=cargo[rng.choice(len(cargo), p=[0.55, 0.2, 0.15, 0.1])],
            priority=int(rng.choice([1, 2, 3], p=[0.6, 0.3, 0.1])),
        )
        for i in range(n_requests)
    ]
    carriers = [
        Carrier(
            id=f"C{j}",
            name=f"Carrier {j}",
            location=loc(),
            vehicle_type=vehicles[rng.choice(len(vehicles), p=[0.45, 0.25, 0.15, 0.15])],
            capacity_kg=float(rng.uniform(8_000, 25_000)),
            rate_per_km=float(rng.uniform(250, 450)),
            rating=float(rng.uniform(3, 5)),
            on_time_rate=float(rng.uniform(0.75, 1.0)),
        )
        for j in range(n_carriers)
    ]
    return requests, carriers


def run(instances: int, seed: int, sizes: list[int]) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for size in sizes:
        for k in range(instances):
            requests, carriers = random_instance(rng, size, size)
            for allocator in (GreedyAllocator(), OptimalAllocator()):
                t0 = time.perf_counter()
                result = allocator.allocate(requests, carriers)
                elapsed = time.perf_counter() - t0
                rows.append(
                    {
                        "size": size,
                        "instance": k,
                        "strategy": allocator.name,
                        "objective": result.objective,
                        "assigned": result.n_assigned,
                        "total_cost": result.total_cost,
                        "empty_km_share": result.empty_km_share,
                        "time_ms": elapsed * 1000,
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--instances", type=int, default=50, help="instances per size")
    parser.add_argument("--sizes", type=int, nargs="+", default=[10, 25, 50, 100])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="results/benchmark.csv")
    args = parser.parse_args()

    df = run(args.instances, args.seed, args.sizes)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    summary = df.groupby(["size", "strategy"]).agg(
        objective=("objective", "mean"),
        assigned=("assigned", "mean"),
        cost=("total_cost", "mean"),
        empty_share=("empty_km_share", "mean"),
        time_ms=("time_ms", "mean"),
    )
    print(summary.round(3).to_string())
    print(f"\nRaw results saved to {out}")


if __name__ == "__main__":
    main()
