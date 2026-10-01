"""3D ビューア（viewer.html）の回帰テスト。

守りたいのは、埋め込んだメッシュが部品の形そのものであること（抜け・別物・壊れた index）、
分解ベクトルが部品表どおりに入っていること、ファイル 1 枚で開けること。
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import replace
from pathlib import Path

import cadquery as cq
import pytest
from drumcad.registry import discover
from drumcad.viewer import THREE_JS, viewer_html

TESTS = Path(__file__).parent


@pytest.fixture(scope="module")
def demo():
    m = discover(TESTS)["demo"]
    parts = m.assembly()
    return m, parts, viewer_html(m.name(), "テスト", parts, {p.name: p for p in m.parts()})


def _embedded(html: str) -> dict:
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m, "埋め込みデータが無い"
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_every_part_is_embedded_as_a_valid_mesh(demo):
    _, parts, html = demo
    data = _embedded(html)
    assert [p["name"] for p in data["parts"]] == list(parts)
    for p in data["parts"]:
        n = len(p["positions"]) // 3
        assert n > 0 and len(p["positions"]) % 3 == 0, p["name"]
        assert p["indices"] and len(p["indices"]) % 3 == 0, p["name"]
        assert 0 <= min(p["indices"]) and max(p["indices"]) < n, f"{p['name']}: index が頂点数を超える"
        assert all(math.isfinite(c) for c in p["positions"]), p["name"]


def test_embedded_mesh_matches_the_part_it_came_from(demo):
    _, parts, html = demo
    for p in _embedded(html)["parts"]:
        box = cq.Compound.makeCompound(parts[p["name"]].vals()).BoundingBox()
        xs, ys, zs = p["positions"][0::3], p["positions"][1::3], p["positions"][2::3]
        assert (min(xs), max(xs)) == pytest.approx((box.xmin, box.xmax), abs=0.5), p["name"]
        assert (min(ys), max(ys)) == pytest.approx((box.ymin, box.ymax), abs=0.5), p["name"]
        assert (min(zs), max(zs)) == pytest.approx((box.zmin, box.zmax), abs=0.5), p["name"]


def test_labels_colors_and_explode_vectors_come_from_the_part_infos(demo):
    _, _, html = demo
    data = _embedded(html)
    by = {p["name"]: p for p in data["parts"]}
    assert by["shell"]["label"] == "胴" and by["shell"]["color"] == "#c9ced6"
    assert by["shell"]["explode"] == [0, 0, 1] and by["plate"]["explode"] == [0, 0, -1]
    assert data["title"] == "demo-6-6" and data["note"] == "テスト"


def test_a_count_above_one_shows_in_the_label():
    m = discover(TESTS)["demo"]
    infos = {p.name: p for p in m.parts()}
    infos["plate"] = replace(infos["plate"], count=6)
    data = _embedded(viewer_html("t", "n", m.assembly(), infos))
    assert next(p for p in data["parts"] if p["name"] == "plate")["label"] == "底板 ×6"


def test_the_html_is_self_contained_except_for_three_js(demo):
    _, _, html = demo
    srcs = re.findall(r'<script[^>]*\ssrc="([^"]+)"', html)
    assert srcs == [THREE_JS]
    assert not re.search(r'<link[^>]*href="https?://', html)
    assert 'id="explode"' in html
