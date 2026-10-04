"""付け根の曲げの概算（D-22）。検査ではなく、仕様と決定ログの根拠になる導出値。"""

from __future__ import annotations

import math

import pytest
from drumcad.dims import Source
from gatling.params import SPEC, override
from gatling.strength import G, root_load


def test_the_root_moment_is_half_the_weight_times_the_distance_from_the_holder_to_the_shell_centre():
    load = root_load(SPEC)
    assert float(load.lever) == 160                                              # arm.rear: ホルダーから胴の中心まで
    assert float(load.moment) == pytest.approx(10 * G * 160 / 2)                  # 質量 10 kg の重さを左右 2 か所で受ける
    assert float(load.moment_impact) == pytest.approx(3 * float(load.moment))     # 衝撃係数 3
    assert float(load.moment) == pytest.approx(7845.3, abs=0.1)                   # N·mm（7.8 N·m）


def test_the_pipe_stress_comes_from_the_section_modulus_of_the_arm_pipe():
    load = root_load(SPEC)
    modulus = math.pi * (25.4**4 - 22.4**4) / (32 * 25.4)
    assert float(load.section_modulus) == pytest.approx(modulus) and modulus == pytest.approx(635.7, abs=0.1)
    assert float(load.pipe_stress) == pytest.approx(float(load.moment) / modulus) and float(load.pipe_stress) < 15           # MPa
    assert float(load.pipe_stress_impact) < 205 / 3                                                            # SUS304 の耐力（約 205 MPa）の 1/3 に収まる


def test_the_pad_edge_couple_is_the_moment_over_the_pad_height():
    load = root_load(SPEC)
    assert float(load.pad_edge_force) == pytest.approx(float(load.moment) / 60)           # 約 131 N
    assert float(load.pad_edge_force_impact) == pytest.approx(3 * float(load.pad_edge_force))
    assert float(root_load(override(SPEC, pad__height=30)).pad_edge_force) == pytest.approx(2 * float(load.pad_edge_force))


def test_the_values_follow_the_leaves_and_inherit_the_provisional_source():
    longer = root_load(override(SPEC, arm__rear=200, load__mass=12))
    assert float(longer.moment) == pytest.approx(12 * G * 200 / 2)
    assert root_load(SPEC).moment.source is Source.PROVISIONAL            # 質量・後ろの長さが仮なので、導出値も仮（derived_from）
