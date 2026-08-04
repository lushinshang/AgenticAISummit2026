#!/usr/bin/env python3
"""把譯文中夾在中文之間的半形標點統一成全形，各 subagent 的習慣不一致。

只在「中文字」為錨點時轉換，避免動到英文句子、數字（1,000）、版本號（3.5）、
markdown 語法與 <!-- 註解 -->。可重複執行。
"""
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
STAGES = sys.argv[1:] or ["plenary", "atlas", "compass"]

CJK = r"[一-鿿　-〿）」』】]"
CJK_AHEAD = r"[一-鿿（「『【]"

# (說明, pattern, 取代)
RULES = [
    ("逗號-前錨", re.compile(rf"({CJK}),"), r"\1，"),
    ("逗號-後錨", re.compile(rf",(?={CJK_AHEAD})"), "，"),
    ("句號-前錨", re.compile(rf"({CJK})\.(?=\s|$|{CJK_AHEAD})"), r"\1。"),
    ("問號", re.compile(rf"({CJK})\?"), r"\1？"),
    ("驚嘆號", re.compile(rf"({CJK})!"), r"\1！"),
    ("分號", re.compile(rf"({CJK});"), r"\1；"),
    ("冒號", re.compile(rf"({CJK}):(?!\d)"), r"\1："),
    ("頓號誤用", re.compile(rf"({CJK})/(?={CJK_AHEAD})"), r"\1、"),
    # 英文/數字接中文時的半形標點（例：iPhone;2035年）
    ("分號-後錨", re.compile(rf"(?<=[\w]);(?={CJK_AHEAD})"), "；"),
    ("問號-後錨", re.compile(rf"(?<=[\w])\?(?={CJK_AHEAD})"), "？"),
    ("驚嘆-後錨", re.compile(rf"(?<=[\w])!(?={CJK_AHEAD})"), "！"),
]

changed_files = 0
totals = {}
for stage in STAGES:
    d = TOOLS / "guide_chunks" / stage
    if not d.exists():
        continue
    for md in sorted(d.glob("*.md")):
        t0 = md.read_text(encoding="utf-8")
        # 保護 <!-- 註解 --> 不被動到
        guards = []

        def stash(m):
            guards.append(m.group(0))
            return f"\x00{len(guards) - 1}\x00"

        t = re.sub(r"<!--.*?-->", stash, t0, flags=re.S)

        n_file = 0
        for name, pat, rep in RULES:
            t, n = pat.subn(rep, t)
            if n:
                totals[name] = totals.get(name, 0) + n
                n_file += n

        t = re.sub(r"\x00(\d+)\x00", lambda m: guards[int(m.group(1))], t)
        if t != t0:
            md.write_text(t, encoding="utf-8")
            changed_files += 1
            print(f"{stage}/{md.stem:24} 修正 {n_file} 處")

print(f"\n共修改 {changed_files} 個檔案")
for k, v in sorted(totals.items(), key=lambda x: -x[1]):
    print(f"  {k:10} {v:6d}")
