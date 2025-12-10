import json
from core.utils import *

# ==============================================================================
# [Grandmaster Edition] Domain Knowledge Base (Instructional Video Specialized)
# ==============================================================================

# 修复点：
# 1. 保留了你原版所有的 definitions (I, II, III, IV, V)。
# 2. 在 IV 部分加入了 Walbrodt/Baird 的防幻觉规则。
# 3. 在 II 部分明确了 Castle = 王车易位。
CHESS_INSTRUCTION = (
    "<Chess Instruction Standards>\n"
    "You are translating an **International Chess Instructional Video** (Analysis/Lecture).\n"
    "Your target audience is chess learners. \n"
    "**Goal**: Accuracy > Creativity. The viewer wants to learn chess concepts, not read poetry.\n\n"

    "**I. STRICT PIECE MAPPING (Non-negotiable)**\n"
    "- King = 王 (Not 国王)\n"
    "- Queen = 后 (Not 王后/女王)\n"
    "- Rook = 车 (Sound: Ju. Not 城堡/岩石)\n"
    "- Bishop = 象 (Not 主教)\n"
    "- Knight = 马 (Not 骑士/爵士)\n"
    "- Pawn = 兵 (Not 卒/典当)\n"
    "- Piece = 棋子 (When referring to units on board) | Material = 子力 (Total value)\n\n"

    "**II. CONTEXT-AWARE LOGIC (Crucial)**\n"
    "1. **'Rank'**:\n"
    "   - DEFAULT: **'横线'** (Board geometry, rows 1-8). e.g., 'Back rank' -> '底线'.\n"
    "   - EXCEPTION: If followed by 'Player', 'Grandmaster', 'World', 'Top' -> **'排名'**.\n"
    "2. **'File'**:\n"
    "   - DEFAULT: **'直线'** (Board columns a-h). e.g., 'Open file' -> '开放线', 'C-file' -> 'C线'.\n"
    "   - EXCEPTION: If referring to PGN/Data/Computer -> **'文件'**.\n"
    "3. **'Promotion'**: **升变** (Not 晋升/促销).\n"
    "4. **'Mate'**: **将死** (Not 伙伴/配偶). 'Checkmate' -> '将死'. 'Check' -> '将军'.\n"
    "5. **Pronouns (The 'He' Trap)**: \n"
    "   - When referring to a Piece (Knight/Bishop/Rook): Translate 'He/She' as **'它'** or repeat the piece name.\n"
    "   - When referring to a Player/Opponent: Translate 'He' as **'他'**.\n\n"

    "**III. OPENING NAMES DICTIONARY**\n"
    "*Rule: Only use these if the specific name is CLEARLY audible. Do not guess based on similar sounds.*\n"
    "- Sicilian -> 西西里防御\n"
    "- Ruy Lopez / Spanish -> 西班牙开局\n"
    "- Italian Game -> 意大利开局\n"
    "- Caro-Kann -> 卡罗康防御\n"
    "- French Defense -> 法兰西防御\n"
    "- Scandinavian -> 斯堪的纳维亚防御\n"
    "- Pirc -> 皮尔茨防御\n"
    "- Alekhine -> 阿廖欣防御\n"
    
    # 印度防御系列
    "- King's Indian -> 古印度防御\n"
    "- Queen's Indian -> 新印度防御\n"
    "- Nimzo-Indian -> 尼姆佐-印度防御\n" # 改得好，标准术语
    "- Grunfeld -> 格林菲尔德防御\n"
    "- Benoni -> 别诺尼防御\n"
    "- Dutch -> 荷兰防御\n"
    "- English Opening -> 英国式开局\n"
    "- Reti -> 列蒂开局 (WARNING: Do NOT confuse with 'Ready')\n"
    "- Catalan -> 卡塔兰开局\n"
    "- London System -> 伦敦体系\n"
    
    # 弃兵系列 (Specific Rules First!)
    "- Queen's Gambit -> 后翼弃兵\n"       # 建议新增，出现率极高
    "- King's Gambit -> 王翼弃兵\n"         # 建议新增
    "- Evans Gambit -> 伊文斯弃兵\n"
    "- Scotch Gambit -> 苏格兰弃兵 (Specific Rule)\n"
    "- Scotch -> 苏格兰开局\n"
    "- Vienna Gambit -> 维也纳弃兵 (Specific Rule)\n"
    "- Vienna -> 维也纳开局\n"
    
    "- Petrov / Russian -> 俄罗斯防御\n"
    "- Trompowsky -> 特罗姆波夫斯基攻击\n"
    "- Slav -> 斯拉夫防御\n"
    "- Bird's Opening -> 伯德开局 (WARNING: Do NOT confuse with 'Bad')\n\n"
    
    "**IV. SPECIAL FIXES & ASR ERROR HANDLING**\n"
    "1. **Castle / Castling**: Always **王车易位** (NEVER translate as 城堡 or 堡垒).\n"
    "2. **Rare Names**: If you hear 'Wall-broke' or 'Bared' (especially in Gambit names), it is likely **Walbrodt** or **Baird**.\n"
    "   - Rule: Keep the English name or transliterate (e.g., 瓦尔布罗德). Do NOT translate literally as 'Wall broken'.\n\n"

    "**V. ACTION VERBS**\n"
    "- 'Sacrifice' -> 弃子\n"
    "- 'Exchange' -> 交换 (The Exchange -> 得半子)\n"
    "- 'Fork' -> 捉双 | 'Pin' -> 牵制 | 'Skewer' -> 串击\n"
    "- 'Develop' -> 出子 | 'Fianchetto' -> 堡垒象/侧翼出象\n"
    "- 'Blunder' -> 恶手/大漏着 | 'Gambit' -> 弃兵\n\n"

    "**VI. NOTATION RULE**\n"
    "- Keep algebraic moves (e.g., 'e4', 'Nf3', 'O-O', 'Bxc5') EXACTLY as is.\n"
    "- If the source is spoken text (e.g., 'Knight to f3'), translate to Chinese term + coord (e.g., '马跳f3' or '马f3').\n"
    "</Chess Instruction Standards>\n"
)

