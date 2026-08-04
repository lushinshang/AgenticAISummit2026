#!/usr/bin/env python3
"""產生工作目錄根目錄的 index.html：Day 1 八個連結 + Day 2 待處理佔位。

連結一律相對路徑（day1_zh/html/...），整包搬移不會失效。
"""
import html
import json
import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]                    # 工作目錄根
agenda = json.loads((TOOLS / "agenda.json").read_text(encoding="utf-8"))
manifest = json.loads((TOOLS / "sections_manifest.json").read_text(encoding="utf-8"))

STAGES = ("plenary", "atlas", "nexus", "compass")

# Day 2 議程（僅列舞台與場次數，內容尚未處理）
day2_txt = (ROOT / "Day2Agenda.txt").read_text(encoding="utf-8")
day2 = []
for m in re.finditer(r"^(\d+)\. (.+?) \((.+?)\)$", day2_txt, re.M):
    seg = day2_txt.split(m.group(0), 1)[1]
    nxt = re.search(r"^\d+\. ", seg, re.M)
    seg = seg[:nxt.start()] if nxt else seg
    times = re.findall(r"^\[(\d{2}:\d{2} [AP]M)\] ", seg, re.M)
    day2.append((m.group(2), m.group(3), len(times),
                 f"{times[0]}–{times[-1]}" if times else ""))


CJK = re.compile(r"[\u4e00-\u9fff]")


def stage_stats(stage):
    """回傳（議程數、全文中文字數、導讀中文字數、導讀篇數、缺稿數）

    字數只算中文字，不含空白、標點與 Markdown 標記——標「44 萬字」但其中
    十萬是空格與符號會誤導讀者。
    """
    tr = (TOOLS.parent / "transcript" / f"{stage}.md").read_text(encoding="utf-8")
    gd = (TOOLS.parent / "guide" / f"{stage}.md").read_text(encoding="utf-8")
    n_sess = tr.count("\n## ")
    n_guide = len([m for m in manifest if m["stage"] == stage])
    missing = tr.count("現場錄影未涵蓋此時段")
    return n_sess, len(CJK.findall(tr)), len(CJK.findall(gd)), n_guide, missing


CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#f9f7f4; --fg:#1a1a1a; --muted:#5f5b54; --line:#e3ddd4;
  --accent:#8a5a2b; --accent-soft:#f0e9df; --card:#fffdfa; --dim:#9a938a;
}
body{
  margin:0;background:var(--bg);color:var(--fg);
  font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
  font-size:17px;line-height:1.68;letter-spacing:0;
}
.wrap{max-width:1000px;margin:0 auto;padding:0 24px 96px}
header{padding:72px 0 36px;border-bottom:1px solid var(--line);margin-bottom:44px}
h1{font-size:clamp(2rem,4.4vw,2.9rem);line-height:1.28;margin:0 0 14px;text-wrap:balance}
.lead{color:var(--muted);font-size:16px;margin:0 0 6px}
.meta{color:var(--dim);font-size:14px;margin:18px 0 0}
h2.day{
  font-size:1.5rem;margin:56px 0 6px;text-wrap:balance;
  border-left:5px solid var(--accent);padding-left:14px;margin-left:-19px;
}
h2.day .tag{
  font-size:13px;font-weight:400;color:var(--muted);
  background:var(--accent-soft);border-radius:999px;padding:3px 11px;
  margin-left:10px;vertical-align:middle;white-space:nowrap;
}
h2.day.pending{border-left-color:var(--dim);color:var(--muted)}
h2.day.pending .tag{background:#eeebe6;color:var(--dim)}
.daynote{color:var(--muted);font-size:15px;margin:6px 0 26px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
.card{
  background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:20px 22px 18px;
}
.card h3{margin:0 0 4px;font-size:1.12rem;text-wrap:balance}
.card .en{color:var(--dim);font-size:13px;margin:0 0 12px}
.card .stat{color:var(--muted);font-size:13.5px;margin:0 0 16px;line-height:1.55}
.links{display:flex;gap:10px;flex-wrap:wrap}
.links a{
  font-size:14.5px;text-decoration:none;color:var(--accent);
  border:1px solid var(--line);border-radius:999px;padding:7px 15px;
  background:var(--bg);white-space:nowrap;
}
.links a:hover{background:var(--accent-soft)}
.links a.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.links a.primary:hover{background:#75491f}
.card.pending{background:#f4f2ee;border-style:dashed}
.card.pending h3{color:var(--muted)}
.card.pending .stat{color:var(--dim)}
.pendmark{
  display:inline-block;font-size:13.5px;color:var(--dim);
  border:1px dashed var(--line);border-radius:999px;padding:6px 14px;
}
footer{margin-top:64px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--dim);font-size:13.5px;line-height:1.6}
@media (max-width:640px){
  .wrap{padding:0 18px 72px}
  header{padding:48px 0 28px}
  h2.day{margin-left:0;font-size:1.32rem}
  h2.day .tag{display:block;margin:8px 0 0;width:fit-content}
  body{font-size:16px}
}
"""

cards = []
tot_sess = tot_tr = tot_gd = tot_guide = tot_missing = 0
for s in STAGES:
    st = agenda[s]
    n_sess, tr_len, gd_len, n_guide, missing = stage_stats(s)
    tot_sess += n_sess; tot_tr += tr_len; tot_gd += gd_len
    tot_guide += n_guide; tot_missing += missing
    miss = f"，其中 {missing} 場無錄影" if missing else ""
    cards.append(f"""    <div class="card">
      <h3>{html.escape(st['name_zh'])}</h3>
      <p class="en">{html.escape(st['name_en'])}</p>
      <p class="stat">{n_sess} 場議程{miss}<br>
        全文 {tr_len // 1000} 千字 ／ 導讀 {n_guide} 篇、{gd_len // 1000} 千字</p>
      <div class="links">
        <a class="primary" href="day1_zh/html/{s}-guide.html">主題式導讀</a>
        <a href="day1_zh/html/{s}-transcript.html">繁體中文全文</a>
      </div>
    </div>""")

day2_cards = []
for name_zh, name_en, n, span in day2:
    day2_cards.append(f"""    <div class="card pending">
      <h3>{html.escape(name_zh)}</h3>
      <p class="en">{html.escape(name_en)}</p>
      <p class="stat">議程表列 {n} 場{('，' + span) if span else ''}</p>
      <span class="pendmark">待處理中</span>
    </div>""")

doc = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>代理型 AI 高峰會 2026｜繁體中文全文與導讀</title>
<meta name="description" content="Agentic AI Summit 2026 現場錄影的台式繁體中文全文與逐場主題式導讀。">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>代理型 AI 高峰會 2026<br>繁體中文全文與導讀</h1>
  <p class="lead">Agentic AI Summit 2026 — 加州大學柏克萊分校 RDI 主辦</p>
  <p class="lead">2026 年 8 月 1–2 日</p>
  <p class="meta">
    本站內容由現場錄影的英文自動轉錄稿翻譯為台灣用語繁體中文，依大會議程分節；
    每個舞台另有逐場主題式導讀，梳理講者的核心主張與論點推進。<br>
    講者姓名、職稱與講題以官方議程表為準；錄音轉錄不清之處在全文中標有 [?] 記號。
  </p>
</header>

<h2 class="day">Day 1<span class="tag">2026 年 8 月 1 日（六）· 已完成</span></h2>
<p class="daynote">四個舞台共 {tot_sess} 場議程，全文 {tot_tr // 10000} 萬字，導讀 {tot_guide} 篇。</p>
<div class="grid">
{chr(10).join(cards)}
</div>

<h2 class="day pending">Day 2<span class="tag">2026 年 8 月 2 日（日）· 待處理中</span></h2>
<p class="daynote">素材尚未整理，全文與導讀待後續補上。</p>
<div class="grid">
{chr(10).join(day2_cards)}
</div>

<footer>
  全文與導讀由現場錄影轉錄後翻譯整理，非大會官方發布內容；
  遇有疑義請以官方議程與錄影為準。
</footer>

</div>
</body>
</html>
"""

dst = ROOT / "index.html"
dst.write_text(doc, encoding="utf-8")
print(f"已產出 {dst}")
print(f"  Day 1：{len(cards)} 個舞台卡片、{len(cards) * 2} 個連結，"
      f"{tot_sess} 場議程、{tot_missing} 場無錄影")
print(f"  Day 2：{len(day2_cards)} 個舞台標示待處理中，無可點連結")
print(f"  檔案大小 {len(doc) / 1024:.0f} KB")
