# 逐字稿翻譯規格（所有翻譯派工共用）

工作目錄：`/Users/lanss/projects/2_Practice/events/Agentic AI Summit 2026`

## 任務

把指定區塊檔（`day1_zh/tools/chunks/<stage>/<檔名>.json`）裡的英文逐字稿翻成**台灣用語繁體中文**，寫成同名 `.md`，放到 `day1_zh/tools/zh_chunks/<stage>/<檔名>.md`（目錄不存在請建立）。

## 輸入檔欄位

| 欄位 | 意義 |
|---|---|
| `stage` / `stage_name_zh` | 舞台代號與中文名 |
| `part` | `morning` / `afternoon` |
| `session_index` / `chunk` / `chunk_total` | 議程編號、本區塊序號、該議程總區塊數 |
| `is_first_chunk` | 是否為該議程第一塊（決定要不要輸出節標題） |
| `time_label` / `title` | 議程時間與**繁中標題**（權威，直接用） |
| `speakers` | 講者陣列：`name`（英文姓名，權威）、`affiliation`（中文職稱，權威）、`role`、`topic`（中文講題，權威） |
| `paragraphs` | 待翻譯的英文段落陣列，已濾除填充語 |

## 輸出格式

`is_first_chunk` 為 `true` 時，先輸出節標題區塊，再接內文：

```markdown
## [時間] 議程標題

**講者**
- Peter DeSantis（Amazon 基礎 AI 模型、客製化晶片與量子運算資深副總裁）—— 限制驅動創新：探討 AI 系統問題
- 另一位講者（職稱）—— 講題

譯文第一段……

譯文第二段……
```

`is_first_chunk` 為 `false` 時，**不要**輸出標題與講者區塊，直接從譯文段落開始（這塊會被接在前一塊後面）。

角色不是「講者」時（`role` 為主持人／與談人／對談嘉賓／工作坊帶領人等），照該欄位標示，例如 `- Todd Graham（M12 執行合夥人）—— 主持人`。`topic` 為空就省略破折號後半段。

## 翻譯要求

1. **台灣用語繁體中文**。技術術語沿用台灣慣例：software 軟體、program 程式、data 資料、network 網路、default 預設、performance 效能、quality 品質、robot 機器人、optimize 最佳化。不要出現「軟件」「程序」「數據」「網絡」「默認」「性能」「質量」「機器人學」等中國大陸用語
2. **忠實完整翻譯，不摘要、不濃縮、不跳過段落**。輸入有幾段就譯幾段，段落順序不變
3. **人名一律以 `speakers` 的英文拼法為準**。逐字稿是自動轉錄，人名常拼錯（例如 Jianfeng Gao 被聽成 "Zhang Gao"、Markus Buehler 被聽成 "Mark Spuhler"、Krishnaram Kenthapadi 被聽成 "Kushneram Kinthapati"）。譯文中提到講者時，用 `speakers` 裡的正確英文姓名，不要音譯成中文，也不要沿用錯誤拼法
4. 公司、產品、模型名稱保留英文原文（OpenAI、DeepMind、vLLM、Claude、GPT…）。專有技術詞第一次出現時可用「中文（English）」形式，之後只用中文
5. 轉錄明顯的同音錯字（如把 "agentic" 聽成 "Agentec"、"Lightmatter" 聽成 "Light Matter"）依上下文譯出正確意思
6. 口語重複、語塞、講者自我修正可以順順地整理成通順中文，但**不可刪掉實質內容**
7. 段落切分沿用輸入的段落界線；單段太長（超過 400 字）可在語意轉折處拆成兩段
8. 遇到明顯聽錯導致整句不知所云的地方，照字面譯出並在該處加上 `<!-- 轉錄不清 -->`，不要自己編造內容補洞
9. 不要加入原文沒有的評論、摘要、小標題、結語

## 邊界

- 只新增自己那一個 `.md` 檔，不要碰其他區塊的檔案
- 不要修改 `chunks/`、`segments/`、`cleaned/`、`agenda.json`、`en_srt/` 或任何既有檔案
- 不要寫任何腳本，不要跑批次處理，只處理指派給你的那一塊

## 完成前自檢

- 輸出的段落數與輸入 `paragraphs` 陣列長度一致（拆長段的情況除外，此時只會變多不會變少）
- 全篇沒有殘留英文句子（保留的專有名詞除外）
- 沒有出現中國大陸用語
- `is_first_chunk` 為 false 的區塊，檔案開頭不是 `##` 標題
