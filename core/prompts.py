import json
from core.utils import *

# ==============================================================================
# [Grandmaster Edition] Domain Knowledge Base (Instructional Video Specialized)
# ==============================================================================
# 核心改动：
# 1. 移除了 CASE A/B 检测，默认锁定为国象教学模式。
# 2. 增加了 Rank/File 的逻辑判断（默认是棋盘，除非出现 Player/World 等词）。
# 3. 增加了“防幻觉”警告（Ready != Reti, Bad != Bird）。
# 4. 完善了开局名列表。

CHESS_INSTRUCTION = """
<Chess Instruction Standards>
You are translating an **International Chess Instructional Video** (Analysis/Lecture).
Your target audience is chess learners. 
**Goal**: Accuracy > Creativity. The viewer wants to learn chess concepts, not read poetry.

**I. STRICT PIECE MAPPING (Non-negotiable)**
- King = 王 (Not 国王)
- Queen = 后 (Not 王后/女王)
- Rook = 车 (Sound: Ju. Not 城堡/岩石)
- Bishop = 象 (Not 主教)
- Knight = 马 (Not 骑士/爵士)
- Pawn = 兵 (Not 卒/典当)
- Piece = 棋子 (When referring to units on board) | Material = 子力 (Total value)

**II. CONTEXT-AWARE LOGIC (Crucial)**
1. **"Rank"**:
   - DEFAULT: **"横线"** (Board geometry, rows 1-8). e.g., "Back rank" -> "底线".
   - EXCEPTION: If followed by "Player", "Grandmaster", "World", "Top" -> **"排名"**.
2. **"File"**:
   - DEFAULT: **"直线"** (Board columns a-h). e.g., "Open file" -> "开放线", "C-file" -> "C线".
   - EXCEPTION: If referring to PGN/Data/Computer -> **"文件"**.
3. **"Promotion"**: **升变** (Not 晋升/促销).
4. **"Mate"**: **将死** (Not 伙伴/配偶). "Checkmate" -> "将死". "Check" -> "将军".
5. **Pronouns (The "He" Trap)**: 
   - When referring to a Piece (Knight/Bishop/Rook): Translate "He/She" as **"它"** or repeat the piece name.
   - When referring to a Player/Opponent: Translate "He" as **"他"**.

**III. OPENING NAMES DICTIONARY**
*Rule: Only use these if the specific name is CLEARLY audible. Do not guess based on similar sounds.*
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
- Nimzo-Indian -> 尼姆佐维奇防御
- Grunfeld -> 格林菲尔德防御
- Benoni -> 别诺尼防御
- Dutch -> 荷兰防御
- English Opening -> 英国式开局
- Reti -> 列蒂开局 (WARNING: Do NOT confuse with "Ready")
- Catalan -> 卡塔兰开局
- London System -> 伦敦体系
- Evans Gambit -> 伊文斯弃兵
- Scotch -> 苏格兰开局
- Petrov / Russian -> 俄罗斯防御
- Vienna -> 维也纳开局
- Trompowsky -> 特罗姆波夫斯基攻击
- Slav -> 斯拉夫防御
- Bird's Opening -> 伯德开局 (WARNING: Do NOT confuse with "Bad")

**IV. ACTION VERBS**
- "Sacrifice" -> 弃子
- "Exchange" -> 交换 (The Exchange -> 得半子)
- "Fork" -> 捉双 | "Pin" -> 牵制 | "Skewer" -> 串击
- "Develop" -> 出子 | "Fianchetto" -> 堡垒象/侧翼出象
- "Blunder" -> 恶手/大漏着 | "Gambit" -> 弃兵

**V. NOTATION RULE**
- Keep algebraic moves (e.g., "e4", "Nf3", "O-O", "Bxc5") EXACTLY as is.
- If the source is spoken text (e.g., "Knight to f3"), translate to Chinese term + coord (e.g., "马跳f3" or "马f3").
</Chess Instruction Standards>
"""

## ================================================================
# @ step4_splitbymeaning.py
def get_split_prompt(sentence, num_parts = 2, word_limit = 20):
    language = load_key("whisper.detected_language")
    split_prompt = f"""
## Role
You are a professional subtitle splitter for Chess Videos in **{language}**.

## Task
Split the text into **{num_parts}** parts (max **{word_limit}** words each).

## Critical Rules
1. **Chess Notation Protection**: NEVER split algebraic notations (e.g., "1. e4", "Nf3", "Bxc5"). 
   - "Bxc5" cannot be "Bx" [br] "c5".
   - Keep move number with the move: "1. e4" stays together.
2. Balance length and meaning.

## Given Text
<split_this_sentence>
{sentence}
</split_this_sentence>

## Output in only JSON format and no other text
""" + """```json
{
    "analysis": "Check for chess notations to protect",
    "split1": "Approach 1 with [br]",
    "split2": "Approach 2 with [br]",
    "assess": "Which preserves notation best?",
    "choice": "1 or 2"
}
```""" + f"""

Note: Start you answer with ```json and end with ```, do not add any other text.
""".strip()
    return split_prompt

