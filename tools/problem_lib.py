# -*- coding: utf-8 -*-
"""断面図の問題データを、部品の切り口（セル集合）から組み立てるための共通処理。

手で線分の座標を並べると投影図と断面図が必ずずれる。そこで
  1. 部品の切り口を方眼のセル集合として定義し
  2. 「隣のセルが空である辺」＝外形線として抽出し
  3. 既約な刻みへ分解して answer.lines にする
という手順を機械的に行う。tools/make_problems.py がこのライブラリを使う。

セルの形状:
  F  全塗り        BL 左下三角   BR 右下三角   TR 右上三角   TL 左上三角
座標系:
  セル (c, r) は 0 ≦ c < cols, 0 ≦ r < rows。格子点 (x, y) は 0 ≦ x ≦ cols, 0 ≦ y ≦ rows。
  原点は左上で、r と y は下向きが正（SVG と同じ向き）。
"""
from collections import Counter
from math import gcd

SHAPES = {
    'F':  lambda x, y: [(x, y), (x+1, y), (x+1, y+1), (x, y+1)],
    'BL': lambda x, y: [(x, y), (x, y+1), (x+1, y+1)],
    'BR': lambda x, y: [(x, y+1), (x+1, y+1), (x+1, y)],
    'TR': lambda x, y: [(x, y), (x+1, y), (x+1, y+1)],
    'TL': lambda x, y: [(x, y), (x+1, y), (x, y+1)],
}


def poly(cell):
    c, r, sh = cell
    return SHAPES[sh](c, r)


def rect(c0, c1, r0, r1):
    """[c0, c1) × [r0, r1) を全塗りセルで埋める。"""
    return [(c, r, 'F') for c in range(c0, c1) for r in range(r0, r1)]


def subtract(cells, holes):
    """holes（(c, r) の集合）に当たるセルを取り除く。"""
    h = set((c, r) for c, r in holes)
    return [x for x in cells if (x[0], x[1]) not in h]


def slope_cells(a, b, floor_r):
    """格子点 a→b の 45° 斜辺の下側を、floor_r 行の手前まで埋める（リブなどの三角形）。

    a は左上、b は右下で、傾きは +1（右下がり）であること。
    """
    assert b[0] - a[0] == b[1] - a[1] > 0, '45° の右下がり斜辺であること'
    out = []
    for c in range(a[0], b[0]):
        top = a[1] + (c - a[0])
        out.append((c, top, 'BL'))          # 斜辺が横切るセル
        out += [(c, r, 'F') for r in range(top + 1, floor_r)]
    return out


def boundary(cells):
    """セル集合の外周（1 回しか現れない辺）を返す。"""
    e = Counter()
    for cell in cells:
        pl = poly(cell)
        for i in range(len(pl)):
            e[tuple(sorted((pl[i], pl[(i + 1) % len(pl)])))] += 1
    return set(k for k, n in e.items() if n == 1)


def units(a, b):
    """線分を既約な刻み（差分を最大公約数で割った刻み）へ分解する。"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    g = gcd(abs(dx), abs(dy)) or 1
    sx, sy = dx // g, dy // g
    return [((a[0] + sx * i, a[1] + sy * i), (a[0] + sx * (i + 1), a[1] + sy * (i + 1)))
            for i in range(g)]


def to_lines(edges, kind='outline'):
    """辺の集合 → answer.lines の形式（端点の順序をそろえ、重複を除く）。"""
    out = set()
    for a, b in edges:
        for ua, ub in units(a, b):
            if ua > ub:
                ua, ub = ub, ua
            out.add((ua, ub, kind))
    return [[list(a), list(b), k] for a, b, k in sorted(out)]


def make_answer(solid, outline_extra=(), hatch_exclude=()):
    """切り口のセル集合から answer.lines / answer.hatch を導く。

    outline_extra  … 部品全体のシルエットには出ないが描くべき輪郭（リブなど）のセル集合
    hatch_exclude  … 切り口だが慣例でハッチングを施さないセル（リブなど）
    """
    edges = boundary(solid)
    for region in outline_extra:
        edges |= boundary(region)
    skip = set(tuple(c) for c in hatch_exclude)
    hatch = sorted([[c, r] for c, r, _ in solid if (c, r) not in skip])
    return to_lines(edges), hatch


def hseg(y, x0, x1):
    """y 行の水平な単位線分を [x0, x1) ぶん並べる（trap の segments 用）。"""
    return [[[x, y], [x + 1, y]] for x in range(x0, x1)]


def vseg(x, y0, y1):
    """x 列の垂直な単位線分を [y0, y1) ぶん並べる（trap の segments 用）。"""
    return [[[x, y], [x, y + 1]] for y in range(y0, y1)]


def line(a, b, kind='outline'):
    return {"a": list(a), "b": list(b), "kind": kind}


def circle(c, r, kind='outline'):
    return {"c": list(c), "r": r, "kind": kind}
