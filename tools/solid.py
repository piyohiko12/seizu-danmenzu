# -*- coding: utf-8 -*-
"""部品の形を一度だけ宣言し、正面図・側面図・断面図をすべてそこから導く。

投影図を手で線分の列として書くと、次の誤りが必ず起きる。
  * 穴の中心線を描き忘れる
  * 見え掛かり線・かくれ線を描き漏らす
  * 正面図と側面図と断面図で形が食い違う
どれも「同じ部品を 3 回描いている」ことが原因なので、宣言を 1 つにまとめる。

座標系（すべて格子単位）
    x … 幅   正面図の横。0 が左
    y … 高さ 0 が上（SVG と同じ向き）
    z … 奥行 0 が手前（正面図を見る側）

見える／かくれるの判定
    投影面の隣り合うマスで「材料がある奥行の集合」を比べ、違いが出る最も手前の
    奥行が、どちらかの最前面と一致すれば見える稜線（実線）、そうでなければ
    かくれ線。奥にある段差を描き漏らさない。
"""
from problem_lib import boundary, to_lines, as_cells

OVERHANG = 0.8          # 中心線を円からはみ出させる長さ


def _r(v):
    """浮動小数の誤差を落とす。整数にごく近い値は整数にそろえる。"""
    n = round(v)
    return float(n) if abs(v - n) < 1e-6 else round(v + 0.0, 4)


def _line(a, b, kind):
    return {"a": [_r(a[0]), _r(a[1])], "b": [_r(b[0]), _r(b[1])], "kind": kind}


def _merge(lines):
    """同じ直線上でつながっている線分をまとめ、重複を落とす。"""
    groups = {}
    for ln in lines:
        (ax, ay), (bx, by) = ln['a'], ln['b']
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            continue
        n = (dx * dx + dy * dy) ** .5          # 斜めの線もまとめるので必ず単位長にする
        dx, dy = dx / n, dy / n
        if dx < 0 or (dx == 0 and dy < 0):          # 向きをそろえる
            dx, dy = -dx, -dy
        cross = ax * dy - ay * dx
        key = (ln['kind'], _r(dx), _r(dy), _r(cross))
        t = lambda p: p[0] * dx + p[1] * dy
        # まとめ直すときは丸めていない値を使う（丸めた値で復元すると座標がずれる）
        groups.setdefault(key, (ln['kind'], dx, dy, cross, []))[4].append(
            tuple(sorted((t(ln['a']), t(ln['b'])))))
    out = []
    for key in sorted(groups, key=str):
        kind, dx, dy, cross, spans = groups[key]
        pos = lambda t: (_r(t * dx + cross * dy), _r(t * dy - cross * dx))
        cur = None
        for t0, t1 in sorted(set(spans)):
            if cur and t0 <= cur[1] + 1e-6:
                cur = (cur[0], max(cur[1], t1))
            else:
                if cur:
                    out.append(_line(pos(cur[0]), pos(cur[1]), kind))
                cur = (t0, t1)
        if cur:
            out.append(_line(pos(cur[0]), pos(cur[1]), kind))
    return out


def _edges(occ, umax, vmax):
    """投影面の稜線を、見える線とかくれ線に分けて返す。

    occ[(u, v)] … その位置に材料がある「視線方向の座標」の集合（手前ほど小さい）
    """
    out = {'outline': set(), 'hidden': set()}
    depth = lambda k: min(occ[k]) if occ.get(k) else None
    for u in range(-1, umax):
        for v in range(-1, vmax):
            a = occ.get((u, v), frozenset())
            for du, dv, edge in ((1, 0, ((u + 1, v), (u + 1, v + 1))),
                                 (0, 1, ((u, v + 1), (u + 1, v + 1)))):
                b = occ.get((u + du, v + dv), frozenset())
                if a == b:
                    continue
                zd = min(a ^ b)
                fronts = [d for d in (depth((u, v)), depth((u + du, v + dv))) if d is not None]
                key = 'outline' if zd == min(fronts) else 'hidden'
                out[key].add(tuple(sorted(edge)))
    out['hidden'] -= out['outline']          # 実線が引かれている位置にかくれ線は描かない
    return out


