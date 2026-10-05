"""Map-like visualisation of an allocation (longitude/latitude plot)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend: works in CI without a display

import matplotlib.pyplot as plt  # noqa: E402

from cargo_dispatch.allocator import AllocationResult  # noqa: E402
from cargo_dispatch.models import CargoRequest, Carrier  # noqa: E402

_CARRIER_COLOR = "#1f6feb"
_LOADED_COLOR = "#2da44e"
_EMPTY_COLOR = "#8c959f"
_UNASSIGNED_COLOR = "#cf222e"


def _grouped_labels(ax: plt.Axes, points: list[tuple[float, float, str]], dy: float) -> None:
    groups: dict[tuple[float, float], list[str]] = defaultdict(list)
    for lon, lat, label in points:
        groups[(round(lon, 3), round(lat, 3))].append(label)
    for (lon, lat), labels in groups.items():
        ax.text(lon + 0.2, lat + dy, ", ".join(sorted(labels)), fontsize=7, color="#424a53")


def plot_allocation(
    result: AllocationResult,
    requests: Sequence[CargoRequest],
    carriers: Sequence[Carrier],
    path: str | Path,
    title: str | None = None,
) -> Path:
    """Draw carriers, empty runs (dashed) and loaded trips (arrows) and save a PNG."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    req_by_id = {r.id: r for r in requests}
    car_by_id = {c.id: c for c in carriers}

    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=150)
    for a in result.assignments:
        r, c = req_by_id[a.request_id], car_by_id[a.carrier_id]
        ax.plot(
            [c.location.lon, r.origin.lon],
            [c.location.lat, r.origin.lat],
            linestyle="--",
            linewidth=1,
            color=_EMPTY_COLOR,
        )
        ax.annotate(
            "",
            xy=(r.destination.lon, r.destination.lat),
            xytext=(r.origin.lon, r.origin.lat),
            arrowprops={"arrowstyle": "-|>", "color": _LOADED_COLOR, "lw": 1.6},
        )

    ax.scatter(
        [c.location.lon for c in carriers],
        [c.location.lat for c in carriers],
        marker="s",
        s=36,
        color=_CARRIER_COLOR,
        zorder=3,
    )
    for rid in result.unassigned:
        r = req_by_id[rid]
        ax.scatter(r.origin.lon, r.origin.lat, marker="x", s=50, color=_UNASSIGNED_COLOR, zorder=4)

    # Several objects often share one city, so labels are grouped by position.
    _grouped_labels(ax, [(c.location.lon, c.location.lat, c.id) for c in carriers], -0.45)
    _grouped_labels(ax, [(r.origin.lon, r.origin.lat, r.id) for r in requests], 0.25)

    # Legend built from proxy artists so it is always complete.
    handles = [
        plt.Line2D([], [], marker="s", linestyle="", color=_CARRIER_COLOR, label="Carrier"),
        plt.Line2D([], [], linestyle="--", color=_EMPTY_COLOR, label="Empty run to pick-up"),
        plt.Line2D([], [], color=_LOADED_COLOR, lw=1.6, label="Loaded trip"),
        plt.Line2D([], [], marker="x", linestyle="", color=_UNASSIGNED_COLOR, label="Unassigned"),
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=4,
        fontsize=8,
        frameon=False,
    )
    ax.set_xlabel("Longitude, °E")
    ax.set_ylabel("Latitude, °N")
    s = result.summary()
    ax.set_title(
        title
        or f"{result.strategy.capitalize()} allocation: {s['assigned']} assigned, "
        f"{s['unassigned']} unassigned, cost {s['total_cost_kzt']:,.0f} KZT",
        fontsize=10,
    )
    ax.grid(alpha=0.25)
    ax.set_aspect(1.4)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path
