#!/usr/bin/env python3
"""查核翻譯區塊：檔案齊全、段落沒短少、標題規則、大陸用語、殘留英文句子。"""
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
STAGES = sys.argv[1:] or ["plenary", "atlas", "compass"]

# 「質量」在物理語境（mass）正確、「用戶端」是 HTTP client 的台灣標準譯法，故排除
CN_TERMS = re.compile(
    r"軟件|程序員|數據|網絡|默認|視頻|音頻|信息|項目經理|激活|緩存|內存|硬盤"
    r"|用戶(?!端)|性能(?!組|力)|智能體|幻燈片|鼠標|優盤|字節|博客|郵箱")
# 簡體字形（繁體文本中不該出現）。只列繁簡字形確實不同的字，避免誤判
SIMPLIFIED = re.compile(
    "[试论说话语这么产开关问题东车动书门长风马鸟华实见觉学习为无还进"
    "样时间点数据网络计发现应该过种类别处结务际标级组织资讯认识证议"
    "决权变转单双击图运营员将带务经历题连续录规则说导构总统]")
# 連續英文句子（4 個以上英文單字且含句點）視為未翻譯殘留
EN_SENT = re.compile(r"[A-Za-z][A-Za-z'’\-]*(?:\s+[A-Za-z'’\-]+){5,}[.?!]")

# subagent 回傳時偶爾漏刪外層包裝標籤（實測 plenary.md 殘留兩處 </content>）
WRAPPER_TAG = re.compile(r"</?(?:content|output|translation|answer|result|response|thinking)\b[^>]*>", re.I)

LIST_ITEM = re.compile(r"^(?:[-+]\s|\*\s|\d+\.\s)")


def is_meta_block(b):
    """標題、講者標記、條列區塊都不是譯文段落。
    注意：`**講者名：**` 開頭的發言段是譯文，不可誤判成條列。"""
    s = b.lstrip()
    if s.startswith("#") or s.startswith("**講者**"):
        return True
    return all(LIST_ITEM.match(l.strip()) or not l.strip() for l in b.splitlines())


def main():
    rows, problems = [], []
    for stage in STAGES:
        for src in sorted((TOOLS / "chunks" / stage).glob("*.json")):
            meta = json.loads(src.read_text(encoding="utf-8"))
            dst = TOOLS / "zh_chunks" / stage / f"{src.stem}.md"
            if not dst.exists():
                problems.append(f"{stage}/{src.stem}：缺輸出檔")
                continue
            t = dst.read_text(encoding="utf-8")
            blocks = [b for b in re.split(r"\n\s*\n", t.strip()) if b.strip()]
            # 標題區塊、講者標記、條列區塊都不算譯文段落
            body = len([b for b in blocks if not is_meta_block(b)])
            n_in = len(meta["paragraphs"])

            has_h2 = t.lstrip().startswith("##")
            if meta["is_first_chunk"] and not has_h2:
                problems.append(f"{stage}/{src.stem}：首塊缺 ## 標題")
            if not meta["is_first_chunk"] and has_h2:
                problems.append(f"{stage}/{src.stem}：非首塊卻有 ## 標題")
            if body < n_in:
                problems.append(f"{stage}/{src.stem}：段落短少（輸入 {n_in} → 輸出 {body}）")

            cn = sorted(set(CN_TERMS.findall(t)))
            if cn:
                problems.append(f"{stage}/{src.stem}：大陸用語 {cn}")
            sim = sorted(set(SIMPLIFIED.findall(t)))
            if sim:
                problems.append(f"{stage}/{src.stem}：簡體字 {''.join(sim)}（共 "
                                f"{len(SIMPLIFIED.findall(t))} 字）")
            tag = sorted(set(WRAPPER_TAG.findall(t)))
            if tag:
                problems.append(f"{stage}/{src.stem}：殘留包裝標籤 {tag}")
            en = EN_SENT.findall(t)
            if en:
                problems.append(f"{stage}/{src.stem}：疑似未翻譯英文 {en[0][:60]!r}（共 {len(en)} 處）")

            rows.append((stage, src.stem, n_in, body, len(t), t.count("轉錄不清")))

    print(f"{'舞台':9} {'區塊':22} {'輸入段':>6} {'輸出段':>6} {'字數':>7} {'不清標註':>8}")
    print("-" * 64)
    for r in rows:
        print(f"{r[0]:9} {r[1]:22} {r[2]:6d} {r[3]:6d} {r[4]:7d} {r[5]:8d}")
    print("-" * 64)
    print(f"{'合計':9} {len(rows):22d} {sum(r[2] for r in rows):6d} {sum(r[3] for r in rows):6d} "
          f"{sum(r[4] for r in rows):7d} {sum(r[5] for r in rows):8d}")

    if problems:
        print(f"\n問題 {len(problems)} 項：")
        for p in problems:
            print("  ⚠", p)
    else:
        print("\n全部通過")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
