import pytest

from cargo_dispatch.models import Assignment, CargoRequest, Location
from tests.conftest import ASTANA, KARAGANDA, make_carrier, make_request


@pytest.mark.parametrize(("lat", "lon"), [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_location_rejects_out_of_range(lat: float, lon: float) -> None:
    with pytest.raises(ValueError):
        Location(lat, lon)


def test_location_accepts_edges() -> None:
    assert Location(90, 180).lat == 90


@pytest.mark.parametrize(
    "kwargs",
    [
        {"capacity": 0},
        {"rate": -1},
        {"rating": 5.5},
        {"on_time": 1.2},
    ],
)
def test_carrier_validation(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        make_carrier("C1", **kwargs)


def test_carrier_requires_id() -> None:
    with pytest.raises(ValueError):
        make_carrier("")


@pytest.mark.parametrize("kwargs", [{"weight": 0}, {"priority": 4}, {"priority": 0}])
def test_request_validation(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        make_request("R1", **kwargs)


def test_request_requires_id() -> None:
    with pytest.raises(ValueError):
        CargoRequest("", ASTANA, KARAGANDA, 100)


def test_assignment_total_km() -> None:
    a = Assignment("R1", "C1", empty_km=10.0, loaded_km=90.0, cost=1.0, score=0.5)
    assert a.total_km == pytest.approx(100.0)
