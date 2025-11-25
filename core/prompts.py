import json
from core.utils import *

# ==============================================================================
# [Chess Logic] Domain Knowledge Base
# ==============================================================================
CHESS_INSTRUCTION = """
<Domain Specific Rule>
**CRITICAL INSTRUCTION**: Check if the text content is about **International Chess**. 
If (and ONLY if) it is about Chess, you MUST strictly follow these terminology rules:

1. **Piece Mapping (Standard Chinese)**:
   - King = 王 (not 国王)
   - Queen = 后 (not 王后)
   - Rook = 车 (not 城堡)
   - Bishop = 象 (not 主教)
   - Knight = 马 (not 骑士)
   - Pawn = 兵 (not 卒/典当)
   - Piece = 棋子/子力 (not 碎片/块)

2. **Opening Names (Standard Translation Table)**:
   - "Sicilian" -> 西西里防御
   - "Ruy Lopez" / "Spanish" -> 西班牙开局
   - "Italian Game" -> 意大利开局
   - "Caro-Kann" -> 卡罗康防御
   - "French Defense" -> 法兰西防御
   - "Scandinavian" -> 斯堪的纳维亚防御
   - "Pirc Defense" -> 皮尔茨防御
   - "Alekhine" -> 阿廖欣防御
   - "King's Indian" -> 古印度防御
   - "Queen's Indian" -> 新印度防御
   - "Nimzo-Indian" -> 尼姆佐维奇防御
   - "Grunfeld" -> 格林菲尔德防御
   - "Benoni" -> 别诺尼防御
   - "Dutch Defense" -> 荷兰防御
   - "English Opening" -> 英国式开局
   - "Reti Opening" -> 列蒂开局
   - "Catalan" -> 卡塔兰开局
   - "London System" -> 伦敦体系
   - "Smith-Morra" -> 史密斯-莫拉弃兵
   - "Wilkes-Barre" -> 威尔克斯-巴雷弃兵
   - "Evans Gambit" -> 伊文斯弃兵
   - "Scotch Game" -> 苏格兰开局
   - "Philidor" -> 菲利道尔防御
   - "Petrov" / "Russian" -> 俄罗斯防御

3. **General Terminology**:
   - "Gambit" -> 弃兵
   - "Variation" -> 变例
   - "Line" -> 线路/变化
   - "Mate" / "Checkmate" -> 将死
   - "Check" -> 将军
   - "Castling" -> 王车易位
   - "Development" -> 出子
   - "Sacrifice" -> 弃子
   - "Exchange" -> 交换
   - "Advantage" -> 优势
   - "Blunder" -> 大漏着/败着

4. **Notation Rule**:
   - KEEP algebraic notation (e.g., "e4", "Nf3", "Bxc5", "O-O", "h3") **EXACTLY AS IS**. 
   - Do NOT translate or expand them.
   - "White" = 白方, "Black" = 黑方.

5. **Anti-Hallucination Protocol (Strict Enforcement)**:
   - **Unknown Terms**: If you encounter an opening name or proper noun NOT listed above, you MUST **Transliterate it phonetically** (音译). 
   - **Universal Ban on Substitution**: Do **NOT** replace unknown terms with **ANY** other existing Chess Opening names. 
     - (e.g. Do NOT swap an unknown word with "Queen's Gambit", "King's Gambit", "Slav Defense", or ANY other famous term just to make the sentence sound smooth).
   - **Accuracy Priority**: It is strictly forbidden to fabricate a chess term. If you don't know it, spell it out by sound (e.g., "Wall-broke" -> "瓦尔布罗克").
</Domain Specific Rule>
"""

