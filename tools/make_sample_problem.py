# -*- coding: utf-8 -*-
"""サンプル問題 sec-a-001 を部品形状の定義から組み立てる。

    python3 tools/make_sample_problem.py

方眼上のセル集合として部品の切り口を定義し、そこから
  * 断面図の外形線（単位線分の集合）
  * ハッチングを施すセル
を機械的に導く。手で座標を並べると投影図と断面図がずれるため、必ずここから生成する。

部品: L 形ブラケット（正面 10 × 高さ 16 × 奥行 6 マス）
  縦板   奥行 0–2、高さ 0–16
  底板   奥行 0–6、高さ 13–16
  リブ   縦板と底板をつなぐ補強。斜辺は格子点 (2,9)–(6,13) の 45°
  上の穴 φ3 の貫通穴（奥行 0–2 を貫く）＋ 手前面の座ぐり φ5 深さ 1
  下の穴 φ2 の貫通穴 2 つ。切断線 A-A から外れた位置にあるため断面には現れない
"""
import io, json, os
from collections import Counter
from math import gcd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPTH, HEIGHT, WIDTH = 6, 16, 10     # 断面（奥行×高さ）と正面図の幅

PLATE_DEPTH = 2       # 縦板の奥行
BASE_TOP    = 13      # 底板の上面
BORE_ROWS   = (3, 8)  # 座ぐり φ5 が占める高さ
HOLE_ROWS   = (4, 7)  # 貫通穴 φ3 が占める高さ
BORE_DEPTH  = 1       # 座ぐりの深さ
RIB_FROM, RIB_TO = (2, 9), (6, 13)   # リブ斜辺の両端

# ── 切り口のセル ────────────────────────────────────────────
def rib_cells():
    """斜辺 (2,9)-(6,13) の下側、底板の上に乗る三角形。"""
    out = []
    for c in range(RIB_FROM[0], RIB_TO[0]):
        top = RIB_FROM[1] + (c - RIB_FROM[0])       # その列で斜辺が始まる行
        out.append((c, top, 'BL'))                  # 斜辺が横切るセル
        for r in range(top + 1, BASE_TOP):
            out.append((c, r, 'F'))
    return out

def solid_cells():
    cells = []
    removed = set()
    for r in range(BORE_ROWS[0], BORE_ROWS[1]):     # 座ぐり（手前面から BORE_DEPTH）
        for c in range(BORE_DEPTH):
            removed.add((c, r))
    for r in range(HOLE_ROWS[0], HOLE_ROWS[1]):     # 貫通穴（縦板を貫く）
        for c in range(PLATE_DEPTH):
            removed.add((c, r))
    for c in range(PLATE_DEPTH):                    # 縦板
        for r in range(HEIGHT):
            if (c, r) not in removed and r < BASE_TOP:
                cells.append((c, r, 'F'))
    for c in range(DEPTH):                          # 底板
        for r in range(BASE_TOP, HEIGHT):
            cells.append((c, r, 'F'))
    return cells + rib_cells(), sorted(removed)

# ── セル集合 → 外形線 ───────────────────────────────────────
def poly(c, r, sh):
    x, y = c, r
    return {'F':  [(x,y),(x+1,y),(x+1,y+1),(x,y+1)],
            'BL': [(x,y),(x,y+1),(x+1,y+1)],
            'BR': [(x,y+1),(x+1,y+1),(x+1,y)],
            'TR': [(x,y),(x+1,y),(x+1,y+1)],
            'TL': [(x,y),(x+1,y),(x,y+1)]}[sh]

def boundary(cells):
    e = Counter()
    for c, r, sh in cells:
        pl = poly(c, r, sh)
        for i in range(len(pl)):
            e[tuple(sorted((pl[i], pl[(i+1) % len(pl)])))] += 1
    return set(k for k, n in e.items() if n == 1)

