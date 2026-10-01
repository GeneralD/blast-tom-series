import cadquery as cq
import pytest
from drumcad.materials import A6063, SUS304, Material, mass_g


def test_materials_carry_name_and_density():
    assert SUS304.density == pytest.approx(7.93e-3)
    assert A6063.density == pytest.approx(2.70e-3)
    assert "SUS304" in SUS304.name


def test_mass_of_a_known_block():
    block = cq.Workplane("XY").box(10, 20, 30)   # 6000 mm³
    assert mass_g(block, SUS304) == pytest.approx(6000 * 7.93e-3)


def test_mass_sums_every_solid_in_the_workplane():
    two = cq.Workplane("XY").box(10, 10, 10).union(cq.Workplane("XY").box(10, 10, 10).translate((50, 0, 0)))
    assert mass_g(two, Material("test", 1.0)) == pytest.approx(2000)
