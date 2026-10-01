from drumcad.checks import Issue, fatal_count


def test_an_issue_prints_with_a_severity_mark():
    assert str(Issue(True, "管同士が干渉する")) == "❌ 管同士が干渉する"
    assert str(Issue(False, "規格径から 1.2 mm ずれている")) == "⚠️  規格径から 1.2 mm ずれている"


def test_fatal_count_counts_only_fatal_issues():
    assert fatal_count([Issue(True, "a"), Issue(False, "b"), Issue(True, "c")]) == 2
    assert fatal_count([]) == 0


def test_count_issues_is_fatal_when_the_solid_count_differs_from_the_part_count():
    from types import SimpleNamespace as NS

    import cadquery as cq
    from drumcad.checks import count_issues

    three = cq.Workplane("XY").pushPoints([(0, 0), (20, 0), (40, 0)]).eachpoint(
        lambda loc: cq.Solid.makeCylinder(4, 10).moved(loc))
    assert count_issues({"a": three}, [NS(name="a", label="A", count=3)]) == []
    [issue] = count_issues({"a": three}, [NS(name="a", label="A", count=2)])
    assert issue.fatal and "A" in issue.what and "3" in issue.what and "2" in issue.what
    [missing] = count_issues({}, [NS(name="a", label="A", count=1)])
    assert missing.fatal
    [extra] = count_issues({"a": three}, [])
    assert extra.fatal


def test_count_issues_is_fatal_when_the_part_count_is_below_one():
    from types import SimpleNamespace as NS

    import cadquery as cq
    from drumcad.checks import count_issues

    for bad in (0, -1):
        [issue] = count_issues({"a": cq.Workplane("XY")}, [NS(name="a", label="A", count=bad)])
        assert issue.fatal and "A" in issue.what and "1 以上" in issue.what

