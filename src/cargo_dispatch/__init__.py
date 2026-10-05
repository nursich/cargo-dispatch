"""cargo-dispatch: an intelligent system for distributing cargo transportation
requests between carriers.

Typical use::

    from cargo_dispatch import OptimalAllocator, load_carriers, load_requests

    carriers = load_carriers("data/carriers.csv")
    requests = load_requests("data/requests.csv")
    result = OptimalAllocator().allocate(requests, carriers)
    print(result.summary())
"""

__version__ = "0.1.0"

from cargo_dispatch.allocator import (  # noqa: E402
    AllocationResult,
    GreedyAllocator,
    OptimalAllocator,
    get_allocator,
)
from cargo_dispatch.io import load_carriers, load_requests, save_assignments  # noqa: E402
from cargo_dispatch.models import (  # noqa: E402
    Assignment,
    CargoRequest,
    CargoType,
    Carrier,
    Location,
    VehicleType,
)
from cargo_dispatch.scoring import ScoringWeights  # noqa: E402

__all__ = [
    "AllocationResult",
    "Assignment",
    "CargoRequest",
    "CargoType",
    "Carrier",
    "GreedyAllocator",
    "Location",
    "OptimalAllocator",
    "ScoringWeights",
    "VehicleType",
    "__version__",
    "get_allocator",
    "load_carriers",
    "load_requests",
    "save_assignments",
]
