#!/usr/bin/env python3
"""把每個議程切成可單次翻譯的區塊，產出 chunks/<stage>/<part>_s<議程>_<序號>.json 與 manifest。

分塊只在段落邊界切，且每塊上限 MAX_WORDS 英文字，避免單一 subagent 輸出超量。
"""
import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
STAGES = ("plenary", "atlas", "nexus", "compass")
PARTS = ("morning", "afternoon")
MAX_WORDS = 5000

agenda = json.loads((TOOLS / "agenda.json").read_text(encoding="utf-8"))
OUT = TOOLS / "chunks"
manifest = []

for stage in STAGES:
    (OUT / stage).mkdir(parents=True, exist_ok=True)
    for part in PARTS:
        paras = [json.loads(l) for l in
                 (TOOLS / "cleaned" / f"{stage}_{part}.jsonl").open(encoding="utf-8")]
        seg = json.loads((TOOLS / "segments" / f"{stage}_{part}.json").read_text(encoding="utf-8"))
        sess_by_idx = {s["index"]: s for s in agenda[stage]["sessions"]}

        for s in seg["segments"]:
            si = s["session_index"]
            meta = sess_by_idx[si]
            if s["start_para"] is None:
                manifest.append({
                    "stage": stage, "part": part, "session_index": si,
                    "time": meta["time_label"], "title": meta["title"],
                    "kind": meta["kind"], "chunks": 0, "words": 0, "missing": True,
                })
                continue

            body = paras[s["start_para"]:s["end_para"] + 1]
            # 依段落累積切塊
            blocks, cur, cur_w = [], [], 0
            for p in body:
                w = len(p["text"].split())
                if cur and cur_w + w > MAX_WORDS:
                    blocks.append(cur)
                    cur, cur_w = [], 0
                cur.append(p)
                cur_w += w
            if cur:
                blocks.append(cur)

            for n, blk in enumerate(blocks, 1):
                fn = OUT / stage / f"{part}_s{si:02d}_{n}.json"
                fn.write_text(json.dumps({
                    "stage": stage,
                    "stage_name_zh": agenda[stage]["name_zh"],
                    "part": part,
                    "session_index": si,
                    "chunk": n,
                    "chunk_total": len(blocks),
                    "is_first_chunk": n == 1,
                    "time_label": meta["time_label"],
                    "title": meta["title"],
                    "kind": meta["kind"],
                    "speakers": meta["speakers"],
                    "paragraphs": [p["text"] for p in blk],
                }, ensure_ascii=False, indent=2), encoding="utf-8")

            manifest.append({
                "stage": stage, "part": part, "session_index": si,
                "time": meta["time_label"], "title": meta["title"],
                "kind": meta["kind"], "chunks": len(blocks),
                "words": sum(len(p["text"].split()) for p in body), "missing": False,
            })

(TOOLS / "chunks_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"{'舞台':10} {'議程':>4} {'缺稿':>4} {'區塊':>4} {'英文字數':>9}")
print("-" * 40)
for stage in STAGES:
    rows = [m for m in manifest if m["stage"] == stage]
    print(f"{stage:10} {len(rows):4d} {sum(m['missing'] for m in rows):4d} "
          f"{sum(m['chunks'] for m in rows):4d} {sum(m['words'] for m in rows):9d}")
print("-" * 40)
print(f"{'合計':10} {len(manifest):4d} {sum(m['missing'] for m in manifest):4d} "
      f"{sum(m['chunks'] for m in manifest):4d} {sum(m['words'] for m in manifest):9d}")