## ================================================================
# @ step4_splitbymeaning.py
def get_split_prompt(sentence, num_parts=2, word_limit=20):
    language = load_key("whisper.detected_language")
    
    # 修复：
    # 1. 移除了 [br] 的要求，改为 List output。
    # 2. 保留了原本的 Critical Rules 细节。
    split_prompt = (
        f"## Role\n"
        f"You are a professional subtitle splitter for Chess Videos in **{language}**.\n\n"

        f"## Task\n"
        f"Split the text into a **list of {num_parts} parts** (max {word_limit} words each).\n\n"

        f"## Critical Rules\n"
        f"1. **Chess Notation Protection**: NEVER split algebraic notations (e.g., '1. e4', 'Nf3', 'Bxc5'). \n"
        f"   - 'Bxc5' cannot be split.\n"
        f"   - Keep move number with the move: '1. e4' stays together.\n"
        f"2. **Output Format**: Return a direct List of Strings. Do NOT use tags like [br].\n"
        f"3. Balance length and meaning.\n\n"

        f"## Given Text\n"
        f"<split_this_sentence>\n"
        f"{sentence}\n"
        f"</split_this_sentence>\n\n"

        f"## Output Format\n"
        f"```json\n"
        f"{{\n"
        f"    \"analysis\": \"Check for chess notations to protect\",\n"
        f"    \"split\": [\n"
        f"        \"Split Part 1 string...\",\n"
        f"        \"Split Part 2 string...\"\n"
        f"    ]\n"
        f"}}\n"
        f"```\n"
        f"Note: Start you answer with ```json and end with ```, do not add any other text."
    )
    return split_prompt

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
    
    # 保持原版 summary prompt 的所有细节
    summary_prompt = (
        f"## Role\n"
        f"You are a Chess Terminology Analyst.\n\n"

        f"## Task\n"
        f"1. Summarize the video content in two sentences.\n"
        f"2. **Conservative Term Extraction**:\n"
        f"   - Extract **Opening Names** ONLY if clearly audible (e.g., 'Sicilian Defense').\n"
        f"   - Extract **Named Tactics** (e.g., 'Windmill', 'Smothered Mate').\n"
        f"   - **CRITICAL**: Do NOT extract common moves (e.g., 'e4', 'Nf3') or generic words (e.g., 'Attack', 'Defense') as terms.\n"
        f"   - **CRITICAL**: If Whisper output is messy/gibberish, IGNORE it. Do not guess terms.\n"
        f"{terms_note}\n\n"
        f"{CHESS_INSTRUCTION}\n\n"

        f"## INPUT\n"
        f"<text>\n"
        f"{source_content}\n"
        f"</text>\n\n"

        f"## Output Format\n"
        f"```json\n"
        f"{{\n"
        f"  \"theme\": \"Two-sentence summary\",\n"
        f"  \"terms\": [\n"
        f"    {{\n"
        f"      \"src\": \"Source term\",\n"
        f"      \"tgt\": \"Target translation\", \n"
        f"      \"note\": \"Brief explanation\"\n"
        f"    }}\n"
        f"  ]\n"
        f"}}\n"
        f"```\n"
        f"Note: Start you answer with ```json and end with ```, do not add any other text."
    )
    return summary_prompt

