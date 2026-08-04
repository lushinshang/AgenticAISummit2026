#!/usr/bin/env python3
"""修正切點錯位：把 start_para 挪到 evidence 引句實際所在的段落，並同步前一筆的 end_para。

錯位來源：部分 subagent 把 jsonl「行號」當成段落 index 寫入，少減 1。
可重複執行（已對齊者不動）。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_segments import en_quotes, ngram_hit  # noqa: E402

TOOLS = Path(__file__).resolve().parent
KEYS = [f"{s}_{p}" for s in ("plenary", "atlas", "compass")
        for p in ("morning", "afternoon")]

total_fixed = 0
for key in KEYS:
    seg_p = TOOLS / "segments" / f"{key}.json"
    paras = [json.loads(l) for l in (TOOLS / "cleaned" / f"{key}.jsonl").open(encoding="utf-8")]
    seg = json.loads(seg_p.read_text(encoding="utf-8"))
    segs = seg["segments"]

    fixed = []
    for s in segs:
        sp = s["start_para"]
        if sp is None:
            continue
        quotes = en_quotes(s.get("evidence", ""))
        if not quotes:
            continue
        hit = None
        for off in (0, -1, 1, -2, 2, -3, 3):
            i = sp + off
            if 0 <= i < len(paras) and any(ngram_hit(q, paras[i]["text"]) >= 0.6 for q in quotes):
                hit = i
                break
        if hit is not None and hit != sp:
            s["start_para"] = hit
            fixed.append((s["session_index"], sp, hit))

    if not fixed:
        continue

    # 依新的 start_para 重建 end_para 鏈
    valid = [s for s in segs if s["start_para"] is not None]
    for a, b in zip(valid, valid[1:]):
        a["end_para"] = b["start_para"] - 1
    valid[-1]["end_para"] = len(paras) - 1

    starts = [s["start_para"] for s in valid]
    assert all(a < b for a, b in zip(starts, starts[1:])), f"{key} 修正後不再遞增"

    seg_p.write_text(json.dumps(seg, ensure_ascii=False, indent=2), encoding="utf-8")
    for si, old, new in fixed:
        print(f"{key:20} 議程 {si:2d}  start_para {old} → {new}")
    total_fixed += len(fixed)

print(f"\n共修正 {total_fixed} 筆切點")
