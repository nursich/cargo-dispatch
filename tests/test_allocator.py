import random

import pytest

from cargo_dispatch.allocator import GreedyAllocator, OptimalAllocator, get_allocator
from cargo_dispatch.models import CargoType, Location, VehicleType
from cargo_dispatch.scoring import ScoringWeights
from tests.conftest import ALMATY, ASTANA, KARAGANDA, make_carrier, make_request

ALLOCATORS = [GreedyAllocator, OptimalAllocator]


@pytest.mark.parametrize("cls", ALLOCATORS)
def test_each_carrier_and_request_used_at_most_once(cls) -> None:
    requests = [make_request(f"R{i}") for i in range(5)]
    carriers = [make_carrier(f"C{i}") for i in range(3)]
    result = cls().allocate(requests, carriers)
    assert result.n_assigned == 3
    assert len(result.unassigned) == 2
    assert len({a.carrier_id for a in result.assignments}) == 3
    assert len({a.request_id for a in result.assignments}) == 3


@pytest.mark.parametrize("cls", ALLOCATORS)
def test_infeasible_request_is_left_unassigned(cls) -> None:
    requests = [make_request("R1", cargo=CargoType.LIQUID)]
    carriers = [make_carrier("C1", vehicle=VehicleType.TENT)]
    result = cls().allocate(requests, carriers)
    assert result.assignments == []
    assert result.unassigned == ["R1"]
    assert result.assignment_rate == 0.0


@pytest.mark.parametrize("cls", ALLOCATORS)
def test_urgent_request_wins_the_only_carrier(cls) -> None:
    requests = [make_request("NORMAL", priority=1), make_request("URGENT", priority=3)]
    carriers = [make_carrier("C1")]
    result = cls().allocate(requests, carriers)
    assert [a.request_id for a in result.assignments] == ["URGENT"]


@pytest.mark.parametrize("cls", ALLOCATORS)
def test_empty_inputs(cls) -> None:
    assert cls().allocate([], [make_carrier("C1")]).n_assigned == 0
    result = cls().allocate([make_request("R1")], [])
    assert result.unassigned == ["R1"]
    assert result.summary()["assigned"] == 0


@pytest.mark.parametrize("cls", ALLOCATORS)
def test_duplicate_ids_rejected(cls) -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        cls().allocate([make_request("R1"), make_request("R1")], [make_carrier("C1")])


def test_optimal_assigns_more_than_greedy_when_greedy_blocks() -> None:
    """A request processed first steals the only carrier able to serve another one."""
    weights = ScoringWeights(1, 0, 0)
    # URGENT is general cargo: both carriers can take it, the refrigerator is closer.
    urgent = make_request("URGENT", origin=ASTANA, priority=3)
    # COLD is perishable: only the refrigerator can take it.
    cold = make_request("COLD", origin=ALMATY, cargo=CargoType.PERISHABLE, priority=1)
    fridge = make_carrier("FRIDGE", location=ASTANA, vehicle=VehicleType.REFRIGERATOR)
    tent = make_carrier("TENT", location=KARAGANDA, vehicle=VehicleType.TENT)

    greedy = GreedyAllocator(weights).allocate([urgent, cold], [fridge, tent])
    optimal = OptimalAllocator(weights).allocate([urgent, cold], [fridge, tent])

    assert greedy.n_assigned == 1
    assert greedy.unassigned == ["COLD"]
    assert optimal.n_assigned == 2
    assert {(a.request_id, a.carrier_id) for a in optimal.assignments} == {
        ("URGENT", "TENT"),
        ("COLD", "FRIDGE"),
    }


def _random_instance(seed: int):
    rng = random.Random(seed)

    def loc() -> Location:
        return Location(rng.uniform(42, 54), rng.uniform(50, 83))

    cargo = list(CargoType)
    vehicles = list(VehicleType)
    requests = [
        make_request(
            f"R{i}",
            origin=loc(),
            destination=loc(),
            weight=rng.uniform(1_000, 25_000),
            cargo=rng.choice(cargo),
            priority=rng.choice([1, 2, 3]),
        )
        for i in range(rng.randint(3, 15))
    ]
    carriers = [
        make_carrier(
            f"C{j}",
            location=loc(),
            vehicle=rng.choice(vehicles),
            capacity=rng.uniform(5_000, 25_000),
            rate=rng.uniform(250, 450),
            rating=rng.uniform(3, 5),
            on_time=rng.uniform(0.7, 1.0),
        )
        for j in range(rng.randint(3, 15))
    ]
    return requests, carriers


@pytest.mark.parametrize("seed", range(30))
def test_optimal_is_never_worse_than_greedy(seed: int) -> None:
    requests, carriers = _random_instance(seed)
    greedy = GreedyAllocator().allocate(requests, carriers)
    optimal = OptimalAllocator().allocate(requests, carriers)
    assert optimal.objective >= greedy.objective - 1e-9


def test_result_metrics_and_dataframe() -> None:
    requests = [make_request("R1"), make_request("R2", origin=ALMATY)]
    carriers = [make_carrier("C1"), make_carrier("C2", location=KARAGANDA)]
    result = OptimalAllocator().allocate(requests, carriers)
    df = result.to_dataframe()
    assert list(df.columns) == [
        "request_id",
        "carrier_id",
        "empty_km",
        "loaded_km",
        "cost",
        "score",
    ]
    assert len(df) == 2
    assert result.total_cost == pytest.approx(sum(a.cost for a in result.assignments))
    assert 0 <= result.empty_km_share <= 1
    assert 0 < result.mean_score <= 1
    assert result.summary()["strategy"] == "optimal"


def test_get_allocator() -> None:
    assert isinstance(get_allocator("greedy"), GreedyAllocator)
    assert isinstance(get_allocator("optimal"), OptimalAllocator)
    with pytest.raises(ValueError, match="Unknown strategy"):
        get_allocator("random")
