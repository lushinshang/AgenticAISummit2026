#!/usr/bin/env python3
"""把 agenda.json 依午餐時間拆成 morning/afternoon，產生給切分用的對照檔。"""
import json
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
agenda = json.loads((TOOLS / "agenda.json").read_text(encoding="utf-8"))
OUT = TOOLS / "agenda_split"
OUT.mkdir(exist_ok=True)

for stage, st in agenda.items():
    lunch = next((s["time"] for s in st["sessions"] if "午餐" in s["title"]), "12:00")
    for key in ("morning", "afternoon"):
        sel = [s for s in st["sessions"]
               if ((s["time"] < lunch) if key == "morning" else (s["time"] > lunch))]
        data = {
            "stage": stage,
            "stage_name_zh": st["name_zh"],
            "stage_name_en": st["name_en"],
            "session_part": key,
            "lunch_time": lunch,
            "sessions": sel,
        }
        (OUT / f"{stage}_{key}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        content = [s for s in sel if s["kind"] == "content"]
        print(f"{stage}_{key}.json  議程 {len(sel):2d}（內容 {len(content):2d}）"
              f"  {sel[0]['time'] if sel else '-'}–{sel[-1]['time'] if sel else '-'}")