## ================================================================
# @ step5_translate.py & translate_lines.py
def generate_shared_prompt(previous_content_prompt, after_content_prompt, summary_prompt, things_to_note_prompt):
    return (
        f"### Context Information\n"
        f"<previous_content>\n{previous_content_prompt}\n</previous_content>\n"
        f"**INSTRUCTION**: Use the context to track board state and disambiguate terms (e.g., Is 'Rank' a line or a standing?).\n\n"
        f"<subsequent_content>\n{after_content_prompt}\n</subsequent_content>\n\n"
        f"### Content Summary & Terminology\n{summary_prompt}\n\n"
        f"### Points to Note\n{things_to_note_prompt}"
    )

def get_prompt_faithfulness(lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    
    # 修复：分离数据与模板
    line_splits = lines.split('\n')
    input_json = {}
    for i, line in enumerate(line_splits, 1):
        input_json[f"{i}"] = {"origin": line}
    input_dump = json.dumps(input_json, indent=2, ensure_ascii=False)

    prompt_faithfulness = (
        f"## Role\n"
        f"You are an expert **Chess Translator**.\n"
        f"Your expertise lies in accurately understanding International Chess terminology and converting it faithfully to {TARGET_LANGUAGE}.\n\n"

        f"## Task\n"
        f"1. Translate line by line.\n"
        f"2. **Context Check**: Use the provided context to resolve pronouns (He vs It) and ambiguous terms (Rank/File).\n\n"
        f"{shared_prompt}\n\n"
        f"{CHESS_INSTRUCTION}\n\n"

        f"## INPUT DATA\n"
        f"The following is the source text to translate:\n"
        f"```json\n"
        f"{input_dump}\n"
        f"```\n\n"

        f"## Output Format\n"
        f"Return a JSON object with the 'direct' (Literal Translation) field added.\n"
        f"```json\n"
        f"{{\n"
        f"  \"1\": {{\n"
        f"    \"origin\": \"source text...\",\n"
        f"    \"direct\": \"literal translation...\"\n"
        f"  }}\n"
        f"}}\n"
        f"```\n"
        f"Note: Start you answer with ```json and end with ```, do not add any other text."
    )
    return prompt_faithfulness


def get_prompt_expressiveness(faithfulness_result, lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    
    # 输入数据：之前的直译结果
    input_data = json.dumps(faithfulness_result, indent=2, ensure_ascii=False)

    prompt_expressiveness = (
        f"## Role\n"
        f"You are an expert **Chess Translator**.\n"
        f"You are translating a video for Chinese chess players.\n\n"

        f"## Goal\n"
        f"Produce the final, polished subtitle line.\n\n"

        f"## The Process (Strict Execution)\n"
        f"For each line, perform two steps:\n\n"

        f"### Step 1: Reflect (Internal Analysis)\n"
        f"In the 'reflect' field, you MUST act as a chess critic. Analyze:\n"
        f"1. **Ambiguity**: 'Rank' (Row vs Standing)? 'Mate' (Friend vs Checkmate)?\n"
        f"2. **Logic Check**: Does the literal translation make sense on a chess board? (e.g., 'White broke the wall' -> Likely 'Walbrodt Gambit').\n"
        f"3. **Tone**: Is this a casual chat or a formal lecture?\n"
        f"4. **Conclusion**: How should I paraphrase this to sound like a native Chinese chess coach?\n\n"

        f"### Step 2: Free (Final Output)\n"
        f"In the 'free' field, output **ONLY THE TRANSLATED TEXT**.\n"
        f"- ❌ DO NOT explain your style (e.g., do NOT write 'Concise style...').\n"
        f"- ❌ DO NOT use descriptions.\n"
        f"- ✅ JUST write the Chinese sentence.\n\n"

        f"{shared_prompt}\n\n"
        f"{CHESS_INSTRUCTION}\n\n"

        f"## INPUT DATA\n"
        f"```json\n"
        f"{input_data}\n"
        f"```\n\n"

        f"## Output Format\n"
        f"Return the JSON with 'reflect' and 'free' fields added.\n"
        f"```json\n"
        f"{{\n"
        f"  \"1\": {{\n"
        f"    \"origin\": \"He missed a mate in two.\",\n"
        f"    \"direct\": \"他错过了一个配偶在两个里。\",\n"
        f"    \"reflect\": \"'Mate' here means Checkmate. 'In two' means inside two moves. Tone: Regretful/Critical.\",\n"
        f"    \"free\": \"他错过了两步杀。\"\n" # <--- 关键修改：这里给了一个真实的翻译例子
        f"  }}\n"
        f"}}\n"
        f"```\n"
        f"Note: Start you answer with ```json and end with ```, do not add any other text."
    )
    return prompt_expressiveness

## ================================================================
# @ step6_splitforsub.py
def get_align_prompt(src_sub, tr_sub, src_part):
    targ_lang = load_key("target_language")
    src_lang = load_key("whisper.detected_language")
    
    src_splits = src_part.split('\n')
    # 修复：不再预填充数据，只生成 Schema 结构
    example_list = []
    for i in range(len(src_splits)):
        example_list.append(f'{{"src_part_{i+1}": "Source text...", "target_part_{i+1}": "Aligned target text..."}}')
    example_json = ",\n        ".join(example_list)
    
    src_part_display = src_part.replace('\n', ' [br] ')

    align_prompt = (
        f"## Role\n"
        f"You are a Netflix subtitle alignment expert.\n\n"

        f"## Task\n"
        f"Align and split the {targ_lang} subtitles to match the structure of the {src_lang} source.\n\n"

        f"## Rules\n"
        f"1. **Chess Notation Protection**: NEVER split algebraic notations (e.g., \"1. e4\", \"Nf3\") across two lines. They must stay intact.\n"
        f"2. Analyze word order differences between languages.\n"
        f"3. Ensure the meaning matches the time segments.\n\n"

        f"## INPUT DATA\n"
        f"<subtitles>\n"
        f"{src_lang} Original: \"{src_sub}\"\n"
        f"{targ_lang} Original: \"{tr_sub}\"\n"
        f"Pre-processed {src_lang} Subtitles ([br] indicates split points): {src_part_display}\n"
        f"</subtitles>\n\n"

        f"## Output Format\n"
        f"```json\n"
        f"{{\n"
        f"    \"analysis\": \"Brief analysis of alignment strategy\",\n"
        f"    \"align\": [\n"
        f"        {example_json}\n"
        f"    ]\n"
        f"}}\n"
        f"```\n"
        f"Note: Start you answer with ```json and end with ```, do not add any other text."
    )
    return align_prompt

## ================================================================
# @ step8_gen_audio_task.py @ step10_gen_audio.py
def get_subtitle_trim_prompt(text, duration):
    rule = (
        "Consider:\n"
        "    a. Reducing filler words.\n"
        "    b. Omitting unnecessary pronouns."
    )

    trim_prompt = (
        f"## Role\n"
        f"You are a professional subtitle editor.\n\n"
        f"## INPUT\n"
        f"<subtitles>\n"
        f"Subtitle: \"{text}\"\n"
        f"Duration: {duration} seconds\n"
        f"</subtitles>\n\n"
        f"## Processing Rules\n"
        f"{rule}\n"
        f"- **CRITICAL for Chess**: \n"
        f"  - DO NOT shorten algebraic notations (e.g., \"Nf3\", \"O-O\"). \n"
        f"  - DO NOT remove \"Checkmate\" or \"Check\".\n"
        f"  - You MAY shorten descriptive text (e.g., \"He moves the Knight\" -> \"He moves Knight\").\n\n"

        f"## Output Format\n"
        f"```json\n"
        f"{{\n"
        f"    \"analysis\": \"Brief analysis of length and content type (Chess or General)\",\n"
        f"    \"result\": \"Optimized subtitle\"\n"
        f"}}\n"
        f"```\n"
        f"Note: Start you answer with ```json and end with ```, do not add any other text."
    )
    return trim_prompt

## ================================================================
# @ tts_main
def get_correct_text_prompt(text):
    prompt = (
        f"## Role\n"
        f"You are a text cleaning expert for TTS.\n\n"
        f"## Task\n"
        f"1. Keep basic punctuation (.,?!).\n"
        f"2. **Chess Check**: If the text contains moves like \"e4\" or \"Nf3\", KEEP THEM EXACTLY AS IS. Do not expand them.\n"
        f"3. Convert non-standard symbols to readable text if necessary, but touch nothing else.\n\n"
        f"## INPUT\n"
        f"{text}\n\n"
        f"## Output Format\n"
        f"```json\n"
        f"{{\n"
        f"    \"text\": \"cleaned text here\"\n"
        f"}}\n"
        f"```\n"
        f"Note: Start you answer with ```json and end with ```, do not add any other text."
    )
    return prompt