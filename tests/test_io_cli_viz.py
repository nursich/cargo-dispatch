import json
from pathlib import Path

import pandas as pd
import pytest

from cargo_dispatch.allocator import OptimalAllocator
from cargo_dispatch.cli import main
from cargo_dispatch.io import load_carriers, load_requests, save_assignments
from cargo_dispatch.models import CargoType, VehicleType
from cargo_dispatch.viz import plot_allocation


def test_load_sample_data(data_dir: Path) -> None:
    carriers = load_carriers(data_dir / "carriers.csv")
    requests = load_requests(data_dir / "requests.csv")
    assert len(carriers) == 12
    assert len(requests) == 15
    assert carriers[0].vehicle_type is VehicleType.TENT
    assert carriers[0].location.name == "Astana"
    assert {r.cargo_type for r in requests} == set(CargoType)


def test_missing_column_is_reported(tmp_path: Path) -> None:
    bad = tmp_path / "carriers.csv"
    bad.write_text("id,name,lat\nC1,X,50\n")
    with pytest.raises(ValueError, match="missing required columns"):
        load_carriers(bad)


def test_empty_value_is_reported(tmp_path: Path, data_dir: Path) -> None:
    df = pd.read_csv(data_dir / "requests.csv")
    df.loc[0, "weight_kg"] = None
    path = tmp_path / "requests.csv"
    df.to_csv(path, index=False)
    with pytest.raises(ValueError, match="empty values"):
        load_requests(path)


def test_save_assignments_includes_unassigned(tmp_path: Path, data_dir: Path) -> None:
    carriers = load_carriers(data_dir / "carriers.csv")
    requests = load_requests(data_dir / "requests.csv")
    result = OptimalAllocator().allocate(requests, carriers)
    out = save_assignments(result, tmp_path / "nested" / "out.csv")
    df = pd.read_csv(out, dtype={"carrier_id": str})
    assert len(df) == len(requests)
    assert df["carrier_id"].isna().sum() == len(result.unassigned)


def test_plot_is_written(tmp_path: Path, data_dir: Path) -> None:
    carriers = load_carriers(data_dir / "carriers.csv")
    requests = load_requests(data_dir / "requests.csv")
    result = OptimalAllocator().allocate(requests, carriers)
    png = plot_allocation(result, requests, carriers, tmp_path / "map.png")
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_cli_allocate(tmp_path: Path, data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    out, plot = tmp_path / "a.csv", tmp_path / "a.png"
    code = main(
        [
            "allocate",
            "--carriers", str(data_dir / "carriers.csv"),
            "--requests", str(data_dir / "requests.csv"),
            "--strategy", "greedy",
            "--out", str(out),
            "--plot", str(plot),
        ]
    )  # fmt: skip
    assert code == 0
    assert out.exists() and plot.exists()
    assert "strategy: greedy" in capsys.readouterr().out


def test_cli_compare_json(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    code = main(
        [
            "compare",
            "--carriers", str(data_dir / "carriers.csv"),
            "--requests", str(data_dir / "requests.csv"),
            "--json",
        ]
    )  # fmt: skip
    assert code == 0
    rows = json.loads(capsys.readouterr().out)
    by_name = {r["strategy"]: r for r in rows}
    assert set(by_name) == {"greedy", "optimal"}
    assert by_name["optimal"]["objective"] >= by_name["greedy"]["objective"]


def test_cli_compare_table(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    args = ["compare", "--carriers", str(data_dir / "carriers.csv")]
    assert main([*args, "--requests", str(data_dir / "requests.csv")]) == 0
    assert "total_cost_kzt" in capsys.readouterr().out


def test_cli_reports_bad_input(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    code = main(["compare", "--carriers", str(tmp_path / "nope.csv"), "--requests", "x.csv"])
    assert code == 2
    assert "error:" in capsys.readouterr().err
