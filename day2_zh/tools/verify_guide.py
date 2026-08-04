#!/usr/bin/env python3
"""查核導讀：檔案齊全、首行與來源一致、禁用詞、簡體字、標點、篇幅。"""
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from verify_zh import CN_TERMS, SIMPLIFIED  # noqa: E402

STAGES = sys.argv[1:] or ["plenary", "atlas", "compass"]

# sections/ 是可重生的中繼檔（歸檔時會被清掉），缺了就自動從 transcript/ 重建
if not (TOOLS / "sections").exists():
    import subprocess
    print("sections/ 不存在，先執行 split_sections.py 重建…")
    subprocess.run([sys.executable, str(TOOLS / "split_sections.py")],
                   check=True, capture_output=True)

manifest = json.loads((TOOLS / "sections_manifest.json").read_text(encoding="utf-8"))

# 規格禁用的空洞詞彙。「閉環／開環」在自駕與控制領域是 closed-loop/open-loop
# 的正確術語，只有當作商業空話時才算違規，故排除技術語境
BANNED = re.compile(r"降維打擊|靈魂拷問|底層共謀|顆粒度|拉齊|抓手|賦能"
                    r"|閉環(?!駕駛|評估|測試|控制|模擬|擴展|訓練)")
# 寫作技法名稱外露
CRAFT = re.compile(r"痛點錨定|問題升級|機制解構|深層洞察|開場變體|反直覺結論開場|數字落差開場|時代斷點開場|具體場景開場")
HALF_PUNCT = re.compile(r"(?<=[一-鿿])[,;?!]|(?<=[一-鿿])\.(?=\s|$)")

rows, problems = [], []
for m in manifest:
    if m["stage"] not in STAGES:
        continue
    stage, si = m["stage"], m["session_index"]
    src = TOOLS / "sections" / stage / f"s{si:02d}.md"
    dst = TOOLS / "guide_chunks" / stage / f"s{si:02d}.md"
    tag = f"{stage}/s{si:02d}"
    if not dst.exists():
        problems.append(f"{tag}：缺輸出檔")
        continue

    t = dst.read_text(encoding="utf-8")
    src_head = src.read_text(encoding="utf-8").splitlines()[0].strip()
    dst_head = t.splitlines()[0].strip()
    if src_head != dst_head:
        problems.append(f"{tag}：首行不符\n      來源 {src_head}\n      導讀 {dst_head}")

    for name, pat in (("空洞詞", BANNED), ("技法名", CRAFT),
                      ("大陸用語", CN_TERMS), ("簡體字", SIMPLIFIED)):
        hit = sorted(set(pat.findall(t)))
        if hit:
            problems.append(f"{tag}：{name} {''.join(hit)}")
    hp = HALF_PUNCT.findall(t)
    if hp:
        problems.append(f"{tag}：中文間半形標點 {len(hp)} 處")

    ratio = len(t) / m["chars"]
    rows.append((tag, m["chars"], len(t), ratio, m["title"][:26]))

print(f"{'議程':16} {'全文':>8} {'導讀':>7} {'比例':>6}  標題")
print("-" * 74)
for r in rows:
    print(f"{r[0]:16} {r[1]:8d} {r[2]:7d} {r[3]:6.1%}  {r[4]}")
print("-" * 74)
print(f"{'合計':16} {sum(r[1] for r in rows):8d} {sum(r[2] for r in rows):7d} "
      f"{sum(r[2] for r in rows) / sum(r[1] for r in rows):6.1%}")

if problems:
    print(f"\n問題 {len(problems)} 項：")
    for p in problems:
        print("  ⚠", p)
else:
    print("\n全部通過")
sys.exit(1 if problems else 0)