## ================================================================
# @ step4_splitbymeaning.py
def get_split_prompt(sentence, num_parts = 2, word_limit = 20):
    language = load_key("whisper.detected_language")
    # 使用拼接方式避免 Markdown 渲染中断
    split_prompt = f"""
## Role
You are a professional Netflix subtitle splitter in **{language}**.

## Task
Split the given subtitle text into **{num_parts}** parts, each less than **{word_limit}** words.

1. Maintain sentence meaning coherence according to Netflix subtitle standards
2. MOST IMPORTANT: Keep parts roughly equal in length (minimum 3 words each)
3. Split at natural points like punctuation marks or conjunctions
4. If provided text is repeated words, simply split at the middle of the repeated words.
5. **CRITICAL**: Do NOT split inside specific technical notations (e.g., Chess moves like "1. e4", "Nf3"). Keep them distinct.

## Steps
1. Analyze the sentence structure, complexity, and key splitting challenges
2. Generate two alternative splitting approaches with [br] tags at split positions
3. Compare both approaches highlighting their strengths and weaknesses
4. Choose the best splitting approach

## Given Text
<split_this_sentence>
{sentence}
</split_this_sentence>

## Output in only JSON format and no other text
""" + """```json
{
    "analysis": "Brief description of sentence structure, complexity, and key splitting challenges",
    "split1": "First splitting approach with [br] tags at split positions",
    "split2": "Alternative splitting approach with [br] tags at split positions",
    "assess": "Comparison of both approaches highlighting their strengths and weaknesses",
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
    
    # add custom terms note
    terms_note = ""
    if custom_terms_json:
        terms_list = []
        for term in custom_terms_json['terms']:
            terms_list.append(f"- {term['src']}: {term['tgt']} ({term['note']})")
        terms_note = "\n### Existing Terms\nPlease exclude these terms in your extraction:\n" + "\n".join(terms_list)
    
    summary_prompt = f"""
## Role
You are a video translation expert and terminology consultant, specializing in {src_lang} comprehension and {tgt_lang} expression optimization.

## Task
For the provided {src_lang} video text:
1. Summarize main topic in two sentences
2. Extract professional terms/names with {tgt_lang} translations (excluding existing terms)
3. Provide brief explanation for each term

{terms_note}

{CHESS_INSTRUCTION}

Steps:
1. Topic Summary:
   - Quick scan for general understanding
   - Write two sentences: first for main topic, second for key point
2. Term Extraction:
   - Mark professional terms and names (excluding those listed in Existing Terms)
   - **IF Chess Content**: Extract Opening Names (e.g. Sicilian) and Tactics (e.g. Pin/Fork) as terms.
   - **IMPORTANT**: Do NOT extract standard moves (e.g. "e4", "Nf3") as terms.
   - Provide {tgt_lang} translation or keep original
   - Add brief explanation
   - Extract less than 15 terms

## INPUT
<text>
{source_content}
</text>

## Output in only JSON format and no other text
{{
  "theme": "Two-sentence video summary",
  "terms": [
    {{
      "src": "{src_lang} term",
      "tgt": "{tgt_lang} translation or original", 
      "note": "Brief explanation"
    }}
  ]
}}  

