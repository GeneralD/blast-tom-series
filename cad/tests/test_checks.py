from drumcad.checks import Issue, fatal_count


def test_an_issue_prints_with_a_severity_mark():
    assert str(Issue(True, "管同士が干渉する")) == "❌ 管同士が干渉する"
    assert str(Issue(False, "規格径から 1.2 mm ずれている")) == "⚠️  規格径から 1.2 mm ずれている"


def test_fatal_count_counts_only_fatal_issues():
    assert fatal_count([Issue(True, "a"), Issue(False, "b"), Issue(True, "c")]) == 2
    assert fatal_count([]) == 0
