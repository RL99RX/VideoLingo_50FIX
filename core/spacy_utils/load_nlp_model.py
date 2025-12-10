import spacy
import os
import sys
from spacy.cli import download
from core.utils import rprint, load_key, except_handler

SPACY_MODEL_MAP = load_key("spacy_model_map")

def get_spacy_model(language: str):
    # 默认获取配置中的模型，如果未配置则回退到 en_core_web_lg
    model = SPACY_MODEL_MAP.get(language.lower(), "en_core_web_lg")
    if language not in SPACY_MODEL_MAP:
        rprint(f"[yellow]Spacy model does not support '{language}', using en_core_web_lg model as fallback...[/yellow]")
    return model

def install_spacy_model(model_name):
    """
    Robust installation strategy:
    1. Direct download
    2. Proxy download (127.0.0.1:7890)
    3. Proxy + No-cache download (Fixes 'invalid wheel' error)
    """
    rprint(f"[blue]⬇️ Attempting to install {model_name}...[/blue]")

    # 1. 尝试常规下载
    try:
        rprint("[cyan]🔄 Method 1: Standard download...[/cyan]")
        download(model_name)
        return
    except Exception as e:
        rprint(f"[yellow]⚠️ Standard download failed: {e}[/yellow]")

    # 2. 尝试使用代理下载
    proxy_url = "http://127.0.0.1:7890"
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    rprint(f"[cyan]🔄 Method 2: Retrying with local proxy ({proxy_url})...[/cyan]")
    
    try:
        download(model_name)
        return
    except Exception as e:
        rprint(f"[yellow]⚠️ Proxy download failed: {e}[/yellow]")

    # 3. 尝试清除缓存 + 代理下载 (解决 Wheel invalid 问题)
    try:
        rprint("[cyan]🔄 Method 3: Retrying with --no-cache-dir + proxy...[/cyan]")
        # spacy.cli.download 支持传递 pip 参数
        download(model_name, False, False, "--no-cache-dir")
        return
    except Exception as e:
        rprint(f"[red]❌ All automated installation methods failed.[/red]")
        raise e

@except_handler("Failed to load NLP Spacy model")
def init_nlp():
    language = "en" if load_key("whisper.language") == "en" else load_key("whisper.detected_language")
    model = get_spacy_model(language)
    rprint(f"[blue]⏳ Loading NLP Spacy model: <{model}> ...[/blue]")
    
    try:
        nlp = spacy.load(model)
    except OSError:
        rprint(f"[yellow]Model {model} not found. Starting robust installation process...[/yellow]")
        try:
            install_spacy_model(model)
            nlp = spacy.load(model)
        except Exception as e:
            # 最终报错信息
            rprint("\n" + "="*60)
            rprint(f"[bold red]❌ CRITICAL ERROR: Failed to install {model}.[/bold red]")
            rprint("[yellow]Possible reasons:[/yellow]")
            rprint("1. Network connection issues connecting to Github/PyPI.")
            rprint("2. Local proxy (127.0.0.1:7890) is not running or misconfigured.")
            rprint("\n[green]Please try installing manually in your terminal:[/green]")
            rprint(f"   [bold white]set HTTPS_PROXY=http://127.0.0.1:7890[/bold white]")
            rprint(f"   [bold white]python -m spacy download {model}[/bold white]")
            rprint("="*60 + "\n")
            raise e

    rprint(f"[green]✅ NLP Spacy model <{model}> loaded successfully![/green]")
    return nlp

# --------------------
# define the intermediate files
# --------------------
SPLIT_BY_COMMA_FILE = "output/log/split_by_comma.txt"
SPLIT_BY_CONNECTOR_FILE = "output/log/split_by_connector.txt"
SPLIT_BY_MARK_FILE = "output/log/split_by_mark.txt"