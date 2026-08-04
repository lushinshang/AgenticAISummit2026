#!/usr/bin/env python3
"""把各議程導讀合併成每個舞台一份的主題式導讀 md。"""
import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
OUT = TOOLS.parent / "guide"
agenda = json.loads((TOOLS / "agenda.json").read_text(encoding="utf-8"))
manifest = json.loads((TOOLS / "sections_manifest.json").read_text(encoding="utf-8"))

OUT.mkdir(parents=True, exist_ok=True)
summary = []

for stage in ("plenary", "atlas", "nexus", "compass"):
    st = agenda[stage]
    rows = sorted([m for m in manifest if m["stage"] == stage],
                  key=lambda m: m["session_index"])
    lines = [
        f"# {st['name_zh']}（{st['name_en']}）主題式導讀",
        "",
        "代理型 AI 高峰會 2026（Agentic AI Summit 2026）Day 1 — 2026 年 8 月 1 日",
        "",
        f"本文為 {st['name_zh']}當日 {len(rows)} 場議程的深度導讀，逐場梳理講者的核心主張與論點推進，"
        "供快速掌握全貌之用。完整內容請見同場次的繁體中文全文。",
        "",
        "---",
        "",
    ]

    n_ok = 0
    for m in rows:
        md = TOOLS / "guide_chunks" / stage / f"s{m['session_index']:02d}.md"
        if not md.exists():
            lines += [f"## [{m['time_label']}] {m['title']}", "", "> 本場導讀尚未產出。", ""]
            continue
        lines.append(md.read_text(encoding="utf-8").strip())
        lines.append("")
        n_ok += 1

    dst = OUT / f"{stage}.md"
    dst.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    text = dst.read_text(encoding="utf-8")
    summary.append((stage, len(rows), n_ok, text.count("\n## "), len(text)))

print(f"{'舞台':10} {'議程':>4} {'已產':>4} {'H2':>4} {'字數':>8}")
print("-" * 36)
for r in summary:
    print(f"{r[0]:10} {r[1]:4d} {r[2]:4d} {r[3]:4d} {r[4]:8d}")
print("-" * 36)
print(f"{'合計':10} {sum(r[1] for r in summary):4d} {sum(r[2] for r in summary):4d} "
      f"{sum(r[3] for r in summary):4d} {sum(r[4] for r in summary):8d}")
