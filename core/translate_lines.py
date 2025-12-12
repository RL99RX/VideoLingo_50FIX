from core.prompts import generate_shared_prompt, get_prompt_faithfulness, get_prompt_expressiveness
from rich.panel import Panel
from rich.console import Console
from rich.table import Table
from rich import box
from core.utils import *

console = Console()

def valid_translate_result(result: dict, required_keys: list, required_sub_keys: list):
    # 基础格式检查
    if not all(key in result for key in required_keys):
        return {"status": "error", "message": f"Missing keys: {', '.join(set(required_keys) - set(result.keys()))}"}
    for key in result:
        if not all(sub_key in result[key] for sub_key in required_sub_keys):
            return {"status": "error", "message": f"Missing sub-keys in {key}: {', '.join(set(required_sub_keys) - set(result[key].keys()))}"}
    return {"status": "success", "message": "Translation completed"}

def translate_lines(lines, previous_content_prompt, after_cotent_prompt, things_to_note_prompt, summary_prompt, index=0):
    shared_prompt = generate_shared_prompt(previous_content_prompt, after_cotent_prompt, summary_prompt, things_to_note_prompt)
    
    # 关键：使用 strip() 确保行数统计准确
    source_lines = lines.strip().split('\n')
    line_count = len(source_lines)

    def retry_translation(prompt, length, step_name):
        
        # 内部函数：包含重复检测逻辑
        def valid_faith(response_data):
            # 1. 检查 Key 是否齐全
            check = valid_translate_result(response_data, [str(i) for i in range(1, length+1)], ['direct'])
            if check['status'] == 'error': return check
            
            # 2. 🛡️ 幻觉检测：检查相邻行是否异常重复
            # 如果 原文不同(source_lines)，但 译文完全一样(direct)，判定为幻觉
            for i in range(1, length):
                curr_trans = response_data[str(i)]['direct'].strip()
                next_trans = response_data[str(i+1)]['direct'].strip()
                
                # 只有当译文长度足够长时才检查，避免简短的 "是"、"对" 被误杀
                if len(curr_trans) > 5 and curr_trans == next_trans:
                    curr_src = source_lines[i-1].strip()
                    next_src = source_lines[i].strip()
                    # 原文不同，译文却一样 -> 报错重试
                    if curr_src != next_src:
                        return {
                            "status": "error", 
                            "message": f"🚫 Hallucination detected: Line {i} & {i+1} are identical in translation but different in source."
                        }
            return {"status": "success", "message": "Pass"}

        def valid_express(response_data):
            check = valid_translate_result(response_data, [str(i) for i in range(1, length+1)], ['free'])
            if check['status'] == 'error': return check
            return {"status": "success", "message": "Pass"}

        for retry in range(3):
            if step_name == 'faithfulness':
                result = ask_gpt(prompt + retry * " ", resp_type='json', valid_def=valid_faith, log_title=f'translate_{step_name}')
            elif step_name == 'expressiveness':
                result = ask_gpt(prompt + retry * " ", resp_type='json', valid_def=valid_express, log_title=f'translate_{step_name}')
            
            if len(result) == length:
                return result
            
            if retry != 2:
                console.print(f'[yellow]⚠️ {step_name.capitalize()} block {index} retry...[/yellow]')
        
        raise ValueError(f'[red]❌ {step_name.capitalize()} failed after 3 retries.[/red]')

    ## Step 1: Faithful Translation
    prompt1 = get_prompt_faithfulness(lines, shared_prompt)
    faith_result = retry_translation(prompt1, line_count, 'faithfulness')

    # 关键修复：手动注入 Origin，防止 Key Error
    for key in faith_result:
        faith_result[key]["direct"] = faith_result[key]["direct"].replace('\n', ' ')
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(source_lines):
                faith_result[key]["origin"] = source_lines[idx]
            else:
                faith_result[key]["origin"] = ""

    reflect_translate = load_key('reflect_translate')
    if not reflect_translate:
        translate_result = "\n".join([faith_result[i]["direct"].strip() for i in faith_result])
        return translate_result, lines

    ## Step 2: Expressive Translation
    prompt2 = get_prompt_expressiveness(faith_result, lines, shared_prompt)
    express_result = retry_translation(prompt2, line_count, 'expressiveness')

    # 打印结果表
    table = Table(title="Translation Results", show_header=False, box=box.ROUNDED)
    table.add_column("Translations", style="bold")
    for i, key in enumerate(express_result):
        table.add_row(f"[cyan]Origin:  {faith_result[key].get('origin', '')}[/cyan]")
        table.add_row(f"[magenta]Direct:  {faith_result[key]['direct']}[/magenta]")
        table.add_row(f"[green]Free:    {express_result[key]['free']}[/green]")
        if i < len(express_result) - 1:
            table.add_row("[yellow]" + "-" * 50 + "[/yellow]")
    console.print(table)

    translate_result = "\n".join([express_result[i]["free"].replace('\n', ' ').strip() for i in express_result])
    return translate_result, lines