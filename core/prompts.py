import json
from core.utils import *

# ==============================================================================
# [Version C++ Dynamic] Domain Knowledge Base (Intelligent Logic Edition)
# ==============================================================================

# 防止网页渲染截断
J_START = "```json"
J_END = "```"

# 1. 核心术语规则 (保持不变，这是硬知识)
STATIC_CHESS_RULES = """
<Chess Terminology Standards>
**I. STRICT PIECE MAPPING**
- King = 王, Queen = 后, Rook = 车, Bishop = 象, Knight = 马, Pawn = 兵.
- Piece = 棋子.

**II. TACTICAL CONCEPTS (CRITICAL)**
- **"Gain a move" / "Extra move"** -> 抢先 / 得先 / 赚取时差 (**ABSOLUTELY FORBIDDEN**: "多走一步").
- "Tempo" -> 先手 / 节奏.
- **"Deflect"** -> 引离.
- "Decoy" -> 引入.
- "Fork" -> 捉双 (Context: if targeting King & Rook -> "王车双击").
- "Pin" -> 牵制.
- "Skewer" -> 串击.
- "Discovered Attack" -> 闪击.
- **"Intermediate move"** -> 中间着 (Unified).
- "Blunder" -> 败着 / 大漏勺.
- "Sacrifice" -> 弃子.
- "Exchange" -> 交换.
- "Material" -> 子力.

**III. CONTEXT AWARENESS**
- "Rank" = 横线 (board) vs 排名 (player).
- "File" = 直线 (board) vs 文件 (file).
- "White/Black" = 白方/黑方.
- "Mate" = 杀棋 / 杀招.

**IV. OPENING NAMES DICTIONARY (FULL)**
- Sicilian -> 西西里防御
- Ruy Lopez / Spanish -> 西班牙开局
- Italian Game -> 意大利开局
- Caro-Kann -> 卡罗康防御
- French Defense -> 法兰西防御
- Scandinavian -> 斯堪的纳维亚防御
- Pirc -> 皮尔茨防御
- Alekhine -> 阿廖欣防御
- King's Indian -> 古印度防御
- Queen's Indian -> 新印度防御
- Nimzo-Indian -> 尼姆佐-印度防御
- Grunfeld -> 格林菲尔德防御
- Benoni -> 别诺尼防御
- Dutch -> 荷兰防御
- English Opening -> 英国式开局
- Reti -> 列蒂开局 
- Catalan -> 卡塔兰开局
- London System -> 伦敦体系
- Queen's Gambit -> 后翼弃兵
- King's Gambit -> 王翼弃兵
- Evans Gambit -> 伊文斯弃兵
- Scotch Gambit -> 苏格兰弃兵
- Scotch -> 苏格兰开局
- Vienna Gambit -> 维也纳弃兵
- Vienna -> 维也纳开局
- Walbrodt-Baird Gambit -> 瓦尔布罗德-贝尔德弃兵
- Mueller Gambit -> 穆勒弃兵
- Petrov / Russian -> 俄罗斯防御
- Trompowsky -> 特罗姆波夫斯基攻击
- Slav -> 斯拉夫防御
- Bird's Opening -> 伯德开局
</Chess Terminology Standards>
"""

# 2. 字幕风格与逻辑约束 (代词逻辑彻底通用化)
SUBTITLE_CONSTRAINTS = """
<Subtitle Style Guidelines>
1. **Role**: You are an **Expert Chess Commentator**. 

2. **🛡️ ASR Error Correction Logic (GENERIC)**: 
   - **Context**: The source text is from speech recognition and contains **phonetic errors** (homophones).
   - **Rule**: **Logic > Literal**. If a word makes no sense in a Chess context, you MUST infer the intended **phonetically similar** chess term.
   - **Examples of Logic**:
     - "Rear lines" (Nonsense) -> sounds like -> "Rare lines" (Chess term: 冷门变化).
     - "Crunchy move" (Food?) -> sounds like -> "Crushing move" (Chess term: 毁灭性).
     - "Night f3" (Time?) -> sounds like -> "Knight f3" (Chess piece).

3. **Dynamic Perspective Logic (Instructional)**:
   - **Context**: This is an instructional video where the speaker teaches ONE side (The Protagonist) against the other (The Opponent).
   - **Task**: Dynamically infer which color is the Protagonist based on context (e.g., "We play..." implies the Protagonist).
   - **Pronoun Rule**:
     - "He/They" referring to **Protagonist** -> Translate as **"你" (You)** or **"我们" (We)** (Engage the viewer).
     - "He/They" referring to **Opponent** -> Translate as **"对手" (Opponent)** or **"白方/黑方" (The specific color)**.
     - **Objective**: Maintain a "Teacher-Student" dialogue, never a "Third-person observer" tone for the main action.

4. **Style & Inference**: 
   - Use vivid commentary style (e.g., "战火" for conflict).
   - **Smart Inference**: "Rook in the corner" -> "h8 的车" (if logic fits).
   - **Clean Stuttering**: Remove repeated words (e.g., 'Bc5... Bc5' -> 'Bc5').

5. **Formatting & Notation**:
   - **NO** trailing periods.
   - **Notation Logic**: 
     - `Nf3` -> "马f3".
     - `Bc5` -> "象c5".
     - `Bxc5` -> "象吃c5" or "象c5".
     - Pawn moves (`e4`) -> "e4" or "冲兵e4".

6. **Syntactical Logic**:
   - "Take Nc5" -> "吃掉 c5 的马" (Natural Chinese order).

7. **Numerals**:
   - Moves -> Arabic ("1. e4").
   - Quantities -> Chinese ("两个兵").
</Subtitle Style Guidelines>
"""

