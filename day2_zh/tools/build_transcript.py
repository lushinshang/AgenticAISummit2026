#!/usr/bin/env python3
"""把翻譯區塊合併成每個舞台一份的繁中全文 md。

標題與講者區塊一律由 agenda.json 重建（權威），只取區塊檔的譯文本體，
避免各 subagent 產生的標題格式不一致。
"""
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
OUT = TOOLS.parent / "transcript"
STAGES = sys.argv[1:] or ["plenary", "atlas", "compass"]

agenda = json.loads((TOOLS / "agenda.json").read_text(encoding="utf-8"))
manifest = json.loads((TOOLS / "chunks_manifest.json").read_text(encoding="utf-8"))

# 素材原始檔的錯字，輸出時修正
TITLE_FIX = {"軟體工程 the 未來": "軟體工程的未來"}


def clean_title(t):
    for bad, good in TITLE_FIX.items():
        t = t.replace(bad, good)
    return t.replace(" - ", " — ")


LIST_ITEM = re.compile(r"^(?:[-+]\s|\*\s|\d+\.\s)")


def body_of(md_path, is_first):
    """取譯文本體：丟掉 md 自己的 ## 標題與講者條列區塊。
    `**講者名：**` 開頭的發言段是譯文，不可當成條列丟掉。"""
    t = md_path.read_text(encoding="utf-8").strip()
    blocks = [b.strip() for b in re.split(r"\n\s*\n", t) if b.strip()]
    out = []
    for b in blocks:
        if is_first and b.startswith("#"):
            continue
        if is_first and b.startswith("**講者**"):
            continue
        if is_first and all(LIST_ITEM.match(l.strip()) or not l.strip()
                            for l in b.splitlines()):
            continue
        out.append(b)
    return out


OUT.mkdir(parents=True, exist_ok=True)
summary = []

for stage in STAGES:
    st = agenda[stage]
    lines = [
        f"# {st['name_zh']}（{st['name_en']}）繁體中文全文",
        "",
        "代理型 AI 高峰會 2026（Agentic AI Summit 2026）Day 2 — 2026 年 8 月 2 日",
        "",
        "本文由現場錄影的英文自動轉錄稿翻譯而成，依大會議程分節。"
        "講者姓名、職稱與講題以官方議程表為準；錄音轉錄不清之處標有 [?] 記號。",
        "",
        "---",
        "",
    ]

    rows = sorted(
        [m for m in manifest if m["stage"] == stage],
        key=lambda m: (0 if m["part"] == "morning" else 1, m["session_index"]),
    )
    n_sess = n_missing = n_para = 0

    for m in rows:
        si = m["session_index"]
        meta = next(s for s in st["sessions"] if s["index"] == si)
        lines.append(f"## [{meta['time_label']}] {clean_title(meta['title'])}")
        lines.append("")

        if meta["speakers"]:
            lines.append("**講者**")
            lines.append("")
            for p in meta["speakers"]:
                bits = p["name"]
                if p["affiliation"]:
                    bits += f"（{p['affiliation']}）"
                if p["role"] and p["role"] != "講者":
                    bits += f" —— {p['role']}"
                if p["topic"]:
                    bits += f" —— {p['topic']}"
                lines.append(f"- {bits}")
            lines.append("")

        if m["missing"] or m["chunks"] == 0:
            lines.append("> 現場錄影未涵蓋此時段。")
            lines.append("")
            n_missing += 1
        else:
            for n in range(1, m["chunks"] + 1):
                name = f"{m['part']}_s{si:02d}_{n}.md"
                # 標好發言者的版本優先；沒標過的區塊仍用原譯文，不會整份缺角
                md = TOOLS / "speaker_tagged" / stage / name
                if not md.exists():
                    md = TOOLS / "zh_chunks" / stage / name
                if not md.exists():
                    lines.append(f"> 本段第 {n} 塊譯文缺漏。")
                    lines.append("")
                    continue
                paras = body_of(md, n == 1)
                n_para += len(paras)
                for p in paras:
                    lines.append(p)
                    lines.append("")
        n_sess += 1

    dst = OUT / f"{stage}.md"
    dst.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    text = dst.read_text(encoding="utf-8")
    summary.append((stage, n_sess, n_missing, n_para, len(text),
                    text.count("## ["), text.count("轉錄不清")))

print(f"{'舞台':10} {'議程':>4} {'缺稿':>4} {'段落':>5} {'字數':>8} {'H2':>4} {'不清':>5}")
print("-" * 46)
for r in summary:
    print(f"{r[0]:10} {r[1]:4d} {r[2]:4d} {r[3]:5d} {r[4]:8d} {r[5]:4d} {r[6]:5d}")
