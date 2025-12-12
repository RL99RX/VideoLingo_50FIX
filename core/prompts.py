import json
from core.utils import *

# ==============================================================================
# [Grandmaster Edition] Domain Knowledge Base (Instructional Video Specialized)
# ==============================================================================

CHESS_INSTRUCTION = """<Chess Instruction Standards>
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
1. **'Rank'**:
   - DEFAULT: **'横线'** (Board geometry, rows 1-8). e.g., 'Back rank' -> '底线'.
   - EXCEPTION: If followed by 'Player', 'Grandmaster', 'World', 'Top' -> **'排名'**.
2. **'File'**:
   - DEFAULT: **'直线'** (Board columns a-h). e.g., 'Open file' -> '开放线', 'C-file' -> 'C线'.
   - EXCEPTION: If referring to PGN/Data/Computer -> **'文件'**.
3. **'Promotion'**: **升变** (Not 晋升/促销).
4. **'Mate'**: **将死** (Not 伙伴/配偶). 'Checkmate' -> '将死'. 'Check' -> '将军'.
5. **Pronouns (The 'He' Trap)**: 
   - When referring to a Piece (Knight/Bishop/Rook): Translate 'He/She' as **'它'** or repeat the piece name.
   - When referring to a Player/Opponent: Translate 'He' as **'他'**.

**III. OPENING NAMES DICTIONARY**
*Rule: Only use these if the specific name is CLEARLY audible or phonetically similar.*
- Sicilian -> 西西里防御
- Ruy Lopez / Spanish -> 西班牙开局
- Italian Game -> 意大利开局
- Caro-Kann -> 卡罗康防御
- French Defense -> 法兰西防御
- Scandinavian -> 斯堪的纳维亚防御
- Pirc -> 皮尔茨防御
- Alekhine -> 阿廖欣防御

# 印度防御系列
- King's Indian -> 古印度防御
- Queen's Indian -> 新印度防御
- Nimzo-Indian -> 尼姆佐-印度防御
- Grunfeld -> 格林菲尔德防御
- Benoni -> 别诺尼防御
- Dutch -> 荷兰防御
- English Opening -> 英国式开局
- Reti -> 列蒂开局 (WARNING: Do NOT confuse with 'Ready')
- Catalan -> 卡塔兰开局
- London System -> 伦敦体系

# 弃兵系列 (Specific Rules First!)
- Queen's Gambit -> 后翼弃兵
- King's Gambit -> 王翼弃兵
- Evans Gambit -> 伊文斯弃兵
- Scotch Gambit -> 苏格兰弃兵
- Scotch -> 苏格兰开局
- Vienna Gambit -> 维也纳弃兵
- Vienna -> 维也纳开局
# 新增修正项
- Walbrodt-Baird Gambit -> 瓦尔布罗德-贝尔德弃兵
- Mueller Gambit -> 穆勒弃兵

- Petrov / Russian -> 俄罗斯防御
- Trompowsky -> 特罗姆波夫斯基攻击
- Slav -> 斯拉夫防御
- Bird's Opening -> 伯德开局 (WARNING: Do NOT confuse with 'Bad')

**IV. SPECIAL FIXES & ASR ERROR HANDLING**
1. **Castle / Castling**: **王车易位** (Default).
   - Context: Even if the grammar is odd (e.g., 'weapons are castle'), it refers to the move '王车易位'.
2. **Phonetic Recovery Strategy (Anti-Hallucination)**:
   - **Issue**: ASR often misinterprets rare names as random words (e.g., 'Wall-broke bared' -> 'Walbrodt-Baird').
   - **Action**: Check the Dictionary for sound-alikes first.
   - **Fallback**: If not in dictionary, use **Sound Transliteration** (音译). 
   - **Prohibition**: NEVER translate literal meanings of broken words if they don't make sense (e.g., 'Bared' != 裸露, likely 'Baird' -> '贝尔德').

**V. ACTION VERBS**
- 'Sacrifice' -> 弃子
- 'Exchange' -> 交换 (The Exchange -> 得半子)
- 'Fork' -> 捉双 | 'Pin' -> 牵制 | 'Skewer' -> 串击
- 'Develop' -> 出子 | 'Fianchetto' -> 堡垒象/侧翼出象
- 'Blunder' -> 恶手/大漏着 | 'Gambit' -> 弃兵

**VI. NOTATION RULE**
- Keep algebraic moves (e.g., 'e4', 'Nf3', 'O-O', 'Bxc5') EXACTLY as is.
- If the source is spoken text (e.g., 'Knight to f3'), translate to Chinese term + coord (e.g., '马跳f3' or '马f3').
</Chess Instruction Standards>
"""