def units(a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    g = gcd(abs(dx), abs(dy)) or 1
    sx, sy = dx//g, dy//g
    return [((a[0]+sx*i, a[1]+sy*i), (a[0]+sx*(i+1), a[1]+sy*(i+1))) for i in range(g)]

def to_lines(edges, kind='outline'):
    out = set()
    for a, b in edges:
        for ua, ub in units(a, b):
            if ua > ub: ua, ub = ub, ua
            out.add((ua, ub, kind))
    return [[list(a), list(b), k] for a, b, k in sorted(out)]

def hseg(y, x0, x1):
    return [[[x, y], [x + 1, y]] for x in range(x0, x1)]

# ── 組み立て ────────────────────────────────────────────────
solid, removed = solid_cells()
ribs = set((c, r) for c, r, _ in rib_cells())
lines = to_lines(boundary(solid) | boundary(rib_cells()))
hatch = sorted([[c, r] for c, r, _ in solid if (c, r) not in ribs])

HOLE_CY, HOLE_CR = 5.5, 1.5          # 上の穴 φ3
BORE_CR = 2.5                        # 座ぐり φ5
FOOT_CY, FOOT_CR = 14.5, 1.0         # 下の穴 φ2
FOOT_CX = (2.5, 7.5)
FOOT_DEPTH = (2, 4)                  # 下の穴の奥行位置

front = {
  "name": "正面図",
  "grid": {"cols": WIDTH, "rows": HEIGHT, "pitch": 24},
  "lines": [
    {"a": [0, 0], "b": [WIDTH, 0], "kind": "outline"},
    {"a": [WIDTH, 0], "b": [WIDTH, HEIGHT], "kind": "outline"},
    {"a": [WIDTH, HEIGHT], "b": [0, HEIGHT], "kind": "outline"},
    {"a": [0, HEIGHT], "b": [0, 0], "kind": "outline"},
    {"a": [0, HOLE_CY], "b": [WIDTH, HOLE_CY], "kind": "center"},
    {"a": [0, FOOT_CY], "b": [WIDTH, FOOT_CY], "kind": "center"},
    {"a": [WIDTH / 2, -1], "b": [WIDTH / 2, HEIGHT + 1], "kind": "cut"}
  ],
  "circles": [
    {"c": [WIDTH / 2, HOLE_CY], "r": BORE_CR, "kind": "outline"},
    {"c": [WIDTH / 2, HOLE_CY], "r": HOLE_CR, "kind": "outline"},
    {"c": [FOOT_CX[0], FOOT_CY], "r": FOOT_CR, "kind": "outline"},
    {"c": [FOOT_CX[1], FOOT_CY], "r": FOOT_CR, "kind": "outline"}
  ],
  "labels": [{"at": [WIDTH / 2, -1], "text": "A"}, {"at": [WIDTH / 2, HEIGHT + 1], "text": "A"}]
}

side = {
  "name": "側面図",
  "grid": {"cols": DEPTH, "rows": HEIGHT, "pitch": 24},
  "lines": [
    {"a": [0, 0], "b": [PLATE_DEPTH, 0], "kind": "outline"},
    {"a": [PLATE_DEPTH, 0], "b": [PLATE_DEPTH, BASE_TOP], "kind": "outline"},
    {"a": list(RIB_FROM), "b": list(RIB_TO), "kind": "outline"},
    {"a": list(RIB_TO), "b": [DEPTH, HEIGHT], "kind": "outline"},
    {"a": [DEPTH, HEIGHT], "b": [0, HEIGHT], "kind": "outline"},
    {"a": [0, HEIGHT], "b": [0, 0], "kind": "outline"},
    {"a": [PLATE_DEPTH, BASE_TOP], "b": [DEPTH, BASE_TOP], "kind": "outline"},
    # 座ぐりと貫通穴（かくれ線）
    {"a": [0, BORE_ROWS[0]], "b": [BORE_DEPTH, BORE_ROWS[0]], "kind": "hidden"},
    {"a": [0, BORE_ROWS[1]], "b": [BORE_DEPTH, BORE_ROWS[1]], "kind": "hidden"},
    {"a": [BORE_DEPTH, BORE_ROWS[0]], "b": [BORE_DEPTH, BORE_ROWS[1]], "kind": "hidden"},
    {"a": [BORE_DEPTH, HOLE_ROWS[0]], "b": [PLATE_DEPTH, HOLE_ROWS[0]], "kind": "hidden"},
    {"a": [BORE_DEPTH, HOLE_ROWS[1]], "b": [PLATE_DEPTH, HOLE_ROWS[1]], "kind": "hidden"},
    # 下の穴（かくれ線）
    {"a": [FOOT_DEPTH[0], BASE_TOP], "b": [FOOT_DEPTH[0], HEIGHT], "kind": "hidden"},
    {"a": [FOOT_DEPTH[1], BASE_TOP], "b": [FOOT_DEPTH[1], HEIGHT], "kind": "hidden"},
    {"a": [0, HOLE_CY], "b": [DEPTH, HOLE_CY], "kind": "center"}
  ]
}

problem = {
  "schemaVersion": 2,
  "answerMode": "line",
  "id": "sec-a-001",
  "title": "全断面図 A-A（L 形ブラケット）",
  "category": "full",
  "level": 2,
  "instruction": "次の図は、機械部品の投影図である。(答)の箇所に指示された断面図をかきなさい。ハッチングもほどこしなさい。",
  "views": [front, side],
  "answerArea": {
    "title": "A-A",
    "grid": {"cols": DEPTH, "rows": HEIGHT, "pitch": 26},
    "hintLines": [{"a": [0, HOLE_CY], "b": [DEPTH, HOLE_CY], "kind": "center"}]
  },
  "answer": {
    "lines": lines,
    "hatch": hatch,
    "tolerance": {"lineJaccard": 0.90, "hatchJaccard": 0.90}
  },
  "traps": [
    {"tag": "rib-hatched", "check": "hatch-in-cells", "penalty": 20,
     "cells": sorted([list(c) for c in ribs]),
     "message": "リブは切断面に沿って切られていても、長手方向にはハッチングを施しません（JIS B 0001）。輪郭線だけを描きます。"},
    {"tag": "hole-hatched", "check": "hatch-in-cells", "penalty": 15,
     "cells": [list(c) for c in removed],
     "message": "座ぐりと貫通穴の部分には材料がありません。ハッチングは施しません。"},
    {"tag": "hidden-line-drawn", "check": "line-of-kind", "lineKind": "hidden", "penalty": 10,
     "message": "断面図では、かくれ線は原則として省略します。"},
    {"tag": "off-plane-hole", "check": "segments-present", "penalty": 10,
     "segments": hseg(BASE_TOP + 1, 0, DEPTH) + hseg(HEIGHT - 1, 0, DEPTH),
     "message": "下の 2 つの穴は切断線 A-A 上にないため、この断面には現れません。かくれ線も省略します。"}
  ],
  "hints": [
    "切断線 A-A は部品の中心を通っています。中心にあるものだけが切り口に現れます。",
    "手前面の座ぐりは切断面に現れます。深さのぶんだけ材料が削られています。",
    "リブは切られていますが、ハッチングはしません。輪郭線だけを描きます。",
    "下の 2 つの穴は中心線から外れているので、この断面には現れません。"
  ],
  "explain": ("A-A は部品の中心を通る鉛直な切断面です。切り口は「縦板」と「底板」で、いずれもハッチングを施します。"
              "縦板の中心には φ3 の貫通穴があり、その手前側は φ5 の座ぐりになっているため、"
              "手前 1 マスぶんは座ぐりの高さだけ材料が削られています。"
              "補強リブは切断面に沿って切られていますが、長手方向に切断されるリブにはハッチングを施さないという規則"
              "（JIS B 0001）により、輪郭線だけを描きます。"
              "底板の 2 つの取付穴は切断線から外れた位置にあるため、この断面には現れません"
              "（断面図ではかくれ線を原則省略します）。"),
  "authoring": {
    "solid": [[c, r, sh] for c, r, sh in sorted(solid)],
    "note": "tools/make_sample_problem.py が生成。answer.lines / answer.hatch はこの solid から導出。"
  }
}

dst = os.path.join(ROOT, 'docs/samples/problem_a_full_section.json')
io.open(dst, 'w', encoding='utf-8').write(json.dumps(problem, ensure_ascii=False, indent=2) + '\n')
print('solid=%d  hatch=%d  rib=%d  removed=%d  lines=%d' %
      (len(solid), len(hatch), len(ribs), len(removed), len(lines)))
print('wrote', dst)
