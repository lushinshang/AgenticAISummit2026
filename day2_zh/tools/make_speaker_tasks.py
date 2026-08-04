#!/usr/bin/env python3
"""為每個譯文區塊產生「發言者判讀」派工檔：講者名單 + 英文原文 + 譯文並排。

輸出 speaker_tasks/<stage>/<chunk>.md，subagent 讀這一個檔就有全部判斷材料。
段號以譯文段落為準——最終要標註的是譯文，段數必須對得上。
"""
import json
import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
OUT = TOOLS / "speaker_tasks"
STAGES = ("plenary", "atlas", "compass")

# 標題、講者清單、缺稿提示都不是發言段落
META = re.compile(r"^(#{1,6}\s|\*\*講者\*\*|>|-\s|\d+\.\s|\*\s)")


def body_paras(md_text):
    """取出譯文裡真正的發言段落（順序不變）。"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", md_text.strip()) if b.strip()]
    return [b for b in blocks if not META.match(b)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for stage in STAGES:
        (OUT / stage).mkdir(parents=True, exist_ok=True)
        for src in sorted((TOOLS / "chunks" / stage).glob("*.json")):
            meta = json.loads(src.read_text(encoding="utf-8"))
            zh_path = TOOLS / "zh_chunks" / stage / f"{src.stem}.md"
            if not zh_path.exists():
                continue
            zh = body_paras(zh_path.read_text(encoding="utf-8"))
            en = meta["paragraphs"]

            lines = [
                f"# 發言者判讀：{stage} / {src.stem}",
                "",
                f"**議程**：[{meta['time_label']}] {meta['title']}",
                f"**區塊**：第 {meta['chunk']} 塊（共 {meta['chunk_total']} 塊）"
                f"{'　※ 本場第一塊' if meta['is_first_chunk'] else ''}",
                "",
                "## 講者名單（姓名以此為準）",
                "",
            ]
            if meta["speakers"]:
                for sp in meta["speakers"]:
                    bits = [sp["name"]]
                    if sp.get("affiliation"):
                        bits.append(sp["affiliation"])
                    if sp.get("role"):
                        bits.append(sp["role"])
                    if sp.get("topic"):
                        bits.append(f"講題：{sp['topic']}")
                    lines.append("- " + "｜".join(bits))
            else:
                lines.append("- （議程表未列講者）")

            lines += ["", f"## 段落（共 {len(zh)} 段）", ""]
            for i, para in enumerate(zh, 1):
                lines.append(f"### 第 {i} 段")
                lines.append("")
                lines.append("英文原文：")
                lines.append("")
                lines.append(en[i - 1] if i - 1 < len(en) else "（英文段數不足，僅憑譯文判斷）")
                lines.append("")
                lines.append("譯文：")
                lines.append("")
                lines.append(para)
                lines.append("")

            dst = OUT / stage / f"{src.stem}.md"
            dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
            rows.append((stage, src.stem, len(zh), len(en), len(meta["speakers"])))

    print(f"{'舞台':9} {'區塊':22} {'譯文段':>6} {'英文段':>6} {'講者':>5}")
    print("-" * 54)
    for r in rows:
        flag = "" if r[2] == r[3] else "  ← 段數不一致"
        print(f"{r[0]:9} {r[1]:22} {r[2]:6d} {r[3]:6d} {r[4]:5d}{flag}")
    print("-" * 54)
    print(f"共 {len(rows)} 個派工檔，譯文段合計 {sum(r[2] for r in rows)}")


if __name__ == "__main__":
    main()
