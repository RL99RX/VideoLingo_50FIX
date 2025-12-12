import pandas as pd
import os
import re
from rich.panel import Panel
from rich.console import Console
import autocorrect_py as autocorrect
from core.utils import *
from core.utils.models import *
from difflib import SequenceMatcher

console = Console()

SUBTITLE_OUTPUT_CONFIGS = [ 
    ('src.srt', ['Source']),
    ('trans.srt', ['Translation']),
    ('src_trans.srt', ['Source', 'Translation']),
    ('trans_src.srt', ['Translation', 'Source'])
]

AUDIO_SUBTITLE_OUTPUT_CONFIGS = [
    ('src_subs_for_audio.srt', ['Source']),
    ('trans_subs_for_audio.srt', ['Translation'])
]

def convert_to_srt_format(start_time, end_time):
    """Convert time (in seconds) to the format: hours:minutes:seconds,milliseconds"""
    def seconds_to_hmsm(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int(seconds * 1000) % 1000
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

    start_srt = seconds_to_hmsm(start_time)
    end_srt = seconds_to_hmsm(end_time)
    return f"{start_srt} --> {end_srt}"

def remove_punctuation(text):
    # 强化清洗逻辑，统一处理为字符串，移除标点
    text = re.sub(r'\s+', ' ', str(text))
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def find_best_match(query, text, start_pos, search_window=2500, threshold=0.6):
    """在指定窗口内寻找最佳模糊匹配"""
    search_limit = min(len(text), start_pos + search_window)
    window_text = text[start_pos:search_limit]
    
    if not query or not window_text:
        return None

    # 1. 尝试直接匹配（最高效）
    exact_idx = window_text.find(query)
    if exact_idx != -1:
        return (start_pos + exact_idx, start_pos + exact_idx + len(query))

    # 2. 模糊匹配
    matcher = SequenceMatcher(None, query, window_text)
    match = matcher.find_longest_match(0, len(query), 0, len(window_text))
    
    # 只有当匹配长度占原句一定比例时才认为有效
    if match.size / len(query) > threshold:
        abs_start = start_pos + match.b
        abs_end = abs_start + match.size
        return (abs_start, abs_end)
    
    return None

def get_sentence_timestamps(df_words, df_sentences):
    time_stamp_list = []
    
    # 构建全文字符串和位置索引映射
    full_words_str = ''
    position_to_word_idx = {}
    
    for idx, word in enumerate(df_words['text']):
        clean_word = remove_punctuation(word.lower())
        start_pos = len(full_words_str)
        full_words_str += clean_word
        for pos in range(start_pos, len(full_words_str)):
            position_to_word_idx[pos] = idx
            
    current_pos = 0
    last_end_time = 0.0
    
    sentences = df_sentences['Source'].tolist()
    total_sentences = len(sentences)
    i = 0
    
    while i < total_sentences:
        sentence = sentences[i]
        clean_sentence = remove_punctuation(sentence.lower()).replace(" ", "")
        
        # 如果句子为空，直接给一个极短的时间
        if not clean_sentence:
            time_stamp_list.append((last_end_time, last_end_time + 0.1))
            last_end_time += 0.1
            i += 1
            continue

        # === 策略1: 尝试当前句子的匹配 ===
        match_span = find_best_match(clean_sentence, full_words_str, current_pos)
        
        if match_span:
            # 找到匹配，提取时间
            start_idx = match_span[0]
            end_idx = match_span[1] - 1 # inclusive
            
            # 安全检查：防止索引越界
            if start_idx in position_to_word_idx and end_idx in position_to_word_idx:
                start_word_idx = position_to_word_idx[start_idx]
                end_word_idx = position_to_word_idx[end_idx]
                
                start_t = float(df_words['start'][start_word_idx])
                end_t = float(df_words['end'][end_word_idx])
                
                # 修正：开始时间不能早于上一句结束时间
                if start_t < last_end_time:
                    start_t = last_end_time
                if end_t < start_t:
                    end_t = start_t + 0.1

                time_stamp_list.append((start_t, end_t))
                last_end_time = end_t
                current_pos = match_span[1]
                i += 1
                continue

        # === 策略2: 匹配失败，启用前瞻 (Smart Lookahead) ===
        # 既然当前句子找不到，我们看看下一句能不能找到
        console.print(f"[yellow]⚠️ Match failed for: '{sentence[:20]}...', looking ahead...[/yellow]")
        
        next_match_span = None
        lookahead_idx = i + 1
        
        # 向后看1句（如果需要更强鲁棒性可以循环向后看，但1句通常足够）
        if lookahead_idx < total_sentences:
            next_sent = sentences[lookahead_idx]
            clean_next = remove_punctuation(next_sent.lower()).replace(" ", "")
            if clean_next:
                # 在更远的窗口寻找下一句
                next_match_span = find_best_match(clean_next, full_words_str, current_pos, search_window=3000)
        
        if next_match_span:
            # === 策略2.1: 下一句找到了 ===
            # 下一句的开始位置
            next_start_idx = next_match_span[0]
            if next_start_idx in position_to_word_idx:
                next_start_t = float(df_words['start'][position_to_word_idx[next_start_idx]])
            else:
                next_start_t = last_end_time + 2.0
            
            # 当前丢失的句子，就填补在 [last_end_time, next_start_t] 之间
            # 至少保留0.5秒给它，避免时间倒流
            if next_start_t <= last_end_time:
                next_start_t = last_end_time + 1.0
                
            console.print(f"[green]✅ Recovered using lookahead. Assigning interval {last_end_time:.2f}-{next_start_t:.2f}[/green]")
            time_stamp_list.append((last_end_time, next_start_t))
            last_end_time = next_start_t
            
            # 注意：这里我们不移动 current_pos，也不增加 i
            # 因为下一轮循环处理 i+1 时，会再次找到这个 next_match_span 并正常处理
            # 这里的目的是给当前“丢失”的句子 i 分配时间
            
            # 修正：为了避免下一轮重复搜索带来的开销，其实可以直接在这里跳过吗？
            # 不，保持 current_pos 不变，下一轮 i+1 自然会匹配到 next_match_span，逻辑更简单
            i += 1
            
        else:
            # === 策略3: 彻底失败 (当前和下一句都找不到) ===
            # 只能根据文本长度估算一个时间了
            estimated_duration = len(sentence) * 0.1 + 0.5 # 每个字0.1秒 + 0.5秒基础
            if estimated_duration > 5.0: estimated_duration = 5.0
            
            console.print(f"[red]❌ Completely lost match for: '{sentence[:15]}...'. Estimating {estimated_duration:.1f}s[/red]")
            
            start_t = last_end_time
            end_t = last_end_time + estimated_duration
            time_stamp_list.append((start_t, end_t))
            last_end_time = end_t
            # 这种情况下不移动 current_pos，希望后面能重新对齐
            i += 1

    return time_stamp_list

def align_timestamp(df_text, df_translate, subtitle_output_configs: list, output_dir: str, for_display: bool = True):
    """Align timestamps and add a new timestamp column to df_translate"""
    df_trans_time = df_translate.copy()

    # Assign an ID to each word in df_text['text'] and create a new DataFrame
    words = df_text['text'].str.split(expand=True).stack().reset_index(level=1, drop=True).reset_index()
    words.columns = ['id', 'word']
    words['id'] = words['id'].astype(int)

    # Process timestamps ⏰
    try:
        time_stamp_list = get_sentence_timestamps(df_text, df_translate)
    except Exception as e:
        console.print(f"[bold red]Critical Error in timestamp alignment: {str(e)}[/bold red]")
        # Fallback: Generate linear timestamps to prevent crash
        time_stamp_list = []
        curr = 0.0
        for _ in range(len(df_translate)):
            time_stamp_list.append((curr, curr+2.0))
            curr += 2.0
            
    df_trans_time['timestamp'] = time_stamp_list
    df_trans_time['duration'] = df_trans_time['timestamp'].apply(lambda x: x[1] - x[0])

    # Remove gaps 🕳️
    for i in range(len(df_trans_time)-1):
        if i+1 < len(df_trans_time):
            current_end = df_trans_time.loc[i, 'timestamp'][1]
            next_start = df_trans_time.loc[i+1, 'timestamp'][0]
            delta_time = next_start - current_end
            if 0 < delta_time < 1:
                df_trans_time.at[i, 'timestamp'] = (df_trans_time.loc[i, 'timestamp'][0], next_start)

    # Convert start and end timestamps to SRT format
    df_trans_time['timestamp'] = df_trans_time['timestamp'].apply(lambda x: convert_to_srt_format(x[0], x[1]))

    # Polish subtitles: replace punctuation in Translation if for_display
    if for_display:
        df_trans_time['Translation'] = df_trans_time['Translation'].apply(lambda x: re.sub(r'[，。]', ' ', str(x)).strip())

    # Output subtitles 📜
    def generate_subtitle_string(df, columns):
        return ''.join([f"{i+1}\n{row['timestamp']}\n{str(row[columns[0]]).strip()}\n{str(row[columns[1]]).strip() if len(columns) > 1 else ''}\n\n" for i, row in df.iterrows()]).strip()

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for filename, columns in subtitle_output_configs:
            subtitle_str = generate_subtitle_string(df_trans_time, columns)
            with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as f:
                f.write(subtitle_str)
    
    return df_trans_time

# ✨ Beautify the translation
def clean_translation(x):
    if pd.isna(x):
        return ''
    cleaned = str(x).strip('。').strip('，')
    return autocorrect.format(cleaned)

def align_timestamp_main():
    df_text = pd.read_excel(_2_CLEANED_CHUNKS)
    df_text['text'] = df_text['text'].str.strip('"').str.strip()
    df_translate = pd.read_excel(_5_SPLIT_SUB)
    df_translate['Translation'] = df_translate['Translation'].apply(clean_translation)
    
    align_timestamp(df_text, df_translate, SUBTITLE_OUTPUT_CONFIGS, _OUTPUT_DIR)
    console.print(Panel("[bold green]🎉📝 Subtitles generation completed! Please check in the `output` folder 👀[/bold green]"))

    # for audio
    df_translate_for_audio = pd.read_excel(_5_REMERGED) # use remerged file to avoid unmatched lines when dubbing
    df_translate_for_audio['Translation'] = df_translate_for_audio['Translation'].apply(clean_translation)
    
    align_timestamp(df_text, df_translate_for_audio, AUDIO_SUBTITLE_OUTPUT_CONFIGS, _AUDIO_DIR)
    console.print(Panel(f"[bold green]🎉📝 Audio subtitles generation completed! Please check in the `{_AUDIO_DIR}` folder 👀[/bold green]"))
    

if __name__ == '__main__':
    align_timestamp_main()