## ================================================================
# @ step4_splitbymeaning.py
def get_split_prompt(sentence, num_parts=2, word_limit=20):
    language = load_key("whisper.detected_language")
    
    prompt_head = f"""## Role
You are a professional subtitle splitter for Chess Videos in **{language}**.

## Task
Split the text into a **list of {num_parts} parts** (max {word_limit} words each).

## Critical Rules
1. **Chess Notation Protection**: NEVER split algebraic notations (e.g., '1. e4', 'Nf3', 'Bxc5'). 
   - 'Bxc5' cannot be split.
   - Keep move number with the move: '1. e4' stays together.
2. **Output Format**: Return a direct List of Strings. Do NOT use tags like [br].
3. Balance length and meaning.

## Given Text
<split_this_sentence>
{sentence}
</split_this_sentence>
"""
    # 使用拼接避免网页渲染错误
    prompt_tail = """
## Output Format
""" + "```json" + """
{
    "analysis": "Check for chess notations to protect",
    "split": [
        "Split Part 1 string...",
        "Split Part 2 string..."
    ]
}
""" + "```" + """
Note: Start you answer with """ + "```json and end with ```" + """, do not add any other text."""
    
    return prompt_head + prompt_tail

## ================================================================
# @ step4_1_summarize.py
def get_summary_prompt(source_content, custom_terms_json=None):
    src_lang = load_key("whisper.detected_language")
    
    terms_note = ""
    if custom_terms_json:
        terms_list = []
        for term in custom_terms_json['terms']:
            terms_list.append(f"- {term['src']}: {term['tgt']} ({term['note']})")
        terms_note = "\n### Existing Terms\nPlease exclude these terms in your extraction:\n" + "\n".join(terms_list)
    
    prompt_head = f"""## Role
You are a Chess Terminology Analyst.

## Task
1. Summarize the video content in two sentences.
2. **Conservative Term Extraction**:
   - Extract **Opening Names** ONLY if clearly audible (e.g., 'Sicilian Defense').
   - Extract **Named Tactics** (e.g., 'Windmill', 'Smothered Mate').
   - **CRITICAL**: Do NOT extract common moves (e.g., 'e4', 'Nf3') or generic words (e.g., 'Attack', 'Defense') as terms.
   - **CRITICAL**: If Whisper output is messy/gibberish, IGNORE it. Do not guess terms.
{terms_note}

{CHESS_INSTRUCTION}

## INPUT
<text>
{source_content}
</text>
"""
    prompt_tail = """
## Output Format
""" + "```json" + """
{
  "theme": "Two-sentence summary",
  "terms": [
    {
      "src": "Source term",
      "tgt": "Target translation", 
      "note": "Brief explanation"
    }
  ]
}
""" + "```" + """
Note: Start you answer with """ + "```json and end with ```" + """, do not add any other text."""
    return prompt_head + prompt_tail

## ================================================================
# @ step5_translate.py & translate_lines.py
def generate_shared_prompt(previous_content_prompt, after_content_prompt, summary_prompt, things_to_note_prompt):
    return f"""### Context Information
<previous_content>
{previous_content_prompt}
</previous_content>
**INSTRUCTION**: Use the context to track board state and disambiguate terms (e.g., Is 'Rank' a line or a standing?).

<subsequent_content>
{after_content_prompt}
</subsequent_content>

### Content Summary & Terminology
{summary_prompt}

### Points to Note
{things_to_note_prompt}"""

