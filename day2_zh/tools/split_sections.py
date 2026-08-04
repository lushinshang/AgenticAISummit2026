#!/usr/bin/env python3
"""把合併好的舞台全文再切成一議程一檔，供導讀派工使用。"""
import json
import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
TR = TOOLS.parent / "transcript"
OUT = TOOLS / "sections"
agenda = json.loads((TOOLS / "agenda.json").read_text(encoding="utf-8"))

# 招待會、休息、午餐這類沒有演講內容的節不做導讀
SKIP = ("休息", "午餐", "招待會", "海報", "交流酒會")
manifest = []

for stage in ("plenary", "atlas", "compass"):
    (OUT / stage).mkdir(parents=True, exist_ok=True)
    text = (TR / f"{stage}.md").read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## ", text)[1:]
    sess = {s["index"]: s for s in agenda[stage]["sessions"]}

    for sec in sections:
        head = sec.splitlines()[0].strip()
        m = re.match(r"\[(.+?)\]\s*(.+)", head)
        time_label, title = m.group(1), m.group(2)
        idx = next((i for i, s in sess.items()
                    if s["time_label"] == time_label), None)
        body = sec[len(sec.splitlines()[0]):].strip()

        skip = any(k in title for k in SKIP) or len(body) < 500
        if skip:
            continue

        fn = OUT / stage / f"s{idx:02d}.md"
        fn.write_text(f"## [{time_label}] {title}\n\n{body}\n", encoding="utf-8")
        manifest.append({
            "stage": stage, "session_index": idx, "time_label": time_label,
            "title": title, "chars": len(body), "file": str(fn.relative_to(TOOLS.parent.parent)),
        })

(TOOLS / "sections_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"{'舞台':10} {'議程數':>6} {'總字數':>9} {'最小':>7} {'最大':>7}")
print("-" * 44)
for stage in ("plenary", "atlas", "compass"):
    rows = [m for m in manifest if m["stage"] == stage]
    cs = [m["chars"] for m in rows]
    print(f"{stage:10} {len(rows):6d} {sum(cs):9d} {min(cs):7d} {max(cs):7d}")
print("-" * 44)
print(f"{'合計':10} {len(manifest):6d} {sum(m['chars'] for m in manifest):9d}")
