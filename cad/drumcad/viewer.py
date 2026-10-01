"""組立をブラウザで回して確かめる自己完結の HTML（`viewer.html`）。

CAD ソフトを入れずに済むよう、部品を三角形メッシュにして 1 枚の HTML に埋め込み、
three.js で描く。外部に取りに行くのは three.js（cdnjs）だけ。

    python3 -m http.server -d cad/out 8000   # → http://localhost:8000/<出力ディレクトリ>/viewer.html

部品表（表示名・色・分解方向）は機種の `parts()` から受け取る。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import cadquery as cq

from .contract import PartInfo

THREE_JS = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
TOLERANCE = 0.05         # 弦の許容差（mm）。円弧が多角形に見えない程度
ANGULAR_TOLERANCE = 0.2  # 角度の許容差（rad）


def _shape(part: cq.Workplane) -> cq.Shape:
    return part.val() if len(part.vals()) == 1 else cq.Compound.makeCompound(part.vals())


def mesh(part: cq.Workplane) -> dict[str, list[float] | list[int]]:
    """部品の三角形メッシュ。頂点座標を平坦に並べた配列と、三角形ごとの頂点 index。"""
    vertices, triangles = _shape(part).tessellate(TOLERANCE, ANGULAR_TOLERANCE)
    return {
        "positions": [round(c, 3) for v in vertices for c in (v.x, v.y, v.z)],
        "indices": [i for tri in triangles for i in tri],
    }


def _label(info: PartInfo) -> str:
    return f"{info.label} ×{info.count}" if info.count > 1 else info.label


def viewer_data(title: str, note: str, parts: dict[str, cq.Workplane],
                infos: dict[str, PartInfo]) -> dict:
    meshes = [{"name": name, "label": _label(infos[name]), "color": infos[name].color,
               "explode": list(infos[name].explode), **mesh(part)}
              for name, part in parts.items()]
    xyz = [m["positions"] for m in meshes]
    return {
        "title": title,
        "note": note,
        "radius": max(math.hypot(x, y) for p in xyz for x, y in zip(p[0::3], p[1::3], strict=True)),
        "zmin": min(z for p in xyz for z in p[2::3]),
        "zmax": max(z for p in xyz for z in p[2::3]),
        "parts": meshes,
    }


def viewer_html(title: str, note: str, parts: dict[str, cq.Workplane],
                infos: dict[str, PartInfo]) -> str:
    data = viewer_data(title, note, parts, infos)
    # JSON を <script> に入れるので "</" を閉じタグとして読まれないようにする
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (_TEMPLATE.replace("__TITLE__", data["title"]).replace("__NOTE__", data["note"])
            .replace("__THREE__", THREE_JS).replace("__DATA__", payload))


def export_viewer(title: str, note: str, parts: dict[str, cq.Workplane],
                  infos: dict[str, PartInfo], path: Path) -> None:
    Path(path).write_text(viewer_html(title, note, parts, infos), encoding="utf-8")


_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,">
<title>__TITLE__</title>
<style>
  html, body { margin: 0; height: 100%; background: #1b1e24; color: #e6e6e6;
               font: 13px/1.45 -apple-system, "Hiragino Sans", "Noto Sans JP", sans-serif; overflow: hidden; }
  canvas { display: block; touch-action: none; }
  #ui { position: fixed; top: 10px; left: 10px; background: rgba(0, 0, 0, .58); padding: 10px 12px;
        border-radius: 8px; max-width: 280px; backdrop-filter: blur(4px); }
  #ui h1 { font-size: 14px; margin: 0 0 6px; font-weight: 600; }
  #ui label { display: block; margin: 2px 0; cursor: pointer; }
  #ui .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin: 0 6px 0 4px;
            vertical-align: middle; }
  #ui button { margin: 4px 4px 0 0; padding: 3px 9px; background: #2f343c; color: #eee;
               border: 1px solid #555; border-radius: 4px; cursor: pointer; }
  #ui button:hover { background: #454b55; }
  #ui input[type=range] { width: 100%; }
  #note { margin-top: 8px; color: #f2b0a8; font-size: 12px; }
  #hint { position: fixed; bottom: 8px; left: 10px; color: #9aa0a8; font-size: 12px; }
</style>
</head>
<body>
<div id="ui">
  <h1>__TITLE__</h1>
  <div id="parts"></div>
  <div id="views"></div>
  <label><input type="checkbox" id="wire"> ワイヤーフレーム</label>
  <label>分解 <input type="range" id="explode" min="0" max="1" step="0.01" value="0"></label>
  <div id="note">__NOTE__</div>
</div>
<div id="hint">左ドラッグ: 回転 ／ 右ドラッグ・Shift＋ドラッグ: 移動 ／ ホイール・ピンチ: 拡大縮小</div>
<script src="__THREE__"></script>
<script id="data" type="application/json">__DATA__</script>
<script>
(() => {
  const data = JSON.parse(document.getElementById("data").textContent);
  const scene = new THREE.Scene();
  // 正投影。図面と同じで、位置は見たまま読める
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -20000, 20000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  document.body.appendChild(renderer.domElement);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x303030, 0.75));
  const key = new THREE.DirectionalLight(0xffffff, 0.8);
  key.position.set(0.4, 0.3, 1);
  camera.add(key);
  scene.add(camera);

  // 部品 --------------------------------------------------------------
  // ワイヤーフレームは材質の wireframe フラグでは見えない（三角形が多すぎて塗り潰しと
  // 区別が付かない）。稜線だけを線分で描き、面のほうを消す。
  const meshes = [];
  const partsBox = document.getElementById("parts");
  let wire = false;
  let explode = 0;
  const R = data.radius;
  for (const p of data.parts) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(p.positions, 3));
    g.setIndex(p.indices);
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
      color: p.color, metalness: 0.55, roughness: 0.45, flatShading: true, side: THREE.DoubleSide }));
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(g, 15),
                                     new THREE.LineBasicMaterial({ color: p.color }));
    e.visible = false;
    scene.add(m, e);
    const it = { mesh: m, edges: e, on: true, explode: new THREE.Vector3(...p.explode) };
    meshes.push(it);
    const row = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = true;
    box.addEventListener("change", () => { it.on = box.checked; show(); });
    const swatch = document.createElement("span");
    swatch.className = "sw";
    swatch.style.background = p.color;
    row.append(box, swatch, document.createTextNode(p.label));
    partsBox.appendChild(row);
  }
  function show() {
    for (const it of meshes) {
      it.mesh.visible = it.on && !wire;
      it.edges.visible = it.on && wire;
      // 分解: 部品表の方向ベクトル × スライダー × モデル半径
      const off = it.explode.clone().multiplyScalar(explode * R * 0.8);
      it.mesh.position.copy(off);
      it.edges.position.copy(off);
    }
    place();
  }
  document.getElementById("wire").addEventListener("change", e => { wire = e.target.checked; show(); });
  document.getElementById("explode").addEventListener("input", e => { explode = Number(e.target.value); show(); });

  // 床の格子 ------------------------------------------------------------
  const FIT = R * 1.25 + 10;
  const floor = data.zmin - 3;
  const span = Math.ceil(R * 2.6 / 50) * 50;
  const grid = new THREE.GridHelper(span, span / 50, 0x556070, 0x2c323a);
  grid.rotation.x = Math.PI / 2;
  grid.position.z = floor;
  scene.add(grid);

  // カメラ: z を上にして、注視点の周りを球面座標で回す -----------------------
  const zc = (data.zmin + data.zmax) / 2;
  const target = new THREE.Vector3(0, 0, zc);
  const home = { r: R * 3.2, theta: -Math.PI / 2 + 0.7, phi: 1.05 };
  const sph = { ...home };
  function place() {
    const s = Math.sin(sph.phi);
    camera.position.set(target.x + sph.r * s * Math.cos(sph.theta),
                        target.y + sph.r * s * Math.sin(sph.theta),
                        target.z + sph.r * Math.cos(sph.phi));
    camera.up.set(0, 0, 1);
    camera.lookAt(target);
    // 正投影なので寄り引きは視錐台の大きさで出す。縦長の窓では横が先に切れるので狭い辺で合わせる
    const aspect = window.innerWidth / window.innerHeight;
    const zspan = (data.zmax - data.zmin) / 2 + 10;
    const half = Math.max(FIT, zspan) * (1 + explode) * (sph.r / home.r) / Math.min(1, aspect);
    camera.left = -half * aspect; camera.right = half * aspect;
    camera.top = half; camera.bottom = -half;
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
  }
  const views = {
    "斜め": home,
    "上から": { theta: -Math.PI / 2, phi: 0.02 },
    "下から": { theta: -Math.PI / 2, phi: Math.PI - 0.02 },
    "真横": { theta: -Math.PI / 2, phi: Math.PI / 2 },
    "真横（90°）": { theta: 0, phi: Math.PI / 2 },
  };
  const viewsBox = document.getElementById("views");
  for (const [name, v] of Object.entries(views)) {
    const b = document.createElement("button");
    b.textContent = name;
    b.addEventListener("click", () => { Object.assign(sph, { r: home.r, ...v }); target.set(0, 0, zc); place(); });
    viewsBox.appendChild(b);
  }

  // 操作: 左ドラッグ回転、右／Shift ドラッグ移動、ホイール拡大縮小、2 本指はピンチ ------
  const el = renderer.domElement;
  const pointers = new Map();
  let gesture = null;
  const spread = () => { const [a, b] = [...pointers.values()]; return Math.hypot(a.x - b.x, a.y - b.y); };
  const begin = e => {
    if (pointers.size === 1) { const [p] = pointers.values(); return { x: p.x, y: p.y, pan: e ? e.button === 2 || e.shiftKey : false }; }
    if (pointers.size === 2) return { d: spread() };
    return null;
  };
  el.addEventListener("contextmenu", e => e.preventDefault());
  el.addEventListener("pointerdown", e => {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    el.setPointerCapture(e.pointerId);
    gesture = begin(e);
  });
  el.addEventListener("pointermove", e => {
    if (!pointers.has(e.pointerId) || !gesture) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 1) {
      const dx = e.clientX - gesture.x, dy = e.clientY - gesture.y;
      gesture.x = e.clientX; gesture.y = e.clientY;
      if (gesture.pan) pan(dx, dy); else rotate(dx, dy);
    } else if (pointers.size === 2) {
      const d = spread();
      if (d > 0) sph.r = clampR(sph.r * gesture.d / d);
      gesture.d = d;
    }
    place();
  });
  const release = e => { pointers.delete(e.pointerId); gesture = begin(null); };
  el.addEventListener("pointerup", release);
  el.addEventListener("pointercancel", release);
  el.addEventListener("wheel", e => { e.preventDefault(); zoom(Math.sign(e.deltaY)); place(); }, { passive: false });
  function rotate(dx, dy) {
    sph.theta -= dx * 0.006;
    sph.phi = Math.max(0.02, Math.min(Math.PI - 0.02, sph.phi - dy * 0.006));
  }
  function pan(dx, dy) {
    const k = sph.r * 0.0016;
    const right = new THREE.Vector3(), up = new THREE.Vector3();
    camera.matrixWorld.extractBasis(right, up, new THREE.Vector3());
    target.addScaledVector(right, -dx * k).addScaledVector(up, dy * k);
  }
  function clampR(r) { return Math.max(R * 0.3, Math.min(R * 12, r)); }
  function zoom(sign) { sph.r = clampR(sph.r * (sign > 0 ? 1.12 : 1 / 1.12)); }

  function resize() {
    renderer.setSize(window.innerWidth, window.innerHeight);
    show();
  }
  window.addEventListener("resize", resize);
  resize();
})();
</script>
</body>
</html>
"""