def get_prompt_faithfulness(lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    
    # 使用 strip 防止末尾空行导致的计数错误
    line_splits = lines.strip().split('\n')
    input_json = {}
    for i, line in enumerate(line_splits, 1):
        input_json[f"{i}"] = {"origin": line}
    input_dump = json.dumps(input_json, indent=2, ensure_ascii=False)

    prompt_head = f"""## Role
You are an expert **Chess Translator**.
Your expertise lies in accurately understanding International Chess terminology and converting it faithfully to {TARGET_LANGUAGE}.

## Task
1. Translate line by line based on the JSON index.
2. **Context Check**: Use the provided context to resolve pronouns, BUT NEVER REPEAT CONTEXT.

## 🛡️ CRITICAL ANTI-HALLUCINATION RULES
1. **NO REPETITION**: Do NOT repeat the translation of the previous line. If the current line is a repetition of the previous line in source, translate it again. But if the source is different, the translation MUST be different.
2. **HANDLE SHORT/EMPTY LINES**: 
   - If a line is empty, noise, or just a filler word (e.g., "Um", "Ah", "00:00:12"), output an empty string "" or "...".
   - **NEVER** fill silence with text from the previous line.
3. **Keep Notation**: "e4", "Nf3" must remain unchanged.

{shared_prompt}

{CHESS_INSTRUCTION}

## INPUT DATA
The following is the source text to translate:
""" + "```json" + f"""
{input_dump}
""" + "```" + """
"""
    prompt_tail = """
## Output Format
Return a JSON object with the 'direct' (Literal Translation) field added.
""" + "```json" + """
{
  "1": {
    "origin": "source text...",
    "direct": "literal translation..."
  }
}
""" + "```" + """
Note: Start you answer with """ + "```json and end with ```" + """, do not add any other text."""
    
    return prompt_head + prompt_tail


def get_prompt_expressiveness(faithfulness_result, lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    
    input_data = json.dumps(faithfulness_result, indent=2, ensure_ascii=False)

    prompt_head = f"""## Role
You are an expert **Chess Translator**.
You are translating a video for Chinese chess players.

## Goal
Produce the final, polished subtitle line.

## The Process (Strict Execution)
For each line, perform two steps:

### Step 1: Reflect (Internal Analysis)
In the 'reflect' field, you MUST act as a chess critic. Analyze:
1. **ASR Error Check**: Does the source look like gibberish (e.g., 'Wall-broke bared')? Check if it sounds like a term in the Dictionary (e.g., 'Walbrodt-Baird').
2. **Ambiguity**: 'Rank' (Row vs Standing)? 'Mate' (Friend vs Checkmate)?
3. **Logic Check**: Does the translation make sense on a chess board?
4. **Tone**: Is this a casual chat or a formal lecture?
5. **Conclusion**: How should I paraphrase this to sound like a native Chinese chess coach?

### Step 2: Free (Final Output)
In the 'free' field, output **ONLY THE TRANSLATED TEXT**.
- ❌ DO NOT explain your style.
- ❌ DO NOT use descriptions.
- ✅ JUST write the Chinese sentence.

{shared_prompt}

{CHESS_INSTRUCTION}

## INPUT DATA
""" + "```json" + f"""
{input_data}
""" + "```" + """
"""

    prompt_tail = """
## Output Format
Return the JSON with 'reflect' and 'free' fields added.
""" + "```json" + """
{
  "1": {
    "origin": "He missed a mate in two.",
    "direct": "他错过了一个配偶在两个里。",
    "reflect": "'Mate' means Checkmate. 'In two' means 2 moves. Tone: Critical.",
    "free": "他错过了两步杀。"
  }
}
""" + "```" + """
Note: Start you answer with """ + "```json and end with ```" + """, do not add any other text."""

    return prompt_head + prompt_tail

## ================================================================
# @ step6_splitforsub.py
def get_align_prompt(src_sub, tr_sub, src_part):
    targ_lang = load_key("target_language")
    src_lang = load_key("whisper.detected_language")
    
    src_splits = src_part.split('\n')
    example_list = []
    for i in range(len(src_splits)):
        # 内部 JSON 结构，小心转义
        example_list.append(f'{{"src_part_{i+1}": "Source text...", "target_part_{i+1}": "Aligned target text..."}}')
    example_json = ",\n        ".join(example_list)
    
    src_part_display = src_part.replace('\n', ' [br] ')

    prompt_head = f"""## Role
You are a Netflix subtitle alignment expert.

## Task
Align and split the {targ_lang} subtitles to match the structure of the {src_lang} source.

## Rules
1. **Chess Notation Protection**: NEVER split algebraic notations (e.g., "1. e4", "Nf3") across two lines. They must stay intact.
2. Analyze word order differences between languages.
3. Ensure the meaning matches the time segments.

## INPUT DATA
<subtitles>
{src_lang} Original: "{src_sub}"
{targ_lang} Original: "{tr_sub}"
Pre-processed {src_lang} Subtitles ([br] indicates split points): {src_part_display}
</subtitles>
"""
    
    prompt_tail = """
## Output Format
""" + "```json" + f"""
{{
    "analysis": "Brief analysis of alignment strategy",
    "align": [
        {example_json}
    ]
}}
""" + "```" + """
Note: Start you answer with """ + "```json and end with ```" + """, do not add any other text."""
    
    return prompt_head + prompt_tail

## ================================================================
# @ step8_gen_audio_task.py @ step10_gen_audio.py
def get_subtitle_trim_prompt(text, duration):
    rule = """Consider:
    a. Reducing filler words.
    b. Omitting unnecessary pronouns."""

    prompt_head = f"""## Role
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
"""
    prompt_tail = """
## Output Format
""" + "```json" + """
{
    "analysis": "Brief analysis of length and content type (Chess or General)",
    "result": "Optimized subtitle"
}
""" + "```" + """
Note: Start you answer with """ + "```json and end with ```" + """, do not add any other text."""
    return prompt_head + prompt_tail

## ================================================================
# @ tts_main
def get_correct_text_prompt(text):
    prompt_head = f"""## Role
You are a text cleaning expert for TTS.

## Task
1. Keep basic punctuation (.,?!).
2. **Chess Check**: If the text contains moves like "e4" or "Nf3", KEEP THEM EXACTLY AS IS. Do not expand them.
3. Convert non-standard symbols to readable text if necessary, but touch nothing else.

## INPUT
{text}
"""
    prompt_tail = """
## Output Format
""" + "```json" + """
{
    "text": "cleaned text here"
}
""" + "```" + """
Note: Start you answer with """ + "```json and end with ```" + """, do not add any other text."""
    return prompt_head + prompt_tail