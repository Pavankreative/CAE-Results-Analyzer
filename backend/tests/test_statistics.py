import numpy as np
import pytest

from app.analysis import statistics as st
from app.core.model import Domain, Mesh, ResultField, Simulation, UnitSystem


@pytest.fixture()
def toy():
    nodes = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=float)
    sim = Simulation(id="toy", name="toy", domain=Domain.FEA, analysis_type="", solver="",
                     units=UnitSystem(), mesh=Mesh(nodes=nodes, triangles=np.zeros((0, 3), np.int32)))
    sim.add_field(ResultField(name="v", label="V", unit="MPa",
                              values=np.array([[1.0, 2.0, 3.0, 10.0], [2.0, 4.0, 6.0, 20.0]])))
    return sim


def test_statistics_match_numpy(toy):
    s = st.field_statistics(toy, "v", step=0)
    assert s.maximum.value == 10.0
    assert s.minimum.value == 1.0
    assert s.mean == pytest.approx(4.0)
    assert s.std == pytest.approx(np.std([1, 2, 3, 10]))
    assert s.median == pytest.approx(2.5)


def test_extremum_reports_node_and_coordinates(toy):
    s = st.field_statistics(toy, "v", step=0)
    assert s.maximum.node_id == 4
    assert s.maximum.coordinates == [3.0, 0.0, 0.0]


def test_last_step_is_the_default(toy):
    assert st.field_statistics(toy, "v").maximum.value == 20.0


def test_filter_by_fraction_of_max(toy):
    r = st.filter_field(toy, "v", step=0, fraction_of_max=0.5)
    assert r["selected"] == 1
    assert r["node_ids"] == [4]
    assert r["fraction"] == pytest.approx(0.25)


def test_filter_by_band(toy):
    r = st.filter_field(toy, "v", step=0, minimum=2.0, maximum=3.0)
    assert r["selected"] == 2


def test_envelope_and_history(toy):
    e = st.envelope(toy, "v")
    assert e["max"] == [10.0, 20.0]
    h = st.time_history(toy, "v", index=1)
    assert h["values"] == [2.0, 4.0]


def test_nan_values_are_excluded_and_counted(toy):
    toy.fields["v"].values[0, 0] = np.nan
    s = st.field_statistics(toy, "v", step=0)
    assert s.nan_count == 1
    assert s.count == 3
    assert s.minimum.value == 2.0


def test_histogram_bins_sum_to_count(toy):
    h = st.histogram(toy, "v", step=0, bins=4)
    assert sum(h["counts"]) == 4


def test_sample_dataset_peaks_are_finite(bracket, aero, plate, suspension):
    for sim, field in ((bracket, "von_mises"), (aero, "pressure"),
                       (plate, "temperature"), (suspension, "joint_force")):
        s = st.field_statistics(sim, field)
        assert np.isfinite(s.maximum.value)
        assert s.maximum.node_id is not None