## ================================================================
# @ step4_splitbymeaning.py
def get_split_prompt(sentence, num_parts=2, word_limit=20):
    language = load_key("whisper.detected_language")
    json_example = '{\n    "split": [\n        "Part 1 string...",\n        "Part 2 string..."\n    ]\n}'
    
    return f"""
## Role
You are a Netflix subtitle splitter for Chess content in **{language}**.

## Task
Split the text into a **list of {num_parts} parts**.

## Critical Rules
1. **Protect Notation**: NEVER split algebraic notations (e.g., "1. e4", "Nf3").
2. **Format**: Return a direct JSON List of Strings.

## Input
"{sentence}"

## Output Format
Return ONLY JSON.
{J_START}
{json_example}
{J_END}
""".strip()

## ================================================================
# @ step4_1_summarize.py
def get_summary_prompt(source_content, custom_terms_json=None):
    terms_note = ""
    if custom_terms_json:
        terms_str = "\n".join([f"- {t['src']}: {t['tgt']}" for t in custom_terms_json['terms']])
        terms_note = f"\n### Forbidden Terms (Already Known)\n{terms_str}"

    json_example = '{\n  "theme": "Summary here...",\n  "terms": [\n    { "src": "Term", "tgt": "Translation", "note": "Note" }\n  ]\n}'

    return f"""
## Role
You are a Chess Content Analyst.

## Task
1. Summarize content in 2 sentences.
2. Extract **Opening Names** or **Named Tactics**.
3. **Ignore** common moves (e.g., "e4") or generic terms.

{STATIC_CHESS_RULES}
{terms_note}

## Input
{source_content}

## Output Format
{J_START}
{json_example}
{J_END}
""".strip()

## ================================================================
# @ step5_translate.py (BATCH VERSION - CORE)
def get_batch_translation_prompt(target_lines, context_before, context_after):
    tgt_lang = load_key("target_language")
    
    input_data = {
        "context_previous": context_before,
        "batch_to_translate": target_lines,
        "context_next": context_after
    }
    input_json = json.dumps(input_data, indent=2, ensure_ascii=False)
    json_example = '{\n    "translation": [\n        "Translation of line 1",\n        "Translation of line 2"\n    ]\n}'

    return f"""
## Role
You are a **Professional Chess Commentator** translating for **{tgt_lang}** audience.

## Task
Translate the `batch_to_translate` list.
Use `context_previous` and `context_next` to understand the board situation, **correct ASR errors**, and infer missing details.

## Critical Rules
1. **ONE-TO-ONE MAPPING**: The output list MUST have exactly the same number of lines as the input. 
   - **DO NOT MERGE LINES**.
   
2. **ASR Correction (Logic > Literal)**:
   - The source contains phonetic errors.
   - If a word implies a chess impossibility (e.g., "Rear lines", "Peace"), correct it to the phonetic match ("Rare lines", "Piece").

3. **Dynamic Perspective**:
   - Determine who is the "Protagonist" (the side being taught).
   - Translate "He" referring to Protagonist as **"你" (You)** or **"我们" (We)**.
   - Translate "He" referring to Opponent as **"对手" (Opponent)** or the specific color.

4. **Terminology**: 
   - **"Gained a move"** MUST be "抢先" or "得先".
   - **"Fork"** -> "捉双".
   - **"Deflect"** -> "引离".
   
5. **Style**: 
   - Be expressive and vivid.

{STATIC_CHESS_RULES}
{SUBTITLE_CONSTRAINTS}

## Input Data (JSON)
{J_START}
{input_json}
{J_END}

## Output Format
Return a JSON object containing ONLY the translated list.

{J_START}
{json_example}
{J_END}
Note: Start with {J_START} and end with {J_END}.
""".strip()

## ================================================================
# @ step6_splitforsub.py
def get_align_prompt(src_sub, tr_sub, src_part):
    targ_lang = load_key("target_language")
    src_lang = load_key("whisper.detected_language")
    src_part_display = src_part.replace('\n', ' | ')
    json_example = '{\n    "align": [\n        { "src_part": "Source 1", "target_part": "Target 1" },\n        { "src_part": "Source 2", "target_part": "Target 2" }\n    ]\n}'

    return f"""
## Role
Subtitle Alignment Expert.

## Task
Align the {targ_lang} translation to match the structure of the {src_lang} splits.

## Rules
1. **Notation Protection**: Keep "e4", "Nf3" intact.
2. **Timing**: Meaning must match.
3. **No Trailing Periods**.

## Input Data
Source Full: "{src_sub}"
Translation Full: "{tr_sub}"
Split Structure: "{src_part_display}"

## Output Format
{J_START}
{json_example}
{J_END}
""".strip()

## ================================================================
# @ step8 & step10 (Audio Generation)
def get_subtitle_trim_prompt(text, duration):
    json_example = '{\n    "result": "Optimized text"\n}'
    
    return f"""
## Role
Subtitle Editor.

## Task
Shorten the subtitle to fit {duration} seconds.
1. Remove filler words.
2. **Keep Chess Moves (e.g. "e4") UNTOUCHED.**

## Input
"{text}"

## Output Format
{J_START}
{json_example}
{J_END}
""".strip()

## ================================================================
# @ tts_main
def get_correct_text_prompt(text):
    json_example = '{\n    "text": "Cleaned text"\n}'
    
    return f"""
## Role
Text Cleaner for TTS.

## Task
1. Remove unsupported symbols.
2. **Keep Chess Moves (e.g., "Nf3") EXACTLY AS IS.**
3. Pronunciation: Convert "1." to "one dot" ONLY if it helps pronunciation.

## Input
"{text}"

## Output Format
{J_START}
{json_example}
{J_END}
""".strip()