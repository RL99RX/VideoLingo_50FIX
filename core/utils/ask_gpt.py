import os
import json
import shutil
import tempfile
from threading import Lock
import json_repair
from openai import OpenAI
from core.utils.config_utils import load_key
from rich import print as rprint
from core.utils.decorator import except_handler

# ==============================================================================
# Global Configuration & Singletons
# ==============================================================================

LOCK = Lock()
GPT_LOG_FOLDER = 'output/gpt_log'
_GLOBAL_CLIENT = None  # Lazy load client

def get_client():
    """单例模式获取 OpenAI Client"""
    global _GLOBAL_CLIENT
    if _GLOBAL_CLIENT is None:
        base_url = load_key("api.base_url")
        # 智能处理 Base URL
        if 'ark.cn-beijing.volces.com' in base_url:
            pass 
        elif 'v1' not in base_url and 'volces' not in base_url:
            base_url = base_url.strip('/') + '/v1'
            
        _GLOBAL_CLIENT = OpenAI(
            api_key=load_key("api.key"), 
            base_url=base_url,
            timeout=300
        )
    return _GLOBAL_CLIENT

# ==============================================================================
# Cache System (Atomic Writes)
# ==============================================================================

def _load_cache(prompt, resp_type, log_title):
    file = os.path.join(GPT_LOG_FOLDER, f"{log_title}.json")
    if not os.path.exists(file):
        return False
    try:
        with LOCK:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 倒序查找最新结果
            for item in reversed(data):
                if item["prompt"] == prompt and item["resp_type"] == resp_type:
                    return item["resp"]
    except (json.JSONDecodeError, OSError):
        rprint(f"[yellow]⚠️ Cache file {file} is corrupted, ignoring cache.[/yellow]")
        return False
    return False

def _save_cache(model, prompt, resp_content, resp_type, resp, message=None, log_title="default"):
    with LOCK:
        file = os.path.join(GPT_LOG_FOLDER, f"{log_title}.json")
        os.makedirs(os.path.dirname(file), exist_ok=True)
        logs = []
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
        logs.append({
            "model": model, "prompt": prompt, "resp_content": resp_content, 
            "resp_type": resp_type, "resp": resp, "message": message
        })
        # 原子写入防止损坏
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file), text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=4)
            shutil.move(temp_path, file)
        except Exception as e:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

# ==============================================================================
# Main GPT Function
# ==============================================================================

@except_handler("GPT request failed", retry=5)
def ask_gpt(prompt, resp_type=None, valid_def=None, log_title="default"):
    if not load_key("api.key"):
        raise ValueError("API key is not set")

    # 1. Check Cache
    cached = _load_cache(prompt, resp_type, log_title)
    if cached:
        rprint("[dim]Use cache response[/dim]")
        return cached

    client = get_client()
    model = load_key("api.model")
    use_json_mode = (resp_type == "json") and load_key("api.llm_support_json")
    response_format = {"type": "json_object"} if use_json_mode else None
    
    # 2. API Call
    try:
        resp_raw = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            response_format=response_format,
            temperature=0.3
        )
    except Exception as e:
        raise e # Network error -> Retry

    resp_content = resp_raw.choices[0].message.content

    # 3. Parse
    if resp_type == "json":
        try:
            resp = json_repair.loads(resp_content)
        except Exception:
            _save_cache(model, prompt, resp_content, resp_type, None, message="JSON Parse Error", log_title="error")
            raise ValueError(f"❎ JSON Parse Error: {resp_content[:50]}...")
    else:
        resp = resp_content
    
    # 4. Validate (Business Logic)
    if valid_def:
        try:
            valid_resp = valid_def(resp)
            if valid_resp['status'] != 'success':
                _save_cache(model, prompt, resp_content, resp_type, resp, message=valid_resp['message'], log_title="error")
                raise ValueError(f"❎ Validation Error: {valid_resp['message']}")
        except ValueError as ve:
            raise ve
        except Exception as e:
            _save_cache(model, prompt, resp_content, resp_type, resp, message=str(e), log_title="error")
            raise ValueError(f"Validation Crash: {str(e)}")

    # 5. Success
    _save_cache(model, prompt, resp_content, resp_type, resp, log_title=log_title)
    return resp