## Example
{{
  "theme": "本视频介绍国际象棋开局策略。重点讲解了针对1.e4的防御体系。",
  "terms": [
    {{
      "src": "Sicilian Defense",
      "tgt": "西西里防御",
      "note": "黑方应对1.e4最激烈的防御手段"
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

<subsequent_content>
{after_content_prompt}
</subsequent_content>

### Content Summary
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
    prompt_faithfulness = f'''
## Role
You are a professional Netflix subtitle translator, fluent in both {src_language} and {TARGET_LANGUAGE}, as well as their respective cultures. 
Your expertise lies in accurately understanding the semantics and structure of the original {src_language} text and faithfully translating it into {TARGET_LANGUAGE} while preserving the original meaning.

## Task
We have a segment of original {src_language} subtitles that need to be directly translated into {TARGET_LANGUAGE}. These subtitles come from a specific context and may contain specific themes and terminology.

1. Translate the original {src_language} subtitles into {TARGET_LANGUAGE} line by line
2. Ensure the translation is faithful to the original, accurately conveying the original meaning
3. Consider the context and professional terminology

{shared_prompt}

{CHESS_INSTRUCTION}

<translation_principles>
1. Faithful to the original: Accurately convey the content and meaning of the original text, without arbitrarily changing, adding, or omitting content.
2. Accurate terminology: Use professional terms correctly and maintain consistency in terminology. **If Chess content is detected, STRICTLY follow the Domain Specific Rule provided above.**
3. Understand the context: Fully comprehend and reflect the background and contextual relationships of the text.
</translation_principles>

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
    json_format = {
        key: {
            "origin": value["origin"],
            "direct": value["direct"],
            "reflect": "your reflection on direct translation",
            "free": "your free translation"
        }
        for key, value in faithfulness_result.items()
    }
    json_format = json.dumps(json_format, indent=2, ensure_ascii=False)

    src_language = load_key("whisper.detected_language")
    prompt_expressiveness = f'''
## Role
You are a professional Netflix subtitle translator and language consultant.
Your expertise lies not only in accurately understanding the original {src_language} but also in optimizing the {TARGET_LANGUAGE} translation to better suit the target language's expression habits and cultural background.

## Task
We already have a direct translation version of the original {src_language} subtitles.
Your task is to reflect on and improve these direct translations to create more natural and fluent {TARGET_LANGUAGE} subtitles.

1. Analyze the direct translation results line by line, pointing out existing issues
2. Provide detailed modification suggestions
3. Perform free translation based on your analysis
4. Do not add comments or explanations in the translation, as the subtitles are for the audience to read
5. Do not leave empty lines in the free translation, as the subtitles are for the audience to read

{shared_prompt}

{CHESS_INSTRUCTION}

<Translation Analysis Steps>
Please use a two-step thinking process to handle the text line by line:

1. Direct Translation Reflection:
   - Evaluate language fluency
   - Check if the language style is consistent with the original text
   - **Chess Check**: Ensure terms like "Knight" are "马" (not 骑士), and "Piece" is "棋子" (not 碎片/和平).
   - Check the conciseness of the subtitles.

2. {TARGET_LANGUAGE} Free Translation:
   - Aim for contextual smoothness and naturalness, conforming to {TARGET_LANGUAGE} expression habits
   - Ensure it's easy for {TARGET_LANGUAGE} audience to understand and accept
   - **Tone**: If Chess, keep it professional, concise, and instructional. Use "白方/黑方" instead of "白色/黑色".
</Translation Analysis Steps>
   
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
You are a Netflix subtitle alignment expert fluent in both {src_lang} and {targ_lang}.

## Task
We have {src_lang} and {targ_lang} original subtitles for a Netflix program, as well as a pre-processed split version of {src_lang} subtitles.
Your task is to create the best splitting scheme for the {targ_lang} subtitles based on this information.

1. Analyze the word order and structural correspondence between {src_lang} and {targ_lang} subtitles
2. Split the {targ_lang} subtitles according to the pre-processed {src_lang} split version
3. Never leave empty lines. If it's difficult to split based on meaning, you may appropriately rewrite the sentences that need to be aligned
4. Do not add comments or explanations in the translation, as the subtitles are for the audience to read
5. **Chess Notation Rule**: Never split a chess move notation (e.g. "1. e4") across two subtitle lines.

## INPUT
<subtitles>
{src_lang} Original: "{src_sub}"
{targ_lang} Original: "{tr_sub}"
Pre-processed {src_lang} Subtitles ([br] indicates split points): {src_part}
</subtitles>

## Output in only JSON format and no other text
''' + f'''```json
{{
    "analysis": "Brief analysis of word order, structure, and semantic correspondence between two subtitles",
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
 
    rule = '''Consider a. Reducing filler words without modifying meaningful content. b. Omitting unnecessary modifiers or pronouns, for example:
    - "Please explain your thought process" can be shortened to "Please explain thought process"
    - "We need to carefully analyze this complex problem" can be shortened to "We need to analyze this problem"
    - "Let's discuss the various different perspectives on this topic" can be shortened to "Let's discuss different perspectives on this topic"
    - "Can you describe in detail your experience from yesterday" can be shortened to "Can you describe yesterday's experience" '''

    trim_prompt = f'''
## Role
You are a professional subtitle editor, editing and optimizing lengthy subtitles that exceed voiceover time before handing them to voice actors. 
Your expertise lies in cleverly shortening subtitles slightly while ensuring the original meaning and structure remain unchanged.

## INPUT
<subtitles>
Subtitle: "{text}"
Duration: {duration} seconds
</subtitles>

## Processing Rules
{rule}
- **CRITICAL for Chess**: DO NOT shorten or modify algebraic notations (e.g., "Nf3", "O-O"). These are critical information.

## Processing Steps
Please follow these steps and provide the results in the JSON output:
1. Analysis: Briefly analyze the subtitle's structure, key information, and filler words that can be omitted.
2. Trimming: Based on the rules and analysis, optimize the subtitle by making it more concise according to the processing rules.

## Output in only JSON format and no other text
''' + '''```json
{
    "analysis": "Brief analysis of the subtitle, including structure, key information, and potential processing locations",
    "result": "Optimized and shortened subtitle in the original subtitle language"
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
You are a text cleaning expert for TTS (Text-to-Speech) systems.

## Task
Clean the given text by:
1. Keep only basic punctuation (.,?!)
2. Preserve the original meaning
3. **Chess Context**: If text contains chess moves (e.g. "e4"), keep them as is.

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