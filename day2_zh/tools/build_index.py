#!/usr/bin/env python3
"""產生工作目錄根目錄的 index.html：兩天共 14 個連結。

連結一律相對路徑（day1_zh/html/…、day2_zh/html/…），整包搬移不會失效。
兩天的舞台、議程數與字數各自從該天目錄下的資料算，不共用常數——
Day 1 有四個舞台（含 Nexus）、Day 2 只有三個。
"""
import html
import json
import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]                    # 工作目錄根

DAYS = (
    {"key": "day1_zh", "label": "Day 1", "date": "2026 年 8 月 1 日（六）",
     "stages": ("plenary", "atlas", "nexus", "compass")},
    {"key": "day2_zh", "label": "Day 2", "date": "2026 年 8 月 2 日（日）",
     "stages": ("plenary", "atlas", "compass")},
)

CJK = re.compile(r"[一-鿿]")


def stage_stats(base, manifest, stage):
    """回傳（議程數、全文中文字數、導讀中文字數、導讀篇數、缺稿數）

    字數只算中文字，不含空白、標點與 Markdown 標記——標「44 萬字」但其中
    十萬是空格與符號會誤導讀者。
    """
    tr = (base / "transcript" / f"{stage}.md").read_text(encoding="utf-8")
    gd = (base / "guide" / f"{stage}.md").read_text(encoding="utf-8")
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
.about{
  margin:26px 0 0;padding:20px 24px;background:var(--card);
  border:1px solid var(--line);border-radius:12px;
}
.about-h{font-size:1.05rem;margin:0 0 10px;color:var(--accent)}
.about p{margin:0 0 10px;font-size:15px;color:var(--muted);line-height:1.75}
.about p:last-child{margin-bottom:0}
.about-src{font-size:13.5px!important}
.meta a.src{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--line)}
.meta a.src:hover{border-bottom-color:var(--accent)}
h2.day{
  font-size:1.5rem;margin:56px 0 6px;text-wrap:balance;
  border-left:5px solid var(--accent);padding-left:14px;margin-left:-19px;
}
h2.day .tag{
  font-size:13px;font-weight:400;color:var(--muted);
  background:var(--accent-soft);border-radius:999px;padding:3px 11px;
  margin-left:10px;vertical-align:middle;white-space:nowrap;
}
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
footer{margin-top:64px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--dim);font-size:13.5px;line-height:1.68}
footer p{margin:0 0 8px}
footer a{color:var(--accent)}
@media (max-width:640px){
  .wrap{padding:0 18px 72px}
  header{padding:48px 0 28px}
  h2.day{margin-left:0;font-size:1.32rem}
  h2.day .tag{display:block;margin:8px 0 0;width:fit-content}
  body{font-size:16px}
}
"""

blocks = []
summary = []
n_links = 0
for day in DAYS:
    base = ROOT / day["key"]
    agenda = json.loads((base / "tools" / "agenda.json").read_text(encoding="utf-8"))
    manifest = json.loads((base / "tools" / "sections_manifest.json").read_text(encoding="utf-8"))

    cards = []
    tot_sess = tot_tr = tot_guide = tot_missing = 0
    for s in day["stages"]:
        st = agenda[s]
        n_sess, tr_len, gd_len, n_guide, missing = stage_stats(base, manifest, s)
        tot_sess += n_sess; tot_tr += tr_len
        tot_guide += n_guide; tot_missing += missing
        miss = f"，其中 {missing} 場無錄影" if missing else ""
        cards.append(f"""    <div class="card">
      <h3>{html.escape(st['name_zh'])}</h3>
      <p class="en">{html.escape(st['name_en'])}</p>
      <p class="stat">{n_sess} 場議程{miss}<br>
        全文 {tr_len // 1000} 千字 ／ 導讀 {n_guide} 篇、{gd_len // 1000} 千字</p>
      <div class="links">
        <a class="primary" href="{day['key']}/html/{s}-guide.html">主題式導讀</a>
        <a href="{day['key']}/html/{s}-transcript.html">繁體中文全文</a>
      </div>
    </div>""")
        n_links += 2

    n_stage = len(day["stages"])
    blocks.append(f"""<h2 class="day">{day['label']}<span class="tag">{day['date']} · 已完成</span></h2>
<p class="daynote">{['', '一', '兩', '三', '四'][n_stage]}個舞台共 {tot_sess} 場議程，"""
                  f"""全文 {tot_tr // 10000} 萬字，導讀 {tot_guide} 篇。</p>
<div class="grid">
{chr(10).join(cards)}
</div>""")
    summary.append((day["label"], n_stage, tot_sess, tot_missing, tot_tr, tot_guide))

doc = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agentic AI Summit 2026 - AI導讀</title>
<meta name="description" content="Agentic AI Summit 2026（柏克萊 RDI 主辦）現場錄影的繁體中文全文與逐場主題式導讀，兩天七個舞台 70 場議程。">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>Agentic AI Summit 2026<br>AI 導讀</h1>
  <p class="lead">代理型 AI 高峰會 2026 — 加州大學柏克萊分校 RDI 主辦</p>
  <p class="lead">2026 年 8 月 1–2 日 · UC Berkeley 校園</p>

  <div class="about">
    <h2 class="about-h">關於這場大會</h2>
    <p>由柏克萊 RDI（負責任去中心化智慧中心）與 RDI 基金會主辦，延續 2025 年高峰會
    （逾 2,000 名現場與會者、逾 40,000 名線上參與者）與近 40,000 名學習者的代理型 AI 磨課師社群。
    如果說 2025 年是「代理人元年」，2026 年就是代理型 AI 在研究、基礎設施與產業部署上爆發成長的一年。</p>
    <p>大會定位為目前規模最大、最全面的代理型 AI 盛會，議程橫跨基礎模型、代理人框架、
    模型評估、基礎設施到實際場域部署，並直面安全與防護的關鍵挑戰。兩天七個舞台、70 場議程，
    講者來自學術界、頂尖 AI 組織、新創與創投。實體票券全數售罄，預計約 5,000 名現場與會者。</p>
    <p class="about-src">大會官方網站：<a class="src" href="https://rdi.berkeley.edu/events/agentic-ai-summit-2026" target="_blank" rel="noopener">rdi.berkeley.edu/events/agentic-ai-summit-2026</a></p>
  </div>

  <p class="meta">
    本站內容由現場錄影的英文自動轉錄稿翻譯為台灣用語繁體中文，依大會議程分節，
    每次發言前標註發言者；每個舞台另有逐場主題式導讀，梳理講者的核心主張與論點推進。<br>
    講者姓名、職稱與講題以官方議程表為準；錄音轉錄不清之處在全文中標有 [?] 記號。
  </p>
</header>

{chr(10).join(blocks)}

<footer>
  <p><strong>本站為非官方的個人整理，與主辦單位無關。</strong>
  內容來自 Agentic AI Summit 2026 大會公開錄影的英文自動轉錄稿，翻譯為繁體中文並依議程分節；
  導讀為個人撰寫的閱讀輔助。遇有疑義，一律以官方議程與錄影為準。</p>
  <p>大會官方網站：<a href="https://rdi.berkeley.edu/events/agentic-ai-summit-2026" target="_blank" rel="noopener">rdi.berkeley.edu/events/agentic-ai-summit-2026</a></p>
  <p>本站不主張任何內容的著作權。<strong>如權利人要求，將立即下架。</strong></p>
</footer>

</div>
</body>
</html>
"""

dst = ROOT / "index.html"
dst.write_text(doc, encoding="utf-8")
print(f"已產出 {dst}")
for label, n_stage, sess, missing, tr, guide in summary:
    print(f"  {label}：{n_stage} 個舞台、{n_stage * 2} 個連結，"
          f"{sess} 場議程（{missing} 場無錄影）、全文 {tr} 中文字、導讀 {guide} 篇")
print(f"  連結合計 {n_links} 個，檔案大小 {len(doc) / 1024:.0f} KB")
