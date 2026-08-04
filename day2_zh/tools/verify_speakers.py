#!/usr/bin/env python3
"""查核發言者標註：文字必須零損失，只准多出 `**姓名：** ` 前綴與換行。

比對方式是把標註版的前綴拿掉、所有空白去掉，再跟原譯文做同樣處理後比字串——
只要有一個字被改寫、補寫或刪掉就會現形。
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS / "zh_chunks"
TAGGED = TOOLS / "speaker_tagged"
STAGES = ("plenary", "atlas", "compass")

# 判不出真名時允許的代號（規格 SPEAKER_SPEC.md 定義）
ROLE_OK = re.compile(r"^(主持人|提問者|工作人員|觀眾)\s?[A-Z]?$|"
                     r"^(與談人|講者|簡報者)\s?[A-Z]?$|"
                     r"^[A-Za-z][\w .&'-]*\s?(講者|簡報者)\s?[A-Z]?$|"
                     r"^新創簡報者$")


def agenda_names():
    """議程表列出的所有講者姓名（正規化後比對，避免全形空格與撇號差異）。"""
    ag = json.loads((TOOLS / "agenda.json").read_text(encoding="utf-8"))
    out = set()
    for st in ag.values():
        for sess in st.get("sessions", []):
            for sp in sess.get("speakers", []):
                out.add(unicodedata.normalize("NFKC", sp["name"]).replace("’", "'").strip())
    return out

# 行首的發言者標記：**姓名：** 後面接一個空格
PREFIX = re.compile(r"^\*\*([^*\n]{1,40}?)：\*\*[ \t]*", re.M)
WS = re.compile(r"\s+")


def strip_tags(text):
    return PREFIX.sub("", text)


LIST = re.compile(r"^(?:[-+]\s|\*\s|\d+\.\s)")


def norm(text):
    """比對基準要跟 build_transcript.body_of 一致：

    `##` 標題與 `**講者**` 條列在合併時一律由 agenda.json 重建，
    標註版留不留都不影響成品，所以比對前先剝掉，否則會誤報「文字被改動」。
    """
    keep = []
    for b in re.split(r"\n\s*\n", text.strip()):
        b = b.strip()
        if not b or b.startswith("#") or b.startswith("**講者**"):
            continue
        if all(LIST.match(l.strip()) or not l.strip() for l in b.splitlines()):
            continue
        keep.append(b)
    return WS.sub("", strip_tags("\n\n".join(keep)))


def speakers_in(text):
    return [m.group(1) for m in PREFIX.finditer(text)]


def main():
    rows, problems = [], []
    known = agenda_names()
    unknown = {}   # 不在議程表、也不是合法代號的名字 -> 出現在哪些區塊
    for stage in STAGES:
        for src in sorted((SRC / stage).glob("*.md")):
            dst = TAGGED / stage / src.name
            if not dst.exists():
                problems.append(f"{stage}/{src.stem}：缺標註輸出")
                continue
            a = src.read_text(encoding="utf-8")
            b = dst.read_text(encoding="utf-8")

            na, nb = norm(a), norm(b)
            if na != nb:
                # 找出第一個相異位置，方便回頭查
                i = next((k for k in range(min(len(na), len(nb))) if na[k] != nb[k]),
                         min(len(na), len(nb)))
                problems.append(
                    f"{stage}/{src.stem}：文字被改動（原 {len(na)} 字 → 標註後 {len(nb)} 字）"
                    f"，第一處差異在第 {i} 字附近：原「{na[max(0,i-15):i+15]}」"
                    f" vs 新「{nb[max(0,i-15):i+15]}」")
                continue

            names = speakers_in(b)
            if not names:
                problems.append(f"{stage}/{src.stem}：完全沒有標註任何發言者")
                continue
            # 標記若混進正文（不在行首）會被上面的 norm 吃掉，這裡另外抓明顯異常
            if any(len(n) > 30 for n in names):
                problems.append(f"{stage}/{src.stem}：有異常長的發言者名稱 {[n for n in names if len(n) > 30]}")

            uniq = sorted(set(names))
            for n in uniq:
                key = unicodedata.normalize("NFKC", n).replace("’", "'").strip()
                if key not in known and not ROLE_OK.match(key):
                    unknown.setdefault(n, []).append(f"{stage}/{src.stem}")
            rows.append((stage, src.stem, len(names), len(uniq), uniq))

    print(f"{'舞台':9} {'區塊':22} {'標註數':>6} {'人數':>5}  發言者")
    print("-" * 96)
    for stage, name, n, u, uniq in rows:
        shown = "、".join(uniq[:4]) + ("…" if len(uniq) > 4 else "")
        print(f"{stage:9} {name:22} {n:6d} {u:5d}  {shown}")
    print("-" * 96)
    print(f"合計 {len(rows)} 個區塊，標註 {sum(r[2] for r in rows)} 次")

    if unknown:
        print(f"\n議程表查無、也不是合法代號的名字 {len(unknown)} 個："
              "（拼法可能與議程表不符，或是名單外人物）")
        for n, where in sorted(unknown.items()):
            print(f"  ? {n:32} 出現於 {'、'.join(where[:3])}"
                  f"{f'…等 {len(where)} 處' if len(where) > 3 else ''}")

    if problems:
        print(f"\n問題 {len(problems)} 項：")
        for p in problems:
            print("  ⚠", p)
    else:
        print("\n全部通過：譯文零改動")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
