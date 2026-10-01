from drumcad.dims import Source, design
from drumcad.stock import TUBES, Tube, nearest


def test_the_table_has_the_handrail_polished_38_1_by_1_2():
    assert Tube(38.1, 1.2, "手すり用 #400 研磨管") in TUBES


def test_nearest_returns_the_closest_standard_tube_as_a_derived_dim():
    tube, issue = nearest(design(38.0), design(1.2))
    assert (tube.od, tube.thickness) == (38.1, 1.2)
    assert tube.od_dim.source is Source.DERIVED
    assert issue is None


def test_nearest_warns_when_the_design_value_is_far_from_any_standard():
    tube, issue = nearest(design(40.0), design(1.2))
    assert (tube.od, tube.thickness) == (38.1, 1.2)
    assert issue is not None and not issue.fatal
    assert "1.9 mm" in issue.what


def test_nearest_prefers_the_requested_thickness_within_the_same_od():
    tube, _ = nearest(design(38.1), design(1.6))
    assert (tube.od, tube.thickness) == (38.1, 1.5)


def test_tolerance_is_configurable():
    _, issue = nearest(design(40.0), design(1.2), tolerance=3.0)
    assert issue is None


def test_nearest_warns_when_only_the_thickness_is_off():
    tube, issue = nearest(design(38.1), design(2.6))
    assert (tube.od, tube.thickness) == (38.1, 2.0)
    assert issue is not None and not issue.fatal
    assert "肉厚" in issue.what and "0.6 mm" in issue.what
    assert "外径" not in issue.what


def test_nearest_names_both_od_and_thickness_in_one_issue():
    _, issue = nearest(design(40.0), design(2.6))
    assert issue is not None
    assert "外径" in issue.what and "肉厚" in issue.what


def test_thickness_tolerance_is_configurable():
    _, issue = nearest(design(38.1), design(2.6), thickness_tolerance=1.0)
    assert issue is None
