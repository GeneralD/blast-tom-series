"""ねじ・ロッド・ホルダーの規格表。"""

from __future__ import annotations

import pytest
from drumcad.dims import Choice, Source
from gatling.fasteners import HOLDER_RODS, ROD_THREADS, SCREWS, lookup_holder, lookup_rod, lookup_screw


def test_the_screw_table_has_the_sizes_the_spec_uses():
    assert set(SCREWS) == {"M5", "M6"}
    m6 = SCREWS["M6"]
    assert (float(m6.major), float(m6.tap_drill), float(m6.clearance)) == (6.0, 5.0, 6.6)
    assert (float(m6.head_dia), float(m6.head_height)) == (10.0, 6.0)


def test_every_table_value_is_a_standard_value_with_a_source():
    leaves = [v for s in SCREWS.values() for v in vars(s).values()] + list(ROD_THREADS.values()) + list(HOLDER_RODS.values())
    assert leaves and all(leaf.source is Source.SPEC and leaf.note for leaf in leaves)


def test_a_lookup_goes_through_the_choice_value():
    assert float(lookup_screw(Choice("M5", Source.DESIGN)).major) == 5.0
    assert float(lookup_rod(Choice("#12-24", Source.PROVISIONAL))) == 5.5
    assert float(lookup_holder(Choice("L ロッド 12.7", Source.PROVISIONAL))) == 12.7


def test_a_name_not_in_the_table_raises_instead_of_guessing_a_size():
    with pytest.raises(KeyError):
        lookup_screw(Choice("M99", Source.DESIGN))