## ================================================================
# @ step4_1_summarize.py
def get_summary_prompt(source_content, custom_terms_json=None):
    src_lang = load_key("whisper.detected_language")
    tgt_lang = load_key("target_language")
    
    terms_note = ""
    if custom_terms_json:
        terms_list = []
        for term in custom_terms_json['terms']:
            terms_list.append(f"- {term['src']}: {term['tgt']} ({term['note']})")
        terms_note = "\n### Existing Terms\nPlease exclude these terms in your extraction:\n" + "\n".join(terms_list)
    
    # 修改点：更保守的术语提取，避免把 e4, attack 这种通用词提出来
    summary_prompt = f"""
## Role
You are a Chess Terminology Analyst.

## Task
1. Summarize the video content in two sentences.
2. **Conservative Term Extraction**:
   - Extract **Opening Names** ONLY if clearly audible (e.g., "Sicilian Defense").
   - Extract **Named Tactics** (e.g., "Windmill", "Smothered Mate").
   - **CRITICAL**: Do NOT extract common moves (e.g., "e4", "Nf3") or generic words (e.g., "Attack", "Defense") as terms.
   - **CRITICAL**: If Whisper output is messy/gibberish, IGNORE it. Do not guess terms.

{terms_note}

{CHESS_INSTRUCTION}

## INPUT
<text>
{source_content}
</text>

## Output in only JSON format and no other text
{{
  "theme": "Two-sentence summary",
  "terms": [
    {{
      "src": "Source term",
      "tgt": "Target translation", 
      "note": "Brief explanation"
    }}
  ]
}}  

Note: Start you answer with ```json and end with ```, do not add any other text.
""".strip()
    return summary_prompt

## ================================================================
# @ step5_translate.py & translate_lines.py
def generate_shared_prompt(previous_content_prompt, after_content_prompt, summary_prompt, things_to_note_prompt):
    return f'''### Context Information
<previous_content>
{previous_content_prompt}
</previous_content>
**INSTRUCTION**: Use the context to track board state and disambiguate terms (e.g., Is "Rank" a line or a standing?).

<subsequent_content>
{after_content_prompt}
</subsequent_content>

### Content Summary & Terminology
{summary_prompt}

### Points to Note
{things_to_note_prompt}'''

