# -*- coding: utf-8 -*-
"""断面図の問題データを、部品の形状（セル集合）から組み立てるための共通処理。

手で線分の座標を並べると投影図と断面図が必ずずれる。そこで部品を方眼のセル集合として
定義し、外形線を機械的に抽出する。tools/make_problems.py がこのライブラリを使う。

★ 断面図は「切断面の材料」だけを描く図ではない ★

  断面図には、切断面の切り口（ハッチングを施す部分）に加えて、
  **切断面より奥に見える面の輪郭**も実線で描く。

  たとえば板を貫通穴の中心で切ると、切断面には穴の分だけ材料が無い。
  しかし穴は板の幅方向には貫通していないので、穴の向こう側には板の材料が残っており、
  その内壁が見える。したがって板の外形線は穴の位置でも途切れない。

      正しい                  誤り（切り口だけを描いた図）
      ┌────┐                  ┌────┐
      │////│                  │////│
      ├────┤  ← 穴の上面      └────┘
      │    │  ← 穴（内壁が     　　　　  ← 外形線が途切れてしまう
      ├────┤     見えている）  ┌────┐
      │////│                  │////│
      └────┘                  └────┘

  そこで本ライブラリでは 2 つのセル集合を扱う。

    body  … 断面図に現れる部品の外形。切断面より奥に材料が残る範囲すべて
    voids … そのうち切断面では材料が無い部分（穴・座ぐり・溝）

  切り口（ハッチングを施す部分）は cut = body − voids。
  外形線は boundary(body) と boundary(cut) の和集合で求める。
  幅方向にも貫通していて外形が途切れる溝などは、voids ではなく body から外す。

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


def make_answer(body, voids=(), outline_extra=(), hatch_exclude=()):
    """部品の形状から answer.lines / answer.hatch / 切り口セルを導く。

    body           … 断面図に現れる部品の外形（切断面より奥に材料が残る範囲すべて）
    voids          … そのうち切断面では材料が無いセル（穴・座ぐり・溝）
    outline_extra  … 部品全体のシルエットには出ないが描くべき輪郭（リブなど）のセル集合
    hatch_exclude  … 切り口だが慣例でハッチングを施さないセル（リブなど）

    @return (lines, hatch, cut)
    """
    hole = set(tuple(v) for v in voids)
    cut = [c for c in body if (c[0], c[1]) not in hole]

    # 外形線 = 部品の外形の輪郭 ＋ 切り口の輪郭（後者が穴の縁を与える）
    edges = boundary(body) | boundary(cut)
    for region in outline_extra:
        edges |= boundary(region)

    skip = set(tuple(c) for c in hatch_exclude)
    hatch = sorted([[c, r] for c, r, _ in cut if (c, r) not in skip])
    return to_lines(edges), hatch, sorted(cut)


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
