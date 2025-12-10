import concurrent.futures
import math
import json
from rich.console import Console
from rich.table import Table
from core.prompts import get_split_prompt
from core.spacy_utils.load_nlp_model import init_nlp
from core.utils import *
from core.utils.models import _3_1_SPLIT_BY_NLP, _3_2_SPLIT_BY_MEANING

console = Console()

def tokenize_sentence(sentence, nlp):
    doc = nlp(sentence)
    return [token.text for token in doc]

def split_sentence(sentence, num_parts, word_limit=20, index=-1, retry_attempt=0):
    """
    Split a long sentence using GPT and return the result as a string joined by newline.
    Now optimized to expect a JSON list directly from LLM.
    """
    split_prompt = get_split_prompt(sentence, num_parts, word_limit)
    
    def valid_split(response_data):
        if "split" not in response_data:
            return {"status": "error", "message": "Missing required key: `split`"}
        if not isinstance(response_data["split"], list):
            return {"status": "error", "message": "Key `split` must be a list"}
        if len(response_data["split"]) < 2:
             # 如果模型认为不需要切分，返回列表长度为1，这其实不算错误，但我们需要确认行为
             # 这里我们允许，后续逻辑会处理
             return {"status": "success", "message": "Split list valid"}
        return {"status": "success", "message": "Split completed"}
    
    # 调用 LLM
    response_data = ask_gpt(
        split_prompt + " " * retry_attempt, 
        resp_type='json', 
        valid_def=valid_split, 
        log_title='split_by_meaning'
    )
    
    # 直接获取分割好的列表
    split_parts = response_data["split"]
    
    # 简单的拼接逻辑：用换行符连接
    best_split = '\n'.join(split_parts)
    
    # 验证完整性（可选警告）：检查切分后的文本长度是否和原句差异过大（防止漏词）
    # 这里只做简单的控制台提示，不阻断流程
    cleaned_original = sentence.replace(" ", "")
    cleaned_split = best_split.replace("\n", "").replace(" ", "")
    # 注意：LLM有时会微调标点，所以这里不强制报错，只在差异巨大时警告
    if abs(len(cleaned_original) - len(cleaned_split)) > 10:
        console.print(f"[yellow]Warning: Split length mismatch for sentence {index}[/yellow]")

    if index != -1:
        console.print(f'[green]✅ Sentence {index} has been successfully split[/green]')
    
    # 打印表格展示结果
    table = Table(title="")
    table.add_column("Type", style="cyan")
    table.add_column("Sentence")
    table.add_row("Original", sentence, style="yellow")
    table.add_row("Split", best_split.replace('\n', ' || '), style="yellow")
    console.print(table)
    
    return best_split

def parallel_split_sentences(sentences, max_length, max_workers, nlp, retry_attempt=0):
    """Split sentences in parallel using a thread pool."""
    new_sentences = [None] * len(sentences)
    futures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, sentence in enumerate(sentences):
            # Use tokenizer to split the sentence
            tokens = tokenize_sentence(sentence, nlp)
            
            # Decide if splitting is needed
            if len(tokens) > max_length:
                num_parts = math.ceil(len(tokens) / max_length)
                future = executor.submit(split_sentence, sentence, num_parts, max_length, index=index, retry_attempt=retry_attempt)
                futures.append((future, index, num_parts, sentence))
            else:
                new_sentences[index] = [sentence]

        for future, index, num_parts, sentence in futures:
            try:
                split_result = future.result()
                if split_result:
                    split_lines = split_result.strip().split('\n')
                    new_sentences[index] = [line.strip() for line in split_lines]
                else:
                    new_sentences[index] = [sentence]
            except Exception as e:
                console.print(f"[red]Error processing sentence {index}: {e}[/red]")
                new_sentences[index] = [sentence]

    # Flatten the list
    return [sentence for sublist in new_sentences for sentence in sublist]

@check_file_exists(_3_2_SPLIT_BY_MEANING)
def split_sentences_by_meaning():
    """The main function to split sentences by meaning."""
    # read input sentences
    with open(_3_1_SPLIT_BY_NLP, 'r', encoding='utf-8') as f:
        sentences = [line.strip() for line in f.readlines()]

    nlp = init_nlp()
    # 🔄 process sentences multiple times to ensure all are split
    for retry_attempt in range(3):
        sentences = parallel_split_sentences(
            sentences, 
            max_length=load_key("max_split_length"), 
            max_workers=load_key("max_workers"), 
            nlp=nlp, 
            retry_attempt=retry_attempt
        )

    # 💾 save results
    with open(_3_2_SPLIT_BY_MEANING, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sentences))
    console.print('[green]✅ All sentences have been successfully split![/green]')

if __name__ == '__main__':
    # test case
    # print(split_sentence('Which makes no sense to the... average guy who always pushes the character creation slider all the way to the right.', 2, 22))
    split_sentences_by_meaning()