def get_prompt_faithfulness(lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    line_splits = lines.split('\n')
    
    json_dict = {}
    for i, line in enumerate(line_splits, 1):
        json_dict[f"{i}"] = {"origin": line, "direct": f"direct {TARGET_LANGUAGE} translation {i}."}
    json_format = json.dumps(json_dict, indent=2, ensure_ascii=False)

    src_language = load_key("whisper.detected_language")
    
    # 修改点：角色锁定为 Chess Translator
    prompt_faithfulness = f'''
## Role
You are an expert **Chess Translator**.
Your expertise lies in accurately understanding International Chess terminology and converting it faithfully to {TARGET_LANGUAGE}.

## Task
1. Translate line by line.
2. **Context Check**: Use the provided context to resolve pronouns (He vs It) and ambiguous terms (Rank/File).

{shared_prompt}

{CHESS_INSTRUCTION}

## INPUT
<subtitles>
{lines}
</subtitles>

## Output in only JSON format and no other text
''' + f'''```json
{json_format}
```''' + '''

Note: Start you answer with ```json and end with ```, do not add any other text.
'''
    return prompt_faithfulness.strip()


def get_prompt_expressiveness(faithfulness_result, lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    
    # 修改点：Reflect 逻辑大幅增强
    json_format = {
        key: {
            "origin": value["origin"],
            "direct": value["direct"],
            "reflect": "Step-by-step logic: 1.Check Ambiguity (Rank/File). 2.Verify Terms. 3.Check Pronouns.",
            "free": "Natural Instructional translation"
        }
        for key, value in faithfulness_result.items()
    }
    json_format = json.dumps(json_format, indent=2, ensure_ascii=False)

    src_language = load_key("whisper.detected_language")
    
    prompt_expressiveness = f'''
## Role
You are an expert **Chess Translator**.
You are translating a video for Chinese chess players.

## Goal
**Accuracy > Creativity**. 
The viewer wants to learn chess, not read poetry. Use standard terminology.

## The "Reflect" Workflow (Strict Execution)
For each line, you must perform these checks in the "reflect" field:

1. **Ambiguity Check (The "Rank/File" Trap)**:
   - If the word "Rank" appears: Does it mean "Board Row" (Standard) or "Player Standing" (Context: World/Top/High)?
   - If the word "File" appears: Does it mean "Board Column" (Standard) or "Document" (Context: PGN/Computer)?
   - *Logic*: If context is unclear, default to **Board Terminology** for this video type.

2. **Hallucination Check**:
   - Did the audio *clearly* say an Opening Name? 
   - Warning: "Ready" != "Reti". "Bad" != "Bird". "Night" == "Knight".
   - If unsure, translate literally. DO NOT invent terms.

3. **Pronoun Check**:
   - "He is attacking the queen." -> Who is "He"?
   - If "He" = A piece (Knight/Bishop) -> Translate as "它" or the piece name.
   - If "He" = The opponent -> Translate as "他/白方/黑方".

## Translation Style
- **Professional**: Use "白方/黑方" for White/Black.
- **Concise**: "Control the center" -> "控制中心" (Not "去控制这个中心").
- **Notation**: NEVER change "e4", "Nf3".

{shared_prompt}

{CHESS_INSTRUCTION}

## INPUT
<subtitles>
{lines}
</subtitles>

## Output in only JSON format and no other text
''' + f'''```json
{json_format}
```''' + '''

Note: Start you answer with ```json and end with ```, do not add any other text.
'''
    return prompt_expressiveness.strip()

## ================================================================
# @ step6_splitforsub.py
def get_align_prompt(src_sub, tr_sub, src_part):
    targ_lang = load_key("target_language")
    src_lang = load_key("whisper.detected_language")
    src_splits = src_part.split('\n')
    num_parts = len(src_splits)
    src_part = src_part.replace('\n', ' [br] ')
    align_parts_json = ','.join(
        f'''
        {{
            "src_part_{i+1}": "{src_splits[i]}",
            "target_part_{i+1}": "Corresponding aligned {targ_lang} subtitle part"
        }}''' for i in range(num_parts)
    )

    align_prompt = f'''
## Role
You are a Netflix subtitle alignment expert.

## Task
Align and split the {targ_lang} subtitles to match the structure of the {src_lang} source.

## Rules
1. **Chess Notation Protection**: NEVER split algebraic notations (e.g., "1. e4", "Nf3") across two lines. They must stay intact.
2. Analyze word order differences between languages.
3. Ensure the meaning matches the time segments.

## INPUT
<subtitles>
{src_lang} Original: "{src_sub}"
{targ_lang} Original: "{tr_sub}"
Pre-processed {src_lang} Subtitles ([br] indicates split points): {src_part}
</subtitles>

## Output in only JSON format and no other text
''' + f'''```json
{{
    "analysis": "Brief analysis of alignment strategy and check for notation safety",
    "align": [
        {align_parts_json}
    ]
}}
```''' + '''

Note: Start you answer with ```json and end with ```, do not add any other text.
'''.strip()
    return align_prompt

## ================================================================
# @ step8_gen_audio_task.py @ step10_gen_audio.py
def get_subtitle_trim_prompt(text, duration):
    rule = '''Consider:
    a. Reducing filler words.
    b. Omitting unnecessary pronouns.'''

    trim_prompt = f'''
## Role
You are a professional subtitle editor.

## INPUT
<subtitles>
Subtitle: "{text}"
Duration: {duration} seconds
</subtitles>

## Processing Rules
{rule}
- **CRITICAL for Chess**: 
  - DO NOT shorten algebraic notations (e.g., "Nf3", "O-O"). 
  - DO NOT remove "Checkmate" or "Check".
  - You MAY shorten descriptive text (e.g., "He moves the Knight" -> "He moves Knight").

## Output in only JSON format and no other text
''' + '''```json
{
    "analysis": "Brief analysis of length and content type (Chess or General)",
    "result": "Optimized subtitle"
}
```''' + '''

Note: Start you answer with ```json and end with ```, do not add any other text.
'''.strip()
    return trim_prompt

## ================================================================
# @ tts_main
def get_correct_text_prompt(text):
    return f'''
## Role
You are a text cleaning expert for TTS.

## Task
1. Keep basic punctuation (.,?!).
2. **Chess Check**: If the text contains moves like "e4" or "Nf3", KEEP THEM EXACTLY AS IS. Do not expand them.
3. Convert non-standard symbols to readable text if necessary, but touch nothing else.

## INPUT
{text}

## Output in only JSON format and no other text
''' + '''```json
{
    "text": "cleaned text here"
}
```''' + '''

Note: Start you answer with ```json and end with ```, do not add any other text.
'''.strip()
    return get_correct_text_prompt