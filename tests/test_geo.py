import numpy as np
import pytest

from cargo_dispatch.geo import distance_matrix_km, haversine_km, road_distance_km
from cargo_dispatch.models import Location
from tests.conftest import ALMATY, ASTANA, KARAGANDA


def test_zero_distance_to_itself() -> None:
    assert haversine_km(ASTANA, ASTANA) == pytest.approx(0.0)


def test_known_distance_astana_almaty() -> None:
    # Great-circle distance Astana-Almaty is about 970 km.
    assert haversine_km(ASTANA, ALMATY) == pytest.approx(970, abs=15)


def test_one_degree_of_latitude_is_about_111_km() -> None:
    assert haversine_km(Location(0, 0), Location(1, 0)) == pytest.approx(111.2, abs=0.2)


def test_symmetry() -> None:
    assert haversine_km(ASTANA, KARAGANDA) == pytest.approx(haversine_km(KARAGANDA, ASTANA))


def test_road_distance_applies_factor() -> None:
    assert road_distance_km(ASTANA, ALMATY, 1.5) == pytest.approx(
        1.5 * haversine_km(ASTANA, ALMATY)
    )


def test_road_factor_below_one_is_rejected() -> None:
    with pytest.raises(ValueError):
        road_distance_km(ASTANA, ALMATY, 0.9)
    with pytest.raises(ValueError):
        distance_matrix_km([ASTANA], [ALMATY], 0.5)


def test_matrix_matches_scalar_function() -> None:
    src = [ASTANA, KARAGANDA]
    dst = [ALMATY, ASTANA, KARAGANDA]
    mx = distance_matrix_km(src, dst, factor=1.0)
    assert mx.shape == (2, 3)
    for i, a in enumerate(src):
        for j, b in enumerate(dst):
            assert mx[i, j] == pytest.approx(haversine_km(a, b), rel=1e-9)


def test_matrix_with_empty_input() -> None:
    assert distance_matrix_km([], [ASTANA]).shape == (0, 1)
    assert np.size(distance_matrix_km([ASTANA], [])) == 0
