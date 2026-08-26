# -*- coding: utf-8 -*-
"""問題データを部品形状の定義から組み立てる。

    python3 tools/make_problems.py

docs/samples/<id>.json を書き出し、src/Problems.gs を作り直す。
座標は必ずここから生成すること（手で並べると投影図と断面図がずれる）。
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from problem_lib import (rect, slope_cells, make_answer, stepped_hole,
                         hole_hidden_lines, hseg, vseg, line, circle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS = []


def add(p):
    PROBLEMS.append(p)
    return p


def AUTHORING(body, hole, cut):
    """検算に使う作問データ。

    body  … 断面図に現れる部品の外形
    voids … 切断面で材料が無い部分。stepped_hole が面ごとに分けたもの（奥行と半径つき）
    cut   … 切り口 = body − voids
    """
    return {
        "body": [[c, r, sh] for c, r, sh in sorted(body)],
        "voids": [{"name": f["name"], "z": list(f["z"]), "r": f["r"],
                   "cells": sorted([list(c) for c in f["cells"]])} for f in hole],
        "cut": [[c, r, sh] for c, r, sh in sorted(cut)],
        "note": ("tools/make_problems.py が生成。穴は stepped_hole に奥行と半径で宣言し、"
                 "面の分け方は自動。answer.lines は boundary(body)、boundary(cut)、"
                 "穴の面ごとの boundary の和集合。answer.hatch は cut からリブなどを除いたもの。")
    }


def VOID_CELLS(hole):
    """穴の面をまとめて 1 つのセル集合にする（トラップの判定用）。"""
    return sorted([list(c) for f in hole for c in f["cells"]])


# ══════════════════════════════════════════════════════════════════
# sec-a-001 L 形ブラケット
#   奥行 6 × 高さ 16 × 幅 10
#   縦板 2 深、底板 6 深、45° の補強リブ、手前面の座ぐり付き貫通穴
# ══════════════════════════════════════════════════════════════════
def bracket():
    D, H, W = 6, 16, 10
    PLATE, BASE_TOP = 2, 13
    HOLE_CY, BORE_R, HOLE_R = 5.5, 2.5, 1.5   # 穴の中心 / 座ぐり φ5 / 貫通穴 φ3
    BORE_D = 1                                 # 座ぐりの深さ
    RIB_A, RIB_B = (2, 9), (6, 13)

    # 穴は「奥行の範囲と半径」で宣言する。面の分け方（＝段差の線の位置）は自動で決まる。
    # 座ぐりと貫通穴は縦板の幅方向には貫通していないので、外形（body）はそのまま。
    hole = stepped_hole(HOLE_CY, [('座ぐり φ5', 0, BORE_D, BORE_R),
                                  ('貫通穴 φ3', BORE_D, PLATE, HOLE_R)])
    rib = slope_cells(RIB_A, RIB_B, BASE_TOP)
    body = sorted(rect(0, PLATE, 0, BASE_TOP) + rect(0, D, BASE_TOP, H) + rib)
    lines, hatch, cut = make_answer(body, voids=[f['cells'] for f in hole], outline_extra=[rib],
                                    hatch_exclude=[(c, r) for c, r, _ in rib])

    FOOT_CX, FOOT_CY, FOOT_R = (2.5, 7.5), 14.5, 1.0

    front = {
        "name": "正面図",
        "grid": {"cols": W, "rows": H, "pitch": 24},
        "lines": [line((0, 0), (W, 0)), line((W, 0), (W, H)),
                  line((W, H), (0, H)), line((0, H), (0, 0)),
                  line((0, HOLE_CY), (W, HOLE_CY), 'center'),
                  line((0, FOOT_CY), (W, FOOT_CY), 'center'),
                  line((W / 2, -1), (W / 2, H + 1), 'cut')],
        "circles": [circle((W / 2, HOLE_CY), BORE_R), circle((W / 2, HOLE_CY), HOLE_R),
                    circle((FOOT_CX[0], FOOT_CY), FOOT_R),
                    circle((FOOT_CX[1], FOOT_CY), FOOT_R)],
        "labels": [{"at": [W / 2, -1], "text": "A"}, {"at": [W / 2, H + 1], "text": "A"}]
    }
    side_outline = [line((0, 0), (PLATE, 0)), line((PLATE, 0), (PLATE, BASE_TOP)),
                    line(RIB_A, RIB_B), line(RIB_B, (D, H)),
                    line((D, H), (0, H)), line((0, H), (0, 0)),
                    line((PLATE, BASE_TOP), (D, BASE_TOP))]
    side = {
        "name": "側面図",
        "grid": {"cols": D, "rows": H, "pitch": 24},
        # 穴のかくれ線は断面図と同じ宣言から導く。段差の線も自動で入る。
        "lines": side_outline + hole_hidden_lines(hole, side_outline) + [
            # 底板の取付穴 φ2。奥行方向の穴なので、側面図では横のかくれ線になる
            line((0, FOOT_CY - FOOT_R), (D, FOOT_CY - FOOT_R), 'hidden'),
            line((0, FOOT_CY + FOOT_R), (D, FOOT_CY + FOOT_R), 'hidden'),
            line((0, HOLE_CY), (D, HOLE_CY), 'center')]
    }
    return add({
        "schemaVersion": 2, "answerMode": "line",
        "id": "sec-a-001", "title": "全断面図 A-A（L 形ブラケット）",
        "category": "full", "level": 2,
        "instruction": "次の図は、機械部品の投影図である。(答)の箇所に指示された断面図をかきなさい。ハッチングもほどこしなさい。",
        "views": [front, side],
        "answerArea": {"title": "A-A", "grid": {"cols": D, "rows": H, "pitch": 26},
                       "hintLines": [line((0, HOLE_CY), (D, HOLE_CY), 'center')]},
        "answer": {"lines": lines, "hatch": hatch,
                   "tolerance": {"lineJaccard": 0.90, "hatchJaccard": 0.90}},
        "traps": [
            {"tag": "rib-hatched", "check": "hatch-in-cells", "penalty": 20,
             "cells": sorted([[c, r] for c, r, _ in rib]),
             "message": "リブは切断面に沿って切られていても、長手方向にはハッチングを施しません（JIS B 0001）。輪郭線だけを描きます。"},
            {"tag": "hole-hatched", "check": "hatch-in-cells", "penalty": 15,
             "cells": VOID_CELLS(hole),
             "message": "座ぐりと貫通穴の部分には材料がありません。ハッチングは施しません。"},
            {"tag": "hidden-line-drawn", "check": "line-of-kind", "lineKind": "hidden", "penalty": 10,
             "message": "断面図では、かくれ線は原則として省略します。"},
            {"tag": "off-plane-hole", "check": "segments-present", "penalty": 10,
             "segments": hseg(BASE_TOP + 1, 0, D) + hseg(H - 1, 0, D),
             "message": "下の 2 つの穴は切断線 A-A 上にないため、この断面には現れません。かくれ線も省略します。"}
        ],
        "hints": [
            "切断線 A-A は部品の中心を通っています。中心にあるものだけが切り口に現れます。",
            "手前面の座ぐりは切断面に現れます。深さのぶんだけ材料が削られています。",
            "穴は縦板を幅方向には貫いていません。穴の向こう側の内壁が見えるので、縦板の外形線は穴の位置でも途切れません。",
            "座ぐりと貫通穴では径が違います。境目では見える面が変わるので、座ぐりの底の線は穴を横切って引きます。",
            "リブは切られていますが、ハッチングはしません。輪郭線だけを描きます。",
            "下の 2 つの穴は中心線から外れているので、この断面には現れません。"
        ],
        "explain": ("A-A は部品の中心を通る鉛直な切断面です。切り口は「縦板」と「底板」で、いずれもハッチングを施します。"
                    "縦板の中心には φ3 の貫通穴があり、その手前側は φ5 の座ぐりになっているため、"
                    "手前 1 マスぶんは座ぐりの高さだけ材料が削られています。"
                    "穴は縦板を幅方向には貫いていないため、切断面の向こう側には穴の内壁が見えます。"
                    "その輪郭は実線で描くので、縦板の外形線は穴の位置でも途切れません。"
                    "補強リブは切断面に沿って切られていますが、長手方向に切断されるリブにはハッチングを施さないという規則"
                    "（JIS B 0001）により、輪郭線だけを描きます。"
                    "底板の 2 つの取付穴は切断線から外れた位置にあるため、この断面には現れません"
                    "（断面図ではかくれ線を原則省略します）。"),
        "authoring": AUTHORING(body, hole, cut)
    })


# ══════════════════════════════════════════════════════════════════
# sec-a-002 T 形の台座
#   奥行 8 × 高さ 12 × 幅 12
#   底板の上に細い柱が立つ左右対称の部品。柱に奥行方向の貫通穴
# ══════════════════════════════════════════════════════════════════
def pedestal():
    D, H, W = 8, 12, 12
    BASE_TOP = 9                          # 底板の上面
    COL_Z = (2, 6)                        # 柱の奥行の範囲
    COL_X = (4, 8)                        # 柱の幅の範囲（正面図）
    HOLE_CY, HOLE_R = 4.5, 1.5            # 柱の貫通穴 φ3
    FOOT_CX, FOOT_CY, FOOT_R = (2.0, 10.0), 10.5, 1.0

    # 貫通穴は柱の幅方向には貫通していないので、外形（body）は柱をそのまま含む。
    hole = stepped_hole(HOLE_CY, [('貫通穴 φ3', COL_Z[0], COL_Z[1], HOLE_R)])
    body = sorted(rect(COL_Z[0], COL_Z[1], 0, BASE_TOP) + rect(0, D, BASE_TOP, H))
    lines, hatch, cut = make_answer(body, voids=[f['cells'] for f in hole])

    front = {
        "name": "正面図",
        "grid": {"cols": W, "rows": H, "pitch": 24},
        "lines": [line((COL_X[0], 0), (COL_X[1], 0)), line((COL_X[1], 0), (COL_X[1], BASE_TOP)),
                  line((COL_X[1], BASE_TOP), (W, BASE_TOP)), line((W, BASE_TOP), (W, H)),
                  line((W, H), (0, H)), line((0, H), (0, BASE_TOP)),
                  line((0, BASE_TOP), (COL_X[0], BASE_TOP)), line((COL_X[0], BASE_TOP), (COL_X[0], 0)),
                  line((0, HOLE_CY), (W, HOLE_CY), 'center'),
                  line((0, FOOT_CY), (W, FOOT_CY), 'center'),
                  line((W / 2, -1), (W / 2, H + 1), 'cut')],
        "circles": [circle((W / 2, HOLE_CY), HOLE_R),
                    circle((FOOT_CX[0], FOOT_CY), FOOT_R),
                    circle((FOOT_CX[1], FOOT_CY), FOOT_R)],
        "labels": [{"at": [W / 2, -1], "text": "A"}, {"at": [W / 2, H + 1], "text": "A"}]
    }
    side_outline = [line((COL_Z[0], 0), (COL_Z[1], 0)), line((COL_Z[1], 0), (COL_Z[1], BASE_TOP)),
                    line((COL_Z[1], BASE_TOP), (D, BASE_TOP)), line((D, BASE_TOP), (D, H)),
                    line((D, H), (0, H)), line((0, H), (0, BASE_TOP)),
                    line((0, BASE_TOP), (COL_Z[0], BASE_TOP)),
                    line((COL_Z[0], BASE_TOP), (COL_Z[0], 0))]
    side = {
        "name": "側面図",
        "grid": {"cols": D, "rows": H, "pitch": 24},
        "lines": side_outline + hole_hidden_lines(hole, side_outline) + [
            line((0, FOOT_CY - FOOT_R), (D, FOOT_CY - FOOT_R), 'hidden'),
            line((0, FOOT_CY + FOOT_R), (D, FOOT_CY + FOOT_R), 'hidden'),
            line((0, HOLE_CY), (D, HOLE_CY), 'center')]
    }
    return add({
        "schemaVersion": 2, "answerMode": "line",
        "id": "sec-a-002", "title": "全断面図 A-A（T 形の台座）",
        "category": "full", "level": 2,
        "instruction": "次の図は、機械部品の投影図である。(答)の箇所に指示された断面図をかきなさい。ハッチングもほどこしなさい。",
        "views": [front, side],
        "answerArea": {"title": "A-A", "grid": {"cols": D, "rows": H, "pitch": 26},
                       "hintLines": [line((0, HOLE_CY), (D, HOLE_CY), 'center')]},
        "answer": {"lines": lines, "hatch": hatch,
                   "tolerance": {"lineJaccard": 0.90, "hatchJaccard": 0.90}},
        "traps": [
            {"tag": "hole-hatched", "check": "hatch-in-cells", "penalty": 15,
             "cells": VOID_CELLS(hole),
             "message": "貫通穴の部分には材料がありません。ハッチングは施しません。"},
            {"tag": "hidden-line-drawn", "check": "line-of-kind", "lineKind": "hidden", "penalty": 10,
             "message": "断面図では、かくれ線は原則として省略します。"},
            {"tag": "off-plane-hole", "check": "segments-present", "penalty": 10,
             "segments": hseg(BASE_TOP + 1, 0, D) + hseg(H - 1, 0, D),
             "message": "底板の取付穴は切断線 A-A 上にないため、この断面には現れません。かくれ線も省略します。"},
            {"tag": "step-missing", "check": "segments-missing", "penalty": 10,
             "segments": hseg(BASE_TOP, 0, COL_Z[0]) + hseg(BASE_TOP, COL_Z[1], D),
             "message": "柱と底板の段差を描き忘れています。柱の脇では底板の上面が切り口の輪郭になります。"}
        ],
        "hints": [
            "切断線 A-A は柱の中心を通っています。左右対称の切り口になります。",
            "柱は底板より奥行が狭いので、切り口には段差が現れます。",
            "柱の貫通穴は切断線上にあるので、切り口が上下に分かれます。ただし穴は柱を幅方向には貫いていないので、柱の外形線は穴の位置でも途切れません。",
            "底板の取付穴は中心線から外れているので、この断面には現れません。"
        ],
        "explain": ("A-A は柱の中心を通る鉛直な切断面です。柱（奥行 4）は底板（奥行 8）より狭いため、"
                    "切り口は T の字を上下反転した形（凸形）になり、柱の両脇に段差が現れます。"
                    "柱の中心には奥行方向の φ3 貫通穴があり、切断線がその中心を通るので、"
                    "柱の切り口（ハッチングを施す部分）は穴を挟んで上下に分かれます。"
                    "ただし穴は柱を幅方向には貫いていないため、切断面の向こう側には穴の内壁が見えます。"
                    "柱の外形線は穴の位置でも途切れません。"
                    "底板の 2 つの取付穴は切断線から外れた位置にあるため、この断面には現れません。"
                    "この問題にはリブがないので、切り口はすべてハッチングを施します。"),
        "authoring": AUTHORING(body, hole, cut)
    })


# ══════════════════════════════════════════════════════════════════
# sec-a-003 段付き軸受
#   奥行 8 × 高さ 12 × 幅 12（回転体）
#   フランジ φ12 ＋ 胴 φ8、内側は φ6 と φ4 の段付き穴
# ══════════════════════════════════════════════════════════════════
def bearing():
    D, H, W = 8, 12, 12
    CY = H // 2                            # 軸線の高さ（row 6）
    FLANGE_R, BODY_R = 6, 4                # φ12 / φ8
    BIG_R, SMALL_R = 3, 2                  # 段付き穴 φ6 / φ4
    FLANGE_D, STEP_D = 2, 3                # フランジの厚さ / 段付き穴の段の位置

    # 段付き穴は回転体の中心にあり、外形を分断しない。外形（body）は円筒をそのまま含む。
    # 穴は「奥行の範囲と半径」で宣言する。段差の線の位置は自動で決まる。
    hole = stepped_hole(CY, [('大径穴 φ6', 0, STEP_D, BIG_R),
                             ('小径穴 φ4', STEP_D, D, SMALL_R)])
    body = sorted(rect(0, FLANGE_D, 0, H) + rect(FLANGE_D, D, CY - BODY_R, CY + BODY_R))
    lines, hatch, cut = make_answer(body, voids=[f['cells'] for f in hole])

    front = {
        "name": "正面図",
        "grid": {"cols": W, "rows": H, "pitch": 24},
        "lines": [line((0, CY), (W, CY), 'center'),
                  line((W / 2, -1), (W / 2, H + 1), 'cut')],
        # 胴 φ8 はフランジ φ12 の後ろに隠れるので、正面図ではかくれ線になる。
        "circles": [circle((W / 2, CY), FLANGE_R), circle((W / 2, CY), BODY_R, 'hidden'),
                    circle((W / 2, CY), BIG_R), circle((W / 2, CY), SMALL_R)],
        "labels": [{"at": [W / 2, -1], "text": "A"}, {"at": [W / 2, H + 1], "text": "A"}]
    }
    side_outline = [line((0, 0), (FLANGE_D, 0)), line((FLANGE_D, 0), (FLANGE_D, CY - BODY_R)),
                    line((FLANGE_D, CY - BODY_R), (D, CY - BODY_R)),
                    line((D, CY - BODY_R), (D, CY + BODY_R)),
                    line((D, CY + BODY_R), (FLANGE_D, CY + BODY_R)),
                    line((FLANGE_D, CY + BODY_R), (FLANGE_D, H)),
                    line((FLANGE_D, H), (0, H)), line((0, H), (0, 0))]
    side = {
        "name": "側面図",
        "grid": {"cols": D, "rows": H, "pitch": 24},
        "lines": side_outline + hole_hidden_lines(hole, side_outline)
                 + [line((0, CY), (D, CY), 'center')]
    }
    return add({
        "schemaVersion": 2, "answerMode": "line",
        "id": "sec-a-003", "title": "全断面図 A-A（段付き軸受）",
        "category": "full", "level": 3,
        "instruction": "次の図は、機械部品の投影図である。(答)の箇所に指示された断面図をかきなさい。ハッチングもほどこしなさい。",
        "views": [front, side],
        "answerArea": {"title": "A-A", "grid": {"cols": D, "rows": H, "pitch": 26},
                       "hintLines": [line((0, CY), (D, CY), 'center')]},
        "answer": {"lines": lines, "hatch": hatch,
                   "tolerance": {"lineJaccard": 0.90, "hatchJaccard": 0.90}},
        "traps": [
            {"tag": "hole-hatched", "check": "hatch-in-cells", "penalty": 15,
             "cells": VOID_CELLS(hole),
             "message": "穴の部分には材料がありません。ハッチングは施しません。"},
            {"tag": "hidden-line-drawn", "check": "line-of-kind", "lineKind": "hidden", "penalty": 10,
             "message": "断面図では、かくれ線は原則として省略します。"},
            {"tag": "step-missing", "check": "segments-missing", "penalty": 15,
             "segments": vseg(STEP_D, CY - BIG_R, CY + BIG_R),
             "message": "段付き穴の段差を描き忘れています。大径 φ6 と小径 φ4 の境目には、穴を横切る輪郭線が現れます。"}
        ],
        "hints": [
            "回転体なので、切り口は軸線をはさんで上下対称になります。",
            "穴は手前が φ6、奥が φ4 の段付きです。境目では見える面が大径穴の壁から小径穴の壁に変わるので、段差の線は穴を横切って引きます。",
            "正面図の φ8 は破線です。フランジの後ろに胴が隠れているので、切り口には段差が現れます。",
            "穴は回転体を分断していません。穴の向こう側の内壁が見えるので、外形線は穴の位置でも途切れません。",
            "かくれ線は省略します。側面図の破線をそのまま写さないこと。"
        ],
        "explain": ("A-A は軸線を含む鉛直な切断面です。回転体なので、切り口は軸線をはさんで上下対称になります。"
                    "外側はフランジ φ12（厚さ 2）と胴 φ8 の 2 段、内側は手前が φ6、奥が φ4 の段付き穴で、"
                    "それぞれの境目に段差の輪郭線が現れます。段差を描き忘れると別の部品になってしまうので、"
                    "側面図のかくれ線で径が変わる位置を確かめてから描きます。"
                    "穴は部品を分断していないため、切断面の向こう側には穴の内壁が見えます。"
                    "その輪郭は実線で描くので、外形線は穴の位置でも途切れません。"
                    "断面図ではかくれ線を省略するので、側面図の破線をそのまま写してはいけません。"
                    "この部品は軸受（穴のあいた側）なので、切り口にはハッチングを施します"
                    "（ハッチングを施さないのは、軸そのものを長手方向に切断した場合です）。"),
        "authoring": AUTHORING(body, hole, cut)
    })


# ══════════════════════════════════════════════════════════════════
bracket(); pedestal(); bearing()

os.makedirs(os.path.join(ROOT, 'docs/samples'), exist_ok=True)
for p in PROBLEMS:
    dst = os.path.join(ROOT, 'docs/samples', p['id'] + '.json')
    io.open(dst, 'w', encoding='utf-8').write(json.dumps(p, ensure_ascii=False, indent=2) + '\n')
    a = p['authoring']
    print('%-10s 外形=%3d  穴=%s  切り口=%3d  ハッチ=%3d  外形線=%3d  → %s'
          % (p['id'], len(a['body']),
             '+'.join('%s(%d)' % (v['name'], len(v['cells'])) for v in a['voids']),
             len(a['cut']), len(p['answer']['hatch']), len(p['answer']['lines']),
             os.path.relpath(dst, ROOT)))

body = '''/**
 * 問題データ。
 *
 * tools/make_problems.py が生成する。直接編集しないこと。
 * Phase 2 でスプレッドシート（problems シート）からの読み込みに差し替える。
 */
var Problems = (function () {

  var ALL = %s;

  function defaultId() {
    return ALL[0].id;
  }

  function list() {
    return ALL.map(function (p) {
      return { id: p.id, title: p.title, category: p.category, level: p.level };
    });
  }

  function get(id) {
    if (!id) id = defaultId();
    for (var i = 0; i < ALL.length; i++) {
      if (ALL[i].id === id) return ALL[i];
    }
    return null;
  }

  return { defaultId: defaultId, list: list, get: get };
})();
''' % json.dumps(PROBLEMS, ensure_ascii=False, indent=2)
io.open(os.path.join(ROOT, 'src/Problems.gs'), 'w', encoding='utf-8').write(body)
print('wrote src/Problems.gs (%d 問)' % len(PROBLEMS))
