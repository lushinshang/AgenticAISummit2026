#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

def body_of(md_path, is_first):
    """取譯文本體：丟掉 md 自己的 ## 標題與講者條列區塊。"""
    t = md_path.read_text(encoding="utf-8").strip()
    blocks = [b.strip() for b in re.split(r"\n\s*\n", t) if b.strip()]
    out = []
    LIST_ITEM = re.compile(r"^(?:[-+]\s|\*\s|\d+\.\s)")
    for b in blocks:
        if is_first and b.startswith("#"):
            continue
        if is_first and b.startswith("**講者**"):
            continue
        if is_first and all(LIST_ITEM.match(l.strip()) or not l.strip() for l in b.splitlines()):
            continue
        out.append(b)
    return out

def main():
    if len(sys.argv) < 3:
        print("Usage: gen_prompt.py <stage> <chunk_name>", file=sys.stderr)
        print("Example: gen_prompt.py atlas morning_s01_1.md", file=sys.stderr)
        sys.exit(1)
        
    stage = sys.argv[1]
    chunk_name = sys.argv[2]
    if not chunk_name.endswith(".md"):
        chunk_name += ".md"
        
    tools_dir = Path(__file__).resolve().parent
    
    # 讀取中文與英文 chunks
    zh_path = tools_dir / "zh_chunks" / stage / chunk_name
    en_path = tools_dir / "chunks" / stage / chunk_name.replace(".md", ".json")
    
    if not zh_path.exists():
        print(f"Error: {zh_path} not found", file=sys.stderr)
        sys.exit(1)
    if not en_path.exists():
        print(f"Error: {en_path} not found", file=sys.stderr)
        sys.exit(1)
        
    # 載入資料
    en_data = json.loads(en_path.read_text(encoding="utf-8"))
    en_paras = en_data.get("paragraphs", [])
    
    is_first = chunk_name.endswith("_1.md") or en_data.get("is_first_chunk", False)
    zh_paras = body_of(zh_path, is_first)
    
    # 讀取 agenda.json 以取得當前 session 的講者名單
    agenda_path = tools_dir / "agenda.json"
    speakers_list = []
    if agenda_path.exists():
        agenda = json.loads(agenda_path.read_text(encoding="utf-8"))
        st = agenda.get(stage, {})
        si = en_data.get("session_index", 1)
        meta = next((s for s in st.get("sessions", []) if s["index"] == si), None)
        if meta and meta.get("speakers"):
            for p in meta["speakers"]:
                bits = p["name"]
                if p["affiliation"]:
                    bits += f"（{p['affiliation']}）"
                if p["role"] and p["role"] != "講者":
                    bits += f" —— {p['role']}"
                if p["topic"]:
                    bits += f" —— {p['topic']}"
                speakers_list.append(bits)
                
    # 構建 Prompt
    prompt_lines = [
        "Purpose and Goals:",
        "",
        "妳是一位專業的逐字稿生成器,目標是將上傳的音檔、影片或原逐字稿內容,轉換成準確、完整、易讀的文字記錄。",
        "",
        "- 妳的核心能力在於清晰地識別對話中的不同參與者,並為他們分配易於理解的名稱或代號。",
        "- 妳擅長處理包含專有名詞 and 中英日文夾雜的語句;對於不完全確定的詞彙,妳會選擇最可能的選項,並以括號附註其他候選。",
        "- 妳的最高原則是忠實與完整:除了語助詞,不摘要、不改寫、不省略任何實質內容,也絕不腦補聽不清楚的段落。",
        "",
        "Behaviors and Rules (方案 B 專屬):",
        "",
        "1. 發言者辨識與標註",
        "   a) 清晰分辨不同的發言者，參考提供的官方講者與主持人名單。",
        "   b) 每次發言前加 **姓名：**（粗體姓名、全形冒號、粗體收尾後接一個半形空格）。",
        "   c) 同一個人的連續多個發言段落，必須合併為同一個 Markdown 段落，段落內原有的換行以 <br> 軟換行分隔，不可使用雙換行 (\\n\\n) 造成人名與對話內容脫節。也就是說：換人才分段並標姓名！",
        "",
        "2. 完整性（最高優先）",
        "   a) 除了移除無意義的口語填充詞（如：嗯、啊、就是說、這個那個的口頭禪）與無意義口吃重複（如「我我我覺得」→「我覺得」），必須逐句完整轉錄中文譯文，絕對不得摘要、改寫、刪減任何實質內容與特殊記號（如 [?] 或 <!-- 轉錄不清 -->）。",
        "   b) 必須完整對照原譯文的每一句話。一字不漏！",
        "",
        "3. 姓名拼寫與識別",
        "   a) 一律使用講者名單上的拼法。若無法確認姓名，使用「主持人」、「與談人 A」、「提問者」等清晰的代號。",
        "",
        "========================================",
        "【官方講者與主持人名單】",
    ]
    
    if speakers_list:
        for sp in speakers_list:
            prompt_lines.append(f"- {sp}")
    else:
        # 退回使用 json 裡自帶的 speakers
        for p in en_data.get("speakers", []):
            bits = p["name"]
            if p.get("affiliation"):
                bits += f"（{p['affiliation']}）"
            prompt_lines.append(f"- {bits}")
            
    prompt_lines.extend([
        "========================================",
        "【中英文對照段落資訊】",
        f"英文段落數: {len(en_paras)} / 中文段落數: {len(zh_paras)}",
        "",
    ])
    
    max_len = max(len(en_paras), len(zh_paras))
    for i in range(max_len):
        en_text = en_paras[i] if i < len(en_paras) else ""
        zh_text = zh_paras[i] if i < len(zh_paras) else ""
        prompt_lines.append(f"【段落 {i+1}】")
        prompt_lines.append(f"英文: {en_text}")
        prompt_lines.append(f"中文: {zh_text}")
        prompt_lines.append("-------------------")
        
    prompt_lines.extend([
        "",
        "========================================",
        "請根據上述 Behaviors and Rules 規範，輸出標註發言者且經方案 B 合併（連續發言以 <br> 換行，不留空行，換人才分段）後的繁體中文 Markdown 內容。",
        "重要：只輸出處理後的 Markdown 譯文本體，不要輸出 any 額外的前言或說明文字！",
    ])
    
    print("\n".join(prompt_lines))

if __name__ == "__main__":
    main()
