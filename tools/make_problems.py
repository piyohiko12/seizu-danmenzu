# -*- coding: utf-8 -*-
"""問題データを部品形状の定義から組み立てる。

    python3 tools/make_problems.py

docs/samples/<id>.json を書き出し、src/Problems.gs を作り直す。

部品の形は tools/solid.py の Part に**一度だけ**宣言する。
正面図・側面図・断面図はすべてそこから導かれるので、
中心線の描き忘れ・見え掛かり線の描き漏れ・3 面の食い違いが起きない。
座標を手で並べてはいけない。
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from problem_lib import slope_cells, make_answer, hseg, vseg, line
from solid import Part

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS = []


def add(p):
    PROBLEMS.append(p)
    return p


def AUTHORING(body, hole, cut, part=None):
    """検算に使う作問データ。

    body  … 断面図に現れる部品の外形
    voids … 切断面で材料が無い部分。Part.hole() が面ごとに分けたもの（奥行と半径つき）
    cut   … 切り口 = body − voids
    """
    return {
        "body": [[c, r, sh] for c, r, sh in sorted(body)],
        "voids": [{"name": f["name"], "z": list(f["z"]), "r": f["r"],
                   "cells": sorted([list(c) for c in f["cells"]])} for f in hole],
        "cut": [[c, r, sh] for c, r, sh in sorted(cut)],
        "round": part.round_features() if part else [],
        "note": ("tools/make_problems.py が生成。部品は tools/solid.py の Part に一度だけ宣言し、"
                 "正面図・側面図・断面図をそこから導いている。穴は奥行と半径で宣言し、"
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
    RIB_A, RIB_B = (2, 9), (6, 13)
    RIB_X = (4, 6)                             # リブの幅方向の位置
    CUT = W / 2
    HOLE_CY, FOOT_CY = 5.5, 14.5

    rib = slope_cells(RIB_A, RIB_B, BASE_TOP)
    part = Part(W, H, D)
    part.box('縦板', x=(0, W), y=(0, BASE_TOP), z=(0, PLATE))
    part.box('底板', x=(0, W), y=(BASE_TOP, H), z=(0, D))
    part.prism('リブ', x=RIB_X, profile=rib)
    part.hole('中心の穴', CUT, HOLE_CY,
              [('座ぐり φ5', 0, 1, 2.5), ('貫通穴 φ3', 1, PLATE, 1.5)])
    part.hole('取付穴 φ2 左', 2.5, FOOT_CY, [('φ2', 0, D, 1.0)])
    part.hole('取付穴 φ2 右', 7.5, FOOT_CY, [('φ2', 0, D, 1.0)])

    body, hole = part.section_at(CUT)
    lines, hatch, cut = make_answer(body, voids=[s['cells'] for s in hole],
                                    outline_extra=[rib],
                                    hatch_exclude=[(c, r) for c, r, _ in rib])
    front = part.front_view(pitch=24, cut_x=CUT)
    side = part.side_view(pitch=24)

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
        "authoring": AUTHORING(body, hole, cut, part)
    })


# ══════════════════════════════════════════════════════════════════
# sec-a-002 T 形の台座
#   奥行 8 × 高さ 12 × 幅 12
#   底板の上に細い柱が立つ左右対称の部品。柱に奥行方向の貫通穴
# ══════════════════════════════════════════════════════════════════
def pedestal():
    D, H, W = 8, 12, 12
    BASE_TOP = 9                              # 底板の上面
    COL_Z, COL_X = (2, 6), (4, 8)             # 柱の奥行 / 幅
    CUT = W / 2
    HOLE_CY, FOOT_CY = 4.5, 10.5

    part = Part(W, H, D)
    part.box('底板', x=(0, W), y=(BASE_TOP, H), z=(0, D))
    part.box('柱',   x=COL_X, y=(0, BASE_TOP), z=COL_Z)
    part.hole('柱の貫通穴 φ3', CUT, HOLE_CY, [('φ3', COL_Z[0], COL_Z[1], 1.5)])
    part.hole('取付穴 φ2 左',  2.0, FOOT_CY, [('φ2', 0, D, 1.0)])
    part.hole('取付穴 φ2 右', 10.0, FOOT_CY, [('φ2', 0, D, 1.0)])

    body, hole = part.section_at(CUT)
    lines, hatch, cut = make_answer(body, voids=[s['cells'] for s in hole])
    front = part.front_view(pitch=24, cut_x=CUT)
    side = part.side_view(pitch=24)

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
        "authoring": AUTHORING(body, hole, cut, part)
    })


# ══════════════════════════════════════════════════════════════════
# sec-a-003 段付き軸受
#   奥行 8 × 高さ 12 × 幅 12（回転体）
#   フランジ φ12 ＋ 胴 φ8、内側は φ6 と φ4 の段付き穴
# ══════════════════════════════════════════════════════════════════
def bearing():
    D, H, W = 8, 12, 12
    CY = H // 2                                # 軸線の高さ
    FLANGE_R, BODY_R = 6, 4                    # φ12 / φ8
    BIG_R, SMALL_R = 3, 2                      # 段付き穴 φ6 / φ4
    FLANGE_D, STEP_D = 2, 3                    # フランジの厚さ / 段の位置
    CUT = W / 2

    part = Part(W, H, D)
    part.cyl('フランジ φ12', CUT, CY, FLANGE_R, z=(0, FLANGE_D))
    part.cyl('胴 φ8',        CUT, CY, BODY_R,   z=(FLANGE_D, D))
    part.hole('段付き穴', CUT, CY, [('大径穴 φ6', 0, STEP_D, BIG_R),
                                    ('小径穴 φ4', STEP_D, D, SMALL_R)])

    body, hole = part.section_at(CUT)
    lines, hatch, cut = make_answer(body, voids=[s['cells'] for s in hole])
    front = part.front_view(pitch=24, cut_x=CUT)
    side = part.side_view(pitch=24)

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
        "authoring": AUTHORING(body, hole, cut, part)
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
