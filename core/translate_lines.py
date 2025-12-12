import json
import time
from rich.console import Console
# 1. 正确导入 Prompt 接口
from core.prompts import get_batch_translation_prompt
# 2. 动态导入 LLM 调用函数
try:
    from core.ask_gpt import ask_gpt
except ImportError:
    from core.utils.ask_gpt import ask_gpt

console = Console()

def translate_batch_lines(lines, context_before, context_after, chunk_index=0):
    """
    对一组字幕行进行 Batch 翻译 (Version C + 自动降级)
    """
    # ==========================
    # 策略 1: 尝试批量翻译 (Batch Mode)
    # ==========================
    prompt = get_batch_translation_prompt(lines, context_before, context_after)
    
    # 定义验证函数：检查行数是否一致
    def valid_length(response_data):
        if 'translation' not in response_data:
            return {"status": "error", "message": "Missing 'translation' key"}
        if not isinstance(response_data['translation'], list):
            return {"status": "error", "message": "'translation' must be a list"}
        if len(response_data['translation']) != len(lines):
            return {
                "status": "error", 
                "message": f"Length mismatch: Input {len(lines)} vs Output {len(response_data['translation'])}"
            }
        return {"status": "success", "message": "Valid"}

    try:
        # 调用 LLM，尝试 2 次 (减少重试次数，避免触发 Rate Limit)
        # 如果 Batch 失败，尽快降级到串行，不要死磕
        response = ask_gpt(
            prompt, 
            resp_type='json', 
            valid_def=valid_length, 
            log_title=f'batch_trans_{chunk_index}'
        )
        return response['translation']

    except Exception as e:
        # 如果 Batch 模式彻底失败（通常是因为模型非要合并行），进入降级模式
        console.print(f"[bold red]❌ Chunk {chunk_index} Batch failed: {e}[/bold red]")
        console.print(f"[yellow]🔄 Falling back to Serial Translation (Line-by-Line) for Chunk {chunk_index}...[/yellow]")

    # ==========================
    # 策略 2: 降级为逐行翻译 (Serial Fallback)
    # ==========================
    # 既然批量对齐失败，我们就一行一行翻，虽然慢，但绝对稳。
    
    fallback_result = []
    
    for i, line in enumerate(lines):
        # 构造这一行的专属上下文
        # 上文 = 原始上文 + 本 Batch 中已经在这一行之前的行
        current_context_before = context_before + lines[:i]
        # 下文 = 本 Batch 中这一行之后的行 + 原始下文
        current_context_after = lines[i+1:] + context_after
        
        # 构造一个只有 1 行的 Batch Prompt (这就变成了单行翻译)
        single_prompt = get_batch_translation_prompt([line], current_context_before, current_context_after)
        
        try:
            # 这里的 valid_def 依然检查长度（必须是1）
            single_resp = ask_gpt(
                single_prompt,
                resp_type='json',
                valid_def=lambda r: {"status": "success", "message": ""} if len(r.get('translation', [])) == 1 else {"status": "error", "message": "1:1 check failed"},
                log_title=f'serial_{chunk_index}_{i}'
            )
            fallback_result.extend(single_resp['translation'])
        except Exception as e_single:
            console.print(f"[red]❌ Line {i} failed in serial mode: {e_single}. Using source text.[/red]")
            # 最后的最后，如果单行也翻不出来（极罕见），才用原文兜底
            fallback_result.append(line)
            
    return fallback_result