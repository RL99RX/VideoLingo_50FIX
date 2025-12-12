import pandas as pd
import concurrent.futures
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# 1. 导入核心翻译引擎
from core.translate_lines import translate_batch_lines
# 2. 导入必要的常量
from core.utils.models import _3_2_SPLIT_BY_MEANING, _4_2_TRANSLATION, _2_CLEANED_CHUNKS
# 3. 导入工具函数
from core.utils import load_key, check_file_exists
from core._8_1_audio_task import check_len_then_trim
from core._6_gen_sub import align_timestamp

# ==============================================================================
# 关键修复：导入配置文件 (路径常量)
# ==============================================================================
try:
    from core.config import *
except ImportError:
    pass

console = Console()

# ==============================================================================
# 1. 切分逻辑
# ==============================================================================
def split_chunks_by_chars(chunk_size, max_i): 
    """根据字符数限制将文本切分为 chunks"""
    with open(_3_2_SPLIT_BY_MEANING, "r", encoding="utf-8") as file:
        sentences = file.read().strip().split('\n')

    chunks = []
    chunk = ''
    sentence_count = 0
    for sentence in sentences:
        if len(chunk) + len(sentence + '\n') > chunk_size or sentence_count == max_i:
            if chunk:
                chunks.append(chunk.strip())
            chunk = sentence + '\n'
            sentence_count = 1
        else:
            chunk += sentence + '\n'
            sentence_count += 1
            
    if chunk:
        chunks.append(chunk.strip())
    return chunks

# ==============================================================================
# 2. Context Helper (上下文获取)
# ==============================================================================
def get_context(chunks, index, offset, lines_count):
    target_idx = index + offset
    if 0 <= target_idx < len(chunks):
        chunk_lines = chunks[target_idx].strip().split('\n')
        if offset < 0: return chunk_lines[-lines_count:] # 上文
        else: return chunk_lines[:lines_count]           # 下文
    return []

# ==============================================================================
# 3. 任务包装器
# ==============================================================================
def process_chunk(chunk, chunks, i):
    lines = chunk.strip().split('\n')
    # 获取上下文：前一块的最后3行，后一块的前2行
    context_before = get_context(chunks, i, -1, 3)
    context_after = get_context(chunks, i, 1, 2)
    
    # 调用核心引擎
    trans_lines = translate_batch_lines(lines, context_before, context_after, chunk_index=i)
    
    return i, lines, trans_lines

# ==============================================================================
# 4. 主流程
# ==============================================================================
@check_file_exists(_4_2_TRANSLATION)
def translate_all():
    console.print("[bold green]🚀 Start Batch Translation (Version C Engine)...[/bold green]")
    
    # 1. 切分任务
    chunks = split_chunks_by_chars(chunk_size=600, max_i=10)
    
    # 2. 并发执行
    results = []
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task("[cyan]Translating...", total=len(chunks))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=load_key("max_workers")) as executor:
            futures = [executor.submit(process_chunk, chunk, chunks, i) for i, chunk in enumerate(chunks)]
            
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
                progress.update(task, advance=1)

    # 3. 结果重组
    results.sort(key=lambda x: x[0])
    
    all_src = []
    all_trans = []
    for _, src, trans in results:
        all_src.extend(src)
        all_trans.extend(trans)
        
    # 4. 数据保存 (Excel & SRT)
    # 读取原始 Whisper 切片用于时间轴对齐
    df_text = pd.read_excel(_2_CLEANED_CHUNKS)
    df_text['text'] = df_text['text'].str.strip('"').str.strip()
    
    # --- 关键修复开始 ---
    # 不要强行对齐 df_text 的长度！因为我们做过句子分割，行数变多是正常的。
    # 只需确保 Source 和 Translation 一一对应即可。
    
    if len(all_src) != len(all_trans):
        console.print(f"[bold red]❌ Critical Error: Source lines ({len(all_src)}) != Translation lines ({len(all_trans)})[/bold red]")
        # 兜底：截断到最短长度，防止保存失败
        min_len = min(len(all_src), len(all_trans))
        all_src = all_src[:min_len]
        all_trans = all_trans[:min_len]

    df_translate = pd.DataFrame({'Source': all_src, 'Translation': all_trans})
    # --- 关键修复结束 ---
    
    # 生成带时间轴的 Excel
    # align_timestamp 会通过文本模糊匹配，将 df_translate(无时间) 映射到 df_text(有时间) 上
    subtitle_configs = [('trans_subs_for_audio.srt', ['Translation'])]
    df_time = align_timestamp(df_text, df_translate, subtitle_configs, output_dir=None, for_display=False)
    
    # 长度修剪 (Trim)
    min_dur = load_key("min_trim_duration")
    df_time['Translation'] = df_time.apply(
        lambda x: check_len_then_trim(x['Translation'], x['duration']) if x['duration'] > min_dur else x['Translation'], 
        axis=1
    )
    
    console.print(df_time)
    df_time.to_excel(_4_2_TRANSLATION, index=False)
    console.print("[bold green]✅ Translation Pipeline Completed![/bold green]")

if __name__ == '__main__':
    translate_all()