import numpy as np
import pytest

from cargo_dispatch.models import CargoType, VehicleType
from cargo_dispatch.scoring import ScoringWeights, build_matrices, is_feasible, priority_weights
from tests.conftest import ALMATY, KARAGANDA, make_carrier, make_request


@pytest.mark.parametrize(
    ("cargo", "vehicle", "expected"),
    [
        (CargoType.GENERAL, VehicleType.TENT, True),
        (CargoType.GENERAL, VehicleType.TANKER, False),
        (CargoType.PERISHABLE, VehicleType.REFRIGERATOR, True),
        (CargoType.PERISHABLE, VehicleType.TENT, False),
        (CargoType.LIQUID, VehicleType.TANKER, True),
        (CargoType.OVERSIZED, VehicleType.FLATBED, True),
        (CargoType.OVERSIZED, VehicleType.TENT, False),
    ],
)
def test_vehicle_compatibility(cargo: CargoType, vehicle: VehicleType, expected: bool) -> None:
    carrier = make_carrier("C1", vehicle=vehicle)
    assert is_feasible(carrier, make_request("R1", cargo=cargo)) is expected


def test_capacity_constraint() -> None:
    carrier = make_carrier("C1", capacity=5_000)
    assert not is_feasible(carrier, make_request("R1", weight=5_001))
    assert is_feasible(carrier, make_request("R2", weight=5_000))


def test_weights_validation_and_normalisation() -> None:
    assert ScoringWeights(2, 1, 1).normalised() == pytest.approx((0.5, 0.25, 0.25))
    with pytest.raises(ValueError):
        ScoringWeights(-1, 1, 1)
    with pytest.raises(ValueError):
        ScoringWeights(0, 0, 0)


def test_matrices_shapes_and_bounds() -> None:
    requests = [make_request("R1"), make_request("R2", cargo=CargoType.LIQUID)]
    carriers = [make_carrier("C1"), make_carrier("C2", location=ALMATY)]
    mx = build_matrices(requests, carriers)
    assert mx.score.shape == (2, 2)
    # Liquid cargo cannot go in a tent truck -> NaN score.
    assert np.isnan(mx.score[1]).all()
    feasible_scores = mx.score[mx.feasible]
    assert ((feasible_scores >= 0) & (feasible_scores <= 1)).all()


def test_closer_carrier_scores_higher() -> None:
    requests = [make_request("R1")]  # starts in Astana
    near = make_carrier("NEAR")  # in Astana
    far = make_carrier("FAR", location=ALMATY)
    mx = build_matrices(requests, [near, far])
    assert mx.empty_km[0, 0] == pytest.approx(0.0)
    assert mx.score[0, 0] > mx.score[0, 1]


def test_reliability_weight_changes_preference() -> None:
    requests = [make_request("R1")]
    cheap = make_carrier("CHEAP", rate=200, on_time=0.5, rating=3.0)
    reliable = make_carrier("RELIABLE", rate=400, on_time=1.0, rating=5.0)
    by_cost = build_matrices(requests, [cheap, reliable], ScoringWeights(1, 0, 0))
    by_quality = build_matrices(requests, [cheap, reliable], ScoringWeights(0, 1, 1))
    assert by_cost.score[0, 0] > by_cost.score[0, 1]
    assert by_quality.score[0, 1] > by_quality.score[0, 0]


def test_cost_formula() -> None:
    request = make_request("R1", destination=KARAGANDA)
    carrier = make_carrier("C1", rate=100)
    mx = build_matrices([request], [carrier])
    assert mx.cost[0, 0] == pytest.approx((mx.empty_km[0, 0] + mx.loaded_km[0, 0]) * 100)


def test_priority_weights() -> None:
    reqs = [make_request("R1", priority=1), make_request("R2", priority=3)]
    assert priority_weights(reqs).ravel().tolist() == [1.0, 2.0]