class Part:
    """直方体・角柱・円柱・穴で組み立てた部品。"""

    def __init__(self, w, h, d):
        self.w, self.h, self.d = w, h, d
        self.prisms = []     # x 方向に押し出した柱。profile は (z, y) のセル
        self.cyls = []       # z 方向の円柱。正面図では円になる
        self.holes = []      # z 方向の穴。段付きに対応

    # ── 形の宣言 ────────────────────────────────────────────
    def prism(self, name, x, profile):
        """(z, y) の断面形を x 方向に押し出す。リブのような三角形も書ける。"""
        self.prisms.append({'name': name, 'x': tuple(x), 'profile': as_cells(profile)})
        return self

    def box(self, name, x, y, z):
        """直方体。prism の便利記法。"""
        return self.prism(name, x, [(c, r) for c in range(*z) for r in range(*y)])

    def cyl(self, name, cx, cy, r, z):
        """奥行方向の円柱（正面図では円、側面図では長方形）。"""
        self.cyls.append({'name': name, 'cx': cx, 'cy': cy, 'r': r, 'z': tuple(z)})
        return self

    def hole(self, name, cx, cy, sections):
        """奥行方向の穴。sections = [(名前, 奥行の開始, 奥行の終わり, 半径), …]

        段付き穴・座ぐり穴は、段ごとに 1 つの section として書く。
        """
        secs = []
        for nm, z0, z1, r in sections:
            top, bot = cy - r, cy + r
            # 格子点に乗る穴だけが断面図のセルになる。切断面を通らない穴は乗らなくてよい
            cells = ([(c, y) for c in range(z0, z1) for y in range(int(top), int(bot))]
                     if top == int(top) and bot == int(bot) else None)
            secs.append({'name': nm, 'z': (z0, z1), 'r': r, 'cells': cells})
        for i in range(len(secs) - 1):
            if secs[i]['z'][1] > secs[i + 1]['z'][0]:
                raise ValueError('%s: 段の奥行が重なっています' % name)
        self.holes.append({'name': name, 'cx': cx, 'cy': cy, 'sections': secs})
        return self

    def round_features(self):
        """穴と円柱の一覧。中心線が引かれているかの検算に使う。"""
        out = [{"name": h['name'], "cx": _r(h['cx']), "cy": _r(h['cy']),
                "r": max(s['r'] for s in h['sections']),
                "z": [min(s['z'][0] for s in h['sections']),
                      max(s['z'][1] for s in h['sections'])], "kind": "hole"}
               for h in self.holes]
        out += [{"name": c['name'], "cx": _r(c['cx']), "cy": _r(c['cy']),
                 "r": c['r'], "z": list(c['z']), "kind": "cyl"} for c in self.cyls]
        return out

    # ── 占有の計算 ──────────────────────────────────────────
    def _front_occ(self):
        """正面図の各マスにある材料の奥行（角柱のみ。円柱と穴は円として別に描く）。

        角柱は**外接直方体**として扱う。斜面（リブの斜辺）は正面から見ると平らな面で
        あって稜線にならないので、奥行の違いを階段状の線にしてはいけないため。
        段のある断面形を押し出すときは、段ごとに別の角柱として宣言すること。
        """
        occ = {}
        for p in self.prisms:
            rows = [r for _, r, _ in p['profile']]
            zs = frozenset(range(min(c for c, _, _ in p['profile']),
                                 max(c for c, _, _ in p['profile']) + 1))
            for x in range(*p['x']):
                for y in range(min(rows), max(rows) + 1):
                    occ.setdefault((x, y), set()).update(zs)
        return occ

    def _side_occ(self):
        """側面図の各マスにある材料の幅方向の座標（右から見るので大きいほど手前）。"""
        occ = {}
        for p in self.prisms:
            for c, r, _ in p['profile']:
                occ.setdefault((c, r), set()).update(range(*p['x']))
        for cy in self.cyls:
            for c in range(*cy['z']):
                for r in range(int(cy['cy'] - cy['r']), int(cy['cy'] + cy['r'])):
                    occ.setdefault((c, r), set()).update(range(self.w))
        # 右側面図は x が大きいほど手前。手前を小さい値にそろえる
        return {k: frozenset(self.w - 1 - x for x in v) for k, v in occ.items()}

    def _side_profile(self):
        """側面図に映る部品の形（三角セルもそのまま持つ）。"""
        cells = {}
        for p in self.prisms:
            for c, r, sh in p['profile']:
                # 同じ位置に全塗りと三角が重なったら全塗りが勝つ
                if cells.get((c, r)) != 'F':
                    cells[(c, r)] = 'F' if (c, r) in cells else sh
        for cy in self.cyls:
            for c in range(*cy['z']):
                for r in range(int(cy['cy'] - cy['r']), int(cy['cy'] + cy['r'])):
                    cells[(c, r)] = 'F'
        return [(c, r, sh) for (c, r), sh in sorted(cells.items())]

    # ── 中心線 ──────────────────────────────────────────────
    def _front_center(self, cx, cy, r):
        return [_line((cx - r - OVERHANG, cy), (cx + r + OVERHANG, cy), 'center'),
                _line((cx, cy - r - OVERHANG), (cx, cy + r + OVERHANG), 'center')]

    # ── 正面図 ──────────────────────────────────────────────
    def front_view(self, pitch=24, cut_x=None, name='正面図'):
        e = _edges(self._front_occ(), self.w, self.h)
        lines = [_line(a, b, 'outline') for a, b, _ in to_lines(e['outline'])]
        lines += [_line(a, b, 'hidden') for a, b, _ in to_lines(e['hidden'])]

        circles, centers = [], []
        # 円柱: 手前にある円柱より小さいものは隠れる
        for i, c in enumerate(sorted(self.cyls, key=lambda c: c['z'][0])):
            covered = any(o['z'][0] < c['z'][0] and o['r'] >= c['r']
                          for o in self.cyls if o is not c)
            circles.append({"c": [c['cx'], c['cy']], "r": c['r'],
                            "kind": 'hidden' if covered else 'outline'})
        # 穴: 手前の段より半径が大きい段は隠れる
        for hole in self.holes:
            biggest = 0
            for s in hole['sections']:
                kind = 'hidden' if s['r'] > biggest and biggest > 0 else 'outline'
                if biggest == 0:
                    kind = 'outline' if self._hole_open(hole, s) else 'hidden'
                circles.append({"c": [hole['cx'], hole['cy']], "r": s['r'], "kind": kind})
                biggest = max(biggest, s['r'])
            centers += self._front_center(hole['cx'], hole['cy'],
                                          max(s['r'] for s in hole['sections']))
        for c in self.cyls:
            centers += self._front_center(c['cx'], c['cy'], c['r'])
        lines += _dedup_center(centers)

        lines = _merge(lines)
        if cut_x is not None:
            lines.append(_line((cut_x, -1), (cut_x, self.h + 1), 'cut'))
        view = {"name": name, "grid": {"cols": self.w, "rows": self.h, "pitch": pitch},
                "lines": lines, "circles": circles}
        if cut_x is not None:
            view["labels"] = [{"at": [cut_x, -1], "text": "A"},
                              {"at": [cut_x, self.h + 1], "text": "A"}]
        return view

    def _hole_open(self, hole, sec):
        """穴の手前の口が外に出ているか（材料に埋もれていないか）。"""
        occ = self._front_occ()
        cell = (int(hole['cx']), int(hole['cy']))
        zs = occ.get(cell) or {c['z'][0] for c in self.cyls} or {0}
        return sec['z'][0] <= min(zs)

    # ── 側面図 ──────────────────────────────────────────────
    def side_view(self, pitch=24, name='側面図'):
        e = _edges(self._side_occ(), self.d, self.h)
        # 外周は多角形として求める。三角セル（リブの斜辺）を階段にしないため、
        # マスの比較で出た外周は捨て、多角形の外周で置き換える。
        prof = self._side_profile()
        poly_sil = boundary(prof)
        cell_sil = boundary([(c, r, 'F') for c, r, _ in prof])
        outline = (e['outline'] - cell_sil) | poly_sil
        hidden = e['hidden'] - outline
        lines = [_line(a, b, 'outline') for a, b, _ in to_lines(outline)]
        lines += [_line(a, b, 'hidden') for a, b, _ in to_lines(hidden)]

        centers = []
        for hole in self.holes:
            lines += self._hole_side_lines(hole)
            z0 = min(s['z'][0] for s in hole['sections'])
            z1 = max(s['z'][1] for s in hole['sections'])
            centers.append(_line((z0 - OVERHANG, hole['cy']), (z1 + OVERHANG, hole['cy']), 'center'))
        for c in self.cyls:
            centers.append(_line((c['z'][0] - OVERHANG, c['cy']),
                                 (c['z'][1] + OVERHANG, c['cy']), 'center'))
        lines += _dedup_center(centers)
        return {"name": name, "grid": {"cols": self.d, "rows": self.h, "pitch": pitch},
                "lines": _merge(lines)}

    def _hole_side_lines(self, hole):
        """側面図に描く穴のかくれ線。段差の線は大径側の全直径にわたる。

        両端は材料の面と重なるので描かない（そこは実線の外形線になる）。
        """
        cy, secs = hole['cy'], hole['sections']
        out = []
        for s in secs:
            z0, z1, r = s['z'][0], s['z'][1], s['r']
            out.append(_line((z0, cy - r), (z1, cy - r), 'hidden'))
            out.append(_line((z0, cy + r), (z1, cy + r), 'hidden'))
        for a, b in zip(secs, secs[1:]):
            if a['z'][1] != b['z'][0]:
                continue
            big = max(a['r'], b['r'])
            out.append(_line((a['z'][1], cy - big), (a['z'][1], cy + big), 'hidden'))
        return out

    # ── 断面図 ──────────────────────────────────────────────
    def section_at(self, cut_x):
        """切断面 x = cut_x の断面図のもと（部品の外形と、面ごとの穴）を返す。"""
        body = sorted({(c, r, sh) for p in self.prisms for c, r, sh in p['profile']}
                      | {(c, r, 'F') for cy in self.cyls for c in range(*cy['z'])
                         for r in range(int(cy['cy'] - cy['r']), int(cy['cy'] + cy['r']))})
        voids = []
        for hole in self.holes:
            big = max(s['r'] for s in hole['sections'])
            if hole['cx'] - big < cut_x < hole['cx'] + big:      # 切断面が穴を通る
                for sec in hole['sections']:
                    if sec['cells'] is None:
                        raise ValueError('%s / %s: 切断面が通る穴なので、半径 %s は格子点に'
                                         '乗る必要があります' % (hole['name'], sec['name'], sec['r']))
                voids += hole['sections']
        return body, voids


def _dedup_center(lines):
    """同じ位置の中心線が重複しないようにする。"""
    seen, out = set(), []
    for ln in lines:
        k = tuple(sorted((tuple(ln['a']), tuple(ln['b']))))
        if k in seen:
            continue
        seen.add(k)
        out.append(ln)
    return out
