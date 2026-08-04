#!/usr/bin/env python3
"""解析 Day2Agenda.txt（已是台式繁中版）→ agenda.json，作為議程切分與譯名的權威來源。"""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC = BASE / "Day2Agenda.txt"
DST = Path(__file__).resolve().parent / "agenda.json"

STAGE_RE = re.compile(r"^(\d+)\.\s*(.+?)\s*\((.+?)\)\s*$")
TIME_RE = re.compile(r"^\[(\d{2}):(\d{2})\s*(AM|PM)\]\s*(.+?)\s*$")
# 「- 姓名 (職稱)」；姓名可能含 . 與空白
SPEAKER_RE = re.compile(r"^-\s*([^(（:：]+?)\s*[(（](.+?)[)）]\s*$")
TOPIC_RE = re.compile(r"^\*主題：(.+?)\*$")
# 「- 講者：A (x)、B (y)」/「- 與談人：…」/「- 主持人：…」
ROLE_RE = re.compile(r"^-\s*(講者|與談人|主持人|對談嘉賓|主題演講|工作坊帶領人)\s*[:：]\s*(.+?)\s*$")

BREAK_KEYWORDS = ("午餐", "招待會", "海報", "休息", "報到", "結束")


def to_24h(hh: int, mm: int, ampm: str) -> str:
    if ampm == "PM" and hh != 12:
        hh += 12
    if ampm == "AM" and hh == 12:
        hh = 0
    return f"{hh:02d}:{mm:02d}"


def split_name_affil(part: str):
    """拆「姓名 (職稱)」。

    不能用正則，因為兩邊都可能有括號：
    姓名內有括號 —— `Yuan (Emily) Xue (Scale AI 企業 AI 負責人)`
    職稱內有括號 —— `Rahul Bakshi (Amazon 應用科學 (邊緣 AI) 總監)`
    非貪婪會把前者的姓名切成 `Yuan`，貪婪會把後者的職稱切成 `邊緣 AI) 總監`。
    改成從右邊找與結尾括號配對的那一個左括號，兩種情況都對。
    """
    part = part.strip()
    if not part or part[-1] not in ")）":
        return {"name": part, "affiliation": ""}
    depth = 0
    for i in range(len(part) - 1, -1, -1):
        if part[i] in ")）":
            depth += 1
        elif part[i] in "(（":
            depth -= 1
            if depth == 0:
                name = part[:i].strip()
                affil = part[i + 1:-1].strip()
                return {"name": name, "affiliation": affil} if name else {"name": part, "affiliation": ""}
    return {"name": part, "affiliation": ""}


def split_persons(text: str):
    """把「A (x)、B (y)」拆成 [{name, affiliation}]"""
    out = []
    for part in re.split(r"[、,]\s*(?![^(（]*[)）])", text):
        if part.strip():
            out.append(split_name_affil(part))
    return out


def main():
    stages = []
    cur_stage = None
    cur_sess = None

    for line in SRC.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or set(s) <= {"=", "-"}:
            continue

        m = STAGE_RE.match(s)
        if m:
            cur_stage = {
                "order": int(m.group(1)),
                "name_zh": m.group(2).strip(),
                "name_en": m.group(3).strip(),
                "sessions": [],
            }
            stages.append(cur_stage)
            cur_sess = None
            continue

        if cur_stage is None:
            continue

        m = TIME_RE.match(s)
        if m:
            hh, mm, ampm, title = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
            cur_sess = {
                "index": len(cur_stage["sessions"]) + 1,
                "time": to_24h(hh, mm, ampm),
                "time_label": f"{hh:02d}:{mm:02d} {ampm}",
                "title": title,
                "kind": "break" if any(k in title for k in BREAK_KEYWORDS) else "content",
                "speakers": [],
                "raw_lines": [],
            }
            cur_stage["sessions"].append(cur_sess)
            continue

        if cur_sess is None:
            continue
        cur_sess["raw_lines"].append(s)

        m = ROLE_RE.match(s)
        if m:
            role, rest = m.group(1), m.group(2)
            # 「主題演講：講題 (人名 - 職稱)」與一般「講者：A (x)、B (y)」結構相反
            if role in ("主題演講", "工作坊帶領人"):
                mm2 = re.match(r"^(.+?)\s*[(（](.+?)[)）]\s*$", rest)
                if mm2:
                    who = mm2.group(2).split(" - ", 1)
                    cur_sess["speakers"].append({
                        "name": who[0].strip(),
                        "affiliation": who[1].strip() if len(who) > 1 else "",
                        "role": role,
                        "topic": mm2.group(1).strip(),
                    })
                    continue
            for p in split_persons(rest):
                p["role"] = role
                p["topic"] = ""
                cur_sess["speakers"].append(p)
            continue

        if s.startswith("- ") and not ROLE_RE.match(s) and s.rstrip()[-1] in ")）":
            # 姓名或職稱任一邊含括號都要能正確拆（見 split_name_affil）
            p = split_name_affil(s[2:])
            if p["affiliation"]:
                p["role"] = "講者"
                p["topic"] = ""
                cur_sess["speakers"].append(p)
                continue

        m = TOPIC_RE.match(s)
        if m and cur_sess["speakers"]:
            cur_sess["speakers"][-1]["topic"] = m.group(1).strip()
            continue

        if s.startswith("-"):
            cur_sess["speakers"].append({
                "name": s.lstrip("- ").strip(),
                "affiliation": "",
                "role": "講者",
                "topic": "",
            })

    key = {"Plenary Stage": "plenary", "Atlas Stage": "atlas",
           "Compass Stage": "compass"}
    data = {key[st["name_en"]]: st for st in stages}
    DST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'舞台':22} {'議程':>5} {'內容':>5} {'休息':>5} {'講者人次':>8}  時間範圍")
    print("-" * 72)
    total = 0
    for k, st in data.items():
        ss = st["sessions"]
        content = [x for x in ss if x["kind"] == "content"]
        spk = sum(len(x["speakers"]) for x in ss)
        total += len(ss)
        print(f"{k + ' ' + st['name_zh']:22} {len(ss):5d} {len(content):5d} "
              f"{len(ss) - len(content):5d} {spk:8d}  {ss[0]['time']}–{ss[-1]['time']}")
    print("-" * 72)
    print(f"{'合計':22} {total:5d}")

    # 無講者的內容議程要點出來（可能解析漏了）
    for k, st in data.items():
        for x in st["sessions"]:
            if x["kind"] == "content" and not x["speakers"]:
                print(f"注意：{k} [{x['time']}] {x['title']} — 無講者資料")


if __name__ == "__main__":
    main()
