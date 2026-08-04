#!/usr/bin/env python3
"""前處理：把 _source/en_srt/ 的 SRT 統一解析、清洗填充語，輸出帶時間戳的 JSONL 中繼檔。

以 SRT 為唯一來源（.txt 有兩種斷句格式，SRT 兩種檔都是標準格式），
順帶解決 proposal 記錄的「txt 斷句不一致」與「檔名格式不一致」兩個坑。
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC = BASE / "_source" / "en_srt"
OUT = Path(__file__).resolve().parent / "cleaned"

# 舞台 -> (上午檔名關鍵字, 下午檔名關鍵字)
STAGES = {
    "plenary": "Plenary Stage",
    "atlas": "Atlas Stage",
    "nexus": "Nexus Stage",
    "compass": "Compass Stage",
}

# 整段丟棄：純填充語 / 場記標記
DROP_WHOLE = re.compile(
    r"^\W*(thank you|thanks|thank you\.? thank you|applause|music|laughter|"
    r"− double screen \.\.\.|\[.*\]|\(.*\))\W*$",
    re.I,
)
# 行內填充詞（保守：只處理明確無實義的）
INLINE_FILLER = re.compile(
    r"\b(um+|uh+|erm|mm-?hm+|hmm+)\b[,.]?\s*", re.I
)
INLINE_YOUKNOW = re.compile(r"\byou know\b[,]?\s*", re.I)
MULTISPACE = re.compile(r"\s{2,}")

TS = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def to_sec(ts: str) -> float:
    h, m, s, ms = TS.match(ts).groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: Path):
    """回傳 [(start_sec, end_sec, text)]"""
    cues = []
    block = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == "":
            if block:
                cues.append(block)
                block = []
        else:
            block.append(line)
    if block:
        cues.append(block)

    out = []
    for b in cues:
        if len(b) < 3:
            continue
        m = TS.search(b[1])
        if not m or "-->" not in b[1]:
            continue
        start_s, end_s = [x.strip() for x in b[1].split("-->")]
        text = " ".join(b[2:]).strip()
        out.append((to_sec(start_s), to_sec(end_s), text))
    return out


def clean(text: str) -> str:
    if DROP_WHOLE.match(text):
        return ""
    t = INLINE_FILLER.sub("", text)
    t = INLINE_YOUKNOW.sub("", t)
    t = MULTISPACE.sub(" ", t).strip()
    # 清完只剩標點或單字殘渣就丟
    if len(t) <= 2 or not re.search(r"[A-Za-z]", t):
        return ""
    return t


def merge(cues, gap=2.0):
    """相鄰片段合併成段落：句尾標點結束且間隔夠大才斷段。"""
    paras = []
    cur = None
    for st, en, tx in cues:
        if cur is None:
            cur = [st, en, tx]
            continue
        ends_sentence = cur[2].rstrip().endswith((".", "?", "!"))
        if (st - cur[1]) > gap and ends_sentence:
            paras.append(tuple(cur))
            cur = [st, en, tx]
        elif len(cur[2]) > 700 and ends_sentence:
            paras.append(tuple(cur))
            cur = [st, en, tx]
        else:
            cur[1] = en
            cur[2] = (cur[2] + " " + tx).strip()
    if cur:
        paras.append(tuple(cur))
    return paras


def dedup(paras):
    """移除連續完全重複的段落（轉錄常見）。"""
    out = []
    for p in paras:
        if out and out[-1][2] == p[2]:
            continue
        out.append(p)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srts = sorted(SRC.glob("*.srt"))
    if len(srts) != 8:
        print(f"警告：預期 8 份 srt，實際找到 {len(srts)} 份", file=sys.stderr)

    rows = []
    for path in srts:
        name = path.stem
        stage = next((k for k, v in STAGES.items() if v in name), None)
        if stage is None:
            print(f"跳過無法辨識舞台的檔案：{name}", file=sys.stderr)
            continue
        session = "morning" if "Morning" in name else "afternoon"

        raw = parse_srt(path)
        cleaned = [(s, e, clean(t)) for s, e, t in raw]
        kept = [(s, e, t) for s, e, t in cleaned if t]
        paras = dedup(merge(kept))

        dst = OUT / f"{stage}_{session}.jsonl"
        with dst.open("w", encoding="utf-8") as f:
            for s, e, t in paras:
                f.write(json.dumps(
                    {"start": round(s, 2), "end": round(e, 2), "text": t},
                    ensure_ascii=False) + "\n")

        words = sum(len(t.split()) for _, _, t in paras)
        rows.append((dst.name, len(raw), len(kept), len(paras), words,
                     paras[0][0] if paras else 0.0))

    print(f"{'輸出檔':28} {'原cue':>7} {'留存':>7} {'段落':>6} {'字數':>8} {'首段起點':>9}")
    print("-" * 72)
    for n, r, k, p, w, first in rows:
        mm, ss = divmod(int(first), 60)
        print(f"{n:28} {r:7d} {k:7d} {p:6d} {w:8d} {mm:>6d}:{ss:02d}")
    print("-" * 72)
    print(f"{'合計':28} {sum(r[1] for r in rows):7d} {sum(r[2] for r in rows):7d} "
          f"{sum(r[3] for r in rows):6d} {sum(r[4] for r in rows):8d}")


if __name__ == "__main__":
    main()
