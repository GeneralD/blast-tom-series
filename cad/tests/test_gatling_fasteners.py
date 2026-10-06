"""Gatling のロッドのねじとホルダーロッドの規格表（ISO のねじは `test_fasteners.py`）。"""

from __future__ import annotations

from drumcad.dims import Choice, Source
from gatling.fasteners import HOLDER_RODS, ROD_THREADS, lookup_holder, lookup_rod


def test_every_table_value_is_a_standard_value_with_a_source():
    leaves = list(ROD_THREADS.values()) + list(HOLDER_RODS.values())
    assert leaves and all(leaf.source is Source.SPEC and leaf.note for leaf in leaves)


def test_a_lookup_goes_through_the_choice_value():
    assert float(lookup_rod(Choice("#12-24", Source.PROVISIONAL))) == 5.5
    assert float(lookup_holder(Choice("L ロッド 12.7", Source.PROVISIONAL))) == 12.7
