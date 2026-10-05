"""Command-line interface: ``cargo-dispatch allocate`` and ``cargo-dispatch compare``."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

import pandas as pd

from cargo_dispatch import __version__
from cargo_dispatch.allocator import STRATEGIES, get_allocator
from cargo_dispatch.io import load_carriers, load_requests, save_assignments
from cargo_dispatch.scoring import ScoringWeights


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--carriers", required=True, help="CSV file with carriers")
    p.add_argument("--requests", required=True, help="CSV file with cargo requests")
    p.add_argument("--w-cost", type=float, default=0.5, help="weight of cost (default 0.5)")
    p.add_argument(
        "--w-reliability", type=float, default=0.3, help="weight of on-time rate (default 0.3)"
    )
    p.add_argument("--w-rating", type=float, default=0.2, help="weight of rating (default 0.2)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cargo-dispatch",
        description="Distribute cargo transportation requests between carriers.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    alloc = sub.add_parser("allocate", help="run one allocation strategy")
    _add_common(alloc)
    alloc.add_argument("--strategy", choices=sorted(STRATEGIES), default="optimal")
    alloc.add_argument("--out", default="assignments.csv", help="output CSV path")
    alloc.add_argument("--plot", help="optional PNG path for the allocation map")

    cmp_ = sub.add_parser("compare", help="compare all strategies on the same data")
    _add_common(cmp_)
    cmp_.add_argument("--json", action="store_true", help="print metrics as JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        carriers = load_carriers(args.carriers)
        requests = load_requests(args.requests)
        weights = ScoringWeights(args.w_cost, args.w_reliability, args.w_rating)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "allocate":
        result = get_allocator(args.strategy, weights).allocate(requests, carriers)
        out = save_assignments(result, args.out)
        for key, value in result.summary().items():
            print(f"{key:>16}: {value}")
        print(f"{'saved':>16}: {out}")
        if args.plot:
            from cargo_dispatch.viz import plot_allocation  # lazy: matplotlib is heavy

            print(f"{'plot':>16}: {plot_allocation(result, requests, carriers, args.plot)}")
        return 0

    rows = [
        get_allocator(name, weights).allocate(requests, carriers).summary()
        for name in sorted(STRATEGIES)
    ]
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print(pd.DataFrame(rows).set_index("strategy").astype(object).T.to_string())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
