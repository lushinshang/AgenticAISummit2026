#!/usr/bin/env python3
"""把 transcript/ 與 guide/ 的 md 轉成可直接開啟的 html。

排版依 md_to_html skill 的標準：米白底、深灰字、限制版心、繁中字型堆疊、
text-wrap: balance、RWD。長文另加側邊目錄、回到頂部、閱讀進度條。
"""
import html
import json
import re
from pathlib import Path

import markdown

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent            # day1_zh/
OUT = ROOT / "html"
agenda = json.loads((TOOLS / "agenda.json").read_text(encoding="utf-8"))

STAGES = ("plenary", "atlas", "compass")
KINDS = {"transcript": "繁體中文全文", "guide": "主題式導讀"}

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#f9f7f4; --fg:#1a1a1a; --muted:#5f5b54; --line:#e3ddd4;
  --accent:#8a5a2b; --accent-soft:#f0e9df; --card:#fffdfa;
}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--bg); color:var(--fg);
  font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
  font-size:17px; line-height:1.68; letter-spacing:0;
}
.progress{position:fixed;top:0;left:0;height:3px;width:0;background:var(--accent);z-index:120}
.wrap{max-width:820px;margin:0 auto;padding:0 24px}
.toc{
  margin:28px 0 8px;border:1px solid var(--line);border-radius:12px;
  background:var(--card);font-size:14.5px;line-height:1.5;
}
.toc>summary{
  cursor:pointer;padding:14px 18px;font-weight:600;color:var(--fg);
  list-style:none;display:flex;align-items:center;gap:8px;
}
.toc>summary::-webkit-details-marker{display:none}
.toc>summary::before{content:"▸";color:var(--accent);transition:transform .15s}
.toc[open]>summary::before{transform:rotate(90deg)}
.toc>summary:hover{background:var(--accent-soft);border-radius:12px}
.toc[open]>summary{border-bottom:1px solid var(--line);border-radius:12px 12px 0 0}
.toc-list{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
  gap:2px;padding:10px;
}
.toc-list a{
  display:block;padding:8px 12px;color:var(--muted);text-decoration:none;
  border-radius:6px;
}
.toc-list a:hover{background:var(--accent-soft);color:var(--fg)}
main{max-width:720px;margin:0 auto;padding:8px 0 96px}
header.doc{padding:48px 0 8px;border-bottom:1px solid var(--line);margin-bottom:32px}
h1{font-size:clamp(1.9rem,4vw,2.6rem);line-height:1.3;margin:0 0 12px;text-wrap:balance}
.sub{color:var(--muted);font-size:15px;margin:0 0 4px}
.note{color:var(--muted);font-size:14px;line-height:1.6;margin:12px 0 0}
.switch{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0 0}
.switch a{
  font-size:14px;text-decoration:none;color:var(--accent);
  border:1px solid var(--line);background:var(--card);
  padding:7px 14px;border-radius:999px
}
.switch a:hover{background:var(--accent-soft)}
.switch a.home{color:var(--muted)}
h2{
  font-size:1.34rem;line-height:1.45;margin:56px 0 8px;text-wrap:balance;
  border-left:5px solid var(--accent);padding-left:14px;margin-left:-19px;
  scroll-margin-top:20px;
}
h3{font-size:1.08rem;margin:32px 0 6px;text-wrap:balance;color:#2c2620}
p{margin:0 0 1.05em}
ul{margin:0 0 1.1em;padding-left:1.3em}
li{margin:.25em 0}
strong{font-weight:600}
blockquote{
  margin:1.2em 0;padding:12px 18px;background:var(--accent-soft);
  border-left:3px solid var(--accent);border-radius:0 6px 6px 0;color:var(--muted)
}
blockquote p{margin:0}
hr{border:0;border-top:1px solid var(--line);margin:40px 0}
code{background:var(--accent-soft);padding:2px 6px;border-radius:4px;font-size:.92em}
figure.section-figure{margin:26px 0 30px;padding:0}
figure.section-figure img{
  width:100%;max-width:860px;display:block;margin:0 auto;
  height:auto;   /* 依原圖比例縮放：寫死 aspect-ratio + cover 會把圖裁掉 */
  border-radius:12px;cursor:zoom-in;
  box-shadow:0 6px 24px rgba(0,0,0,.08);border:1px solid var(--line);
}
figure.section-figure figcaption{
  text-align:center;color:var(--muted);font-size:13.5px;margin-top:10px;line-height:1.55
}
.lightbox{
  display:none;position:fixed;inset:0;z-index:200;background:rgba(26,26,26,.9);
  align-items:center;justify-content:center;padding:24px;cursor:zoom-out
}
.lightbox.is-open{display:flex}
.lightbox img{max-width:96vw;max-height:92vh;width:auto;height:auto;border-radius:8px}
.lightbox .lightbox-hint{
  position:absolute;top:18px;right:22px;color:rgba(255,255,255,.75);font-size:14px
}
@media (max-width:640px){
  figure.section-figure img{max-width:420px}
}
sup.unclear{
  color:#a8722f;background:#f6ead9;border:1px solid #e6d3b8;
  border-radius:4px;padding:0 4px;margin:0 2px;font-size:.72em;
  cursor:help;vertical-align:super;line-height:1;white-space:nowrap;
}
.say{margin:0 0 1.05em}
.say .who{
  display:inline-block;font-weight:600;color:var(--accent);
  margin-right:.5em;
}
.say .who::after{content:"："}
footer.doc{
  margin:64px 0 0;padding:22px 0 0;border-top:1px solid var(--line);
  color:var(--muted);font-size:13.5px;line-height:1.68;
}
footer.doc p{margin:0 0 8px}
footer.doc a{color:var(--accent)}
.speakers{
  background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:14px 18px;margin:0 0 22px;font-size:15px
}
.speakers ul{margin:0;padding-left:1.15em}
.top{
  position:fixed;right:24px;bottom:24px;z-index:110;
  width:44px;height:44px;border-radius:50%;border:1px solid var(--line);
  background:var(--card);color:var(--accent);font-size:18px;cursor:pointer;
  display:none;align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(0,0,0,.08)
}
.top.show{display:flex}
@media (max-width:900px){
  .wrap{padding:0 18px}
  .toc{margin-top:18px}
  .toc-list{grid-template-columns:1fr;max-height:300px;overflow-y:auto}
  h2{margin-left:0;font-size:1.22rem}
  body{font-size:16px;line-height:1.72}
  figure.section-figure{margin:20px 0 24px}
}
"""

JS = """
(function(){
  var bar=document.querySelector('.progress');
  var top=document.querySelector('.top');
  function onScroll(){
    var st=window.scrollY||document.documentElement.scrollTop;
    var h=document.documentElement.scrollHeight-window.innerHeight;
    bar.style.width=(h>0?(st/h*100):0)+'%';
    top.classList.toggle('show',st>600);
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  onScroll();
  top.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});
  var lb=document.getElementById('lightbox');
  if(lb){
    var lbImg=lb.querySelector('img');
    document.querySelectorAll('figure.section-figure img').forEach(function(im){
      im.addEventListener('click',function(){
        lbImg.src=im.currentSrc||im.src;   // currentSrc：放大的要跟目前顯示的版本一致
        lbImg.alt=im.alt; lb.classList.add('is-open');
      });
    });
    function closeLb(){lb.classList.remove('is-open');lbImg.src='';}
    lb.addEventListener('click',closeLb);
    document.addEventListener('keydown',function(e){if(e.key==='Escape')closeLb();});
  }
})();
"""


def slugify(text, seen):
    s = re.sub(r"[^\w一-鿿]+", "-", text).strip("-").lower() or "sec"
    n, base = 1, s
    while s in seen:
        n += 1
        s = f"{base}-{n}"
    seen.add(s)
    return s



IMG_DIR = OUT / "images"
SPECS = json.loads((TOOLS / "imagegen_specs.json").read_text(encoding="utf-8"))
FIG_BY_SESSION = {s["key"]: s for s in SPECS}

# 導讀各節的出現順序（build_guide.py 依 session_index 排序），用來對上圖檔名
ORDER = {}
for _m in json.loads((TOOLS / "sections_manifest.json").read_text(encoding="utf-8")):
    ORDER.setdefault(_m["stage"], []).append(_m["session_index"])


def insert_figures(body_html, stage):
    """把該舞台已生成的資訊圖插進對應議程節。

    圖放在節標題（與講者區塊）之後、正文之前；同時提供 9:16 手機版。
    沒有圖的議程不插，缺圖不影響其他內容。
    """
    sections = re.split(r'(<h2 id="[^"]+">)', body_html)
    if len(sections) < 2:
        return body_html
    out, idx = [sections[0]], 0
    for i in range(1, len(sections), 2):
        head, rest = sections[i], sections[i + 1] if i + 1 < len(sections) else ""
        idx += 1
        key = f"{stage}-s{ORDER[stage][idx - 1]:02d}" if idx - 1 < len(ORDER[stage]) else None
        spec = FIG_BY_SESSION.get(key)
        desktop = IMG_DIR / f"{key}.webp" if key else None
        if spec and desktop and desktop.exists():
            mobile = IMG_DIR / f"{key}-mobile.webp"
            src_m = (f'<source media="(max-width: 640px)" '
                     f'srcset="images/{key}-mobile.webp">' if mobile.exists() else "")
            fig = (f'<figure class="section-figure"><picture>{src_m}'
                   f'<img src="images/{key}.webp" alt="{html.escape(spec["topic"])}">'
                   f'</picture><figcaption>{html.escape(spec["topic"])}'
                   f'（點擊放大）</figcaption></figure>')
            # 插在講者區塊之後；沒有講者區塊就緊接標題
            m = re.search(r'(</div>\s*)', rest)
            if m and rest[:m.start()].find('class="speakers"') != -1:
                rest = rest[:m.end()] + fig + rest[m.end():]
            else:
                rest = fig + rest
        out.append(head)
        out.append(rest)
    return "".join(out)

def convert(md_path, stage, kind):
    raw = md_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    # 抽出 H1 與前言，其餘為正文
    h1 = lines[0].lstrip("# ").strip()
    body_start = 1
    intro = []
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
        intro.append(lines[i])
    body_md = "\n".join(lines[body_start:])
    # 譯文裡偶有「**標題**」緊接條列而未空行，markdown 不會當成 list，補上空行
    body_md = re.sub(r"(?m)^(\*\*[^*\n]+\*\*)\n(?=[-*] )", r"\1\n\n", body_md)

    # `<!-- 轉錄不清 -->` 是 HTML 註解，瀏覽器不顯示，讀者就看不到這個誠實標註。
    # 轉成可見的上標記號，說明文字放進 title 供滑鼠停留查看。
    def unclear(m):
        detail = (m.group(1) or "").strip(" ：:")
        tip = f"此處錄音轉錄不清：{detail}" if detail else "此處錄音轉錄不清，譯文照字面處理"
        return f'<sup class="unclear" title="{html.escape(tip, quote=True)}">[?]</sup>'

    body_md = re.sub(r"<!--\s*轉錄不清\s*(?:[:：]\s*)?(.*?)\s*-->", unclear,
                     body_md, flags=re.S)

    # 收集 H2 供目錄使用，並植入錨點
    seen, toc = set(), []

    def h2_anchor(m):
        title = m.group(1).strip()
        sid = slugify(title, seen)
        toc.append((sid, title))
        return f'<h2 id="{sid}">{html.escape(title)}</h2>'

    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
    body_html = md.convert(body_md)
    body_html = re.sub(r"<h2>(.*?)</h2>", h2_anchor, body_html, flags=re.S)
    if kind == "guide":
        body_html = insert_figures(body_html, stage)
    # 講者條列套卡片樣式
    body_html = re.sub(
        r"<p><strong>講者</strong></p>\s*(<ul>.*?</ul>)",
        r'<div class="speakers"><p><strong>講者</strong></p>\1</div>',
        body_html, flags=re.S)

    if kind == "transcript":
        # 段首的發言者標記獨立成樣式，長段落中比純粗體好辨識
        body_html = re.sub(
            r"<p><strong>([^<>\n]{1,40}?)：</strong>\s*",
            r'<p class="say"><span class="who">\1</span>',
            body_html)

    other = "guide" if kind == "transcript" else "transcript"
    switch = (
        f'<a href="{stage}-{other}.html">切換到{KINDS[other]}</a>'
        f'<a class="home" href="../../index.html">回總覽</a>'
    )
    toc_html = "\n".join(
        f'<a href="#{sid}">{html.escape(t)}</a>' for sid, t in toc)
    intro_html = markdown.markdown("\n".join(intro).strip())

    doc = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(h1)}｜代理型 AI 高峰會 2026 Day 2</title>
<meta name="description" content="Agentic AI Summit 2026 Day 2 — {html.escape(h1)}">
<style>{CSS}</style>
</head>
<body>
<div class="progress"></div>
<div class="wrap">
<main>
<header class="doc">
  <h1>{html.escape(h1)}</h1>
  {intro_html}
  <div class="switch">{switch}</div>
</header>
<details class="toc" open>
  <summary>本頁議程（{len(toc)}）</summary>
  <div class="toc-list">{toc_html}</div>
</details>
{body_html}
<footer class="doc">
  <p><strong>本頁為非官方的個人整理，與主辦單位無關。</strong>
  內容來自 Agentic AI Summit 2026 大會公開錄影的英文自動轉錄稿，翻譯為繁體中文並依議程分節；
  講者姓名、職稱與講題以官方議程表為準，遇有疑義一律以官方議程與錄影為準。</p>
  <p>大會官方網站：<a href="https://rdi.berkeley.edu/events/agentic-ai-summit-2026" target="_blank" rel="noopener">rdi.berkeley.edu/events/agentic-ai-summit-2026</a></p>
  <p>本站不主張任何內容的著作權。<strong>如權利人要求，將立即下架。</strong></p>
</footer>
</main>
</div>
<button class="top" aria-label="回到頂部">↑</button>
<div class="lightbox" id="lightbox">
  <span class="lightbox-hint">點擊或按 Esc 關閉</span>
  <img src="" alt="">
</div>
<script>{JS}</script>
</body>
</html>
"""
    return doc, len(toc)


OUT.mkdir(parents=True, exist_ok=True)
print(f"{'輸出檔':30} {'議程':>4} {'KB':>7}")
print("-" * 46)
rows = []
for kind in ("transcript", "guide"):
    for stage in STAGES:
        src = ROOT / kind / f"{stage}.md"
        doc, n = convert(src, stage, kind)
        dst = OUT / f"{stage}-{kind}.html"
        dst.write_text(doc, encoding="utf-8")
        print(f"{dst.name:30} {n:4d} {len(doc)/1024:7.0f}")
        rows.append((dst.name, n, len(doc)))
print("-" * 46)
print(f"{'合計 ' + str(len(rows)) + ' 檔':30} {sum(r[1] for r in rows):4d} "
      f"{sum(r[2] for r in rows)/1024:7.0f}")
