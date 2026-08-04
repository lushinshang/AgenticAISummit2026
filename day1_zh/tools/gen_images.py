#!/usr/bin/env python3
"""依 imagegen_specs.json 批次產生議程資訊圖（16:9 桌機版 + 9:16 手機版）。

每張圖 1–5 分鐘，故並行跑；已存在的檔案會跳過，可中斷後重跑。
用法：python3 gen_images.py [--workers N] [--only KEY[,KEY...]] [--aspect 16:9|9:16]
"""
import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
IMG = TOOLS.parent / "html" / "images"
SCRIPT = Path.home() / ".claude/skills/md_to_html/scripts/codex_imagegen.py"
SPECS = json.loads((TOOLS / "imagegen_specs.json").read_text(encoding="utf-8"))

BASE = ("依據本段落內容生成資訊圖表，表達方式白話易懂，"
        "使用台灣 IT／AI 專業用語繁體中文，粉圓體，japan kawaii style，{aspect}。\n"
        "段落主題：{topic}\n"
        "重點：{point}\n"
        "資訊圖結構：{structure}\n"
        "所有文字必須是繁體中文（專有名詞、公司名、產品名保留英文原文），"
        "不可出現簡體字，標點用全形。")
PORTRAIT_EXTRA = ("\n請將上述所有元素改為由上而下垂直堆疊的直式版面，適合手機直向閱讀："
                  "標題置頂，各區塊依序往下排列，不要並排；圖內文字要放大到手機上清晰可讀。")


def gen(spec, aspect):
    suffix = "" if aspect == "16:9" else "-mobile"
    out = IMG / f"{spec['key']}{suffix}.png"
    if out.exists() and out.stat().st_size > 50_000:
        return spec["key"], aspect, "skip", out.stat().st_size

    prompt = BASE.format(aspect=aspect, topic=spec["topic"],
                         point=spec["point"], structure=spec["structure"])
    if aspect == "9:16":
        prompt += PORTRAIT_EXTRA

    t0 = time.time()
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--prompt", prompt,
         "--image", str(out), "--aspect", aspect,
         "--timeout", "300000", "--retries", "2"],
        capture_output=True, text=True, timeout=1200)
    dt = time.time() - t0
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return spec["key"], aspect, f"parse-fail({r.returncode})", int(dt)
    if res.get("status") == "ok":
        return spec["key"], aspect, "ok", res.get("bytes", 0)
    return spec["key"], aspect, f"error:{res.get('error_kind', '?')}", int(dt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--aspect", default="both")
    a = ap.parse_args()

    IMG.mkdir(parents=True, exist_ok=True)
    specs = SPECS
    if a.only:
        want = set(a.only.split(","))
        specs = [s for s in specs if s["key"] in want]
    aspects = ["16:9", "9:16"] if a.aspect == "both" else [a.aspect]
    jobs = [(s, asp) for s in specs for asp in aspects]

    print(f"待產生 {len(jobs)} 張（{len(specs)} 個議程 × {len(aspects)} 版），"
          f"並行 {a.workers}", flush=True)
    ok = skip = fail = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(gen, s, asp): (s["key"], asp) for s, asp in jobs}
        for f in as_completed(futs):
            key, asp, status, info = f.result()
            mark = {"ok": "✓", "skip": "-"}.get(status, "✗")
            print(f"  {mark} {key:16} {asp:5} {status:22} {info}", flush=True)
            ok += status == "ok"; skip += status == "skip"; fail += mark == "✗"
    print(f"\n完成 {ok}／跳過 {skip}／失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
