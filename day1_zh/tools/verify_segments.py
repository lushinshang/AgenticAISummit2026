#!/usr/bin/env python3
"""獨立查核 segments/*.json：結構、覆蓋、單調性，以及 evidence 引句是否真的出現在該段原文。"""
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
KEYS = [f"{s}_{p}" for s in ("plenary", "atlas", "nexus", "compass")
        for p in ("morning", "afternoon")]

fail = 0


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def en_quotes(evidence):
    """從 evidence 抽出英文引句片段；agent 常用 ... 拼接，故拆成多段各自比對。"""
    out = []
    for chunk in re.split(r"\.{3}|…", evidence):
        runs = re.findall(r"[A-Za-z0-9'’,.\- ]{15,}", chunk)
        if runs:
            out.append(max(runs, key=len).strip())
    return out


def ngram_hit(quote, text, n=5):
    """quote 的 n-gram 有多少比例出現在 text（容忍 agent 引用時的小改寫）。"""
    q, t = norm(quote).split(), norm(text)
    if len(q) < n:
        return 1.0 if norm(quote).strip() in t else 0.0
    grams = [" ".join(q[i:i + n]) for i in range(len(q) - n + 1)]
    return sum(1 for g in grams if g in t) / len(grams)


def main():
    global fail
    print(f"{'檔案':22} {'議程':>4} {'對應':>4} {'遞增':>4} {'鏈接':>4} {'總段':>5} {'evidence查核':>12}")
    print("-" * 66)

    for key in KEYS:
        seg_p = TOOLS / "segments" / f"{key}.json"
        ag_p = TOOLS / "agenda_split" / f"{key}.json"
        jl_p = TOOLS / "cleaned" / f"{key}.jsonl"
        if not seg_p.exists():
            print(f"{key:22} 缺檔")
            fail += 1
            continue

        seg = json.loads(seg_p.read_text(encoding="utf-8"))
        ag = json.loads(ag_p.read_text(encoding="utf-8"))
        paras = [json.loads(l) for l in jl_p.open(encoding="utf-8")]

        segs = seg["segments"]
        ag_idx = [s["index"] for s in ag["sessions"]]
        seg_idx = [s["session_index"] for s in segs]
        ok_map = ag_idx == seg_idx

        starts = [s["start_para"] for s in segs if s["start_para"] is not None]
        ok_inc = all(a < b for a, b in zip(starts, starts[1:]))

        valid = [s for s in segs if s["start_para"] is not None]
        ok_chain = True
        for a, b in zip(valid, valid[1:]):
            if a["end_para"] != b["start_para"] - 1:
                ok_chain = False
        if valid and valid[-1]["end_para"] != len(paras) - 1:
            ok_chain = False

        ok_total = seg.get("total_paragraphs") == len(paras)

        # evidence 逐筆回頭比對原文；命中在鄰近段落者視為切點錯位，另行標示
        ev_ok = ev_all = 0
        ev_bad, ev_shift = [], []
        for s in valid:
            quotes = en_quotes(s.get("evidence", ""))
            if not quotes:
                continue
            ev_all += 1
            sp = s["start_para"]
            hit_at = None
            for off in (0, -1, 1, -2, 2, -3, 3):
                i = sp + off
                if not (0 <= i < len(paras)):
                    continue
                if any(ngram_hit(q, paras[i]["text"]) >= 0.6 for q in quotes):
                    hit_at = i
                    break
            if hit_at == sp:
                ev_ok += 1
            elif hit_at is not None:
                ev_shift.append((s["session_index"], sp, hit_at))
            else:
                ev_bad.append((s["session_index"], quotes[0][:50]))

        mark = lambda b: "OK" if b else "!!"
        print(f"{key:22} {len(segs):4d} {mark(ok_map):>4} {mark(ok_inc):>4} "
              f"{mark(ok_chain):>4} {mark(ok_total):>5} {ev_ok:>6}/{ev_all:<5}")

        if not (ok_map and ok_inc and ok_chain and ok_total):
            fail += 1
        for si, sp, hit in ev_shift:
            print(f"    ↔ 議程 {si} 切點錯位：start_para={sp}，evidence 實際落在 {hit}（差 {hit - sp:+d}）")
        for si, q in ev_bad:
            print(f"    ⚠ 議程 {si} 的 evidence 在該段原文查不到：{q!r}")
            fail += 1

    print("-" * 66)
    print("全部通過" if fail == 0 else f"有 {fail} 項未通過")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
