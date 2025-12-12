import os
import sys
import subprocess
import shutil

# ==========================================
# 1. 基础配置 (通用库)
# ==========================================
BASE_DEPENDENCIES = [
    "pip",  # <--- [关键修复] 显式添加 pip，否则 uv 环境无法运行 python -m pip
    "pandas==2.2.3",
    "scipy",
    "matplotlib", 
    "openai==1.55.3",
    "replicate==0.33.0",
    "requests==2.32.3",
    "httpx",
    "transformers==4.39.3",
    "moviepy==1.0.3",
    "librosa==0.10.2.post1",
    "soundfile",
    "pydub==0.25.1",
    "opencv-python==4.10.0.84",
    "resampy==0.4.3",
    "streamlit==1.38.0",
    "yt-dlp",
    "rich",
    "ruamel.yaml",
    "json-repair",
    "inquirerpy",
    "autocorrect-py",
    "openpyxl==3.1.5",
    "pyyaml==6.0.2",
    "spacy==3.7.4",
    "syllables",
    "pypinyin",
    "g2p-en",
    "xmltodict",
    "edge-tts",
    "pytorch-lightning==2.3.3",
    "lightning==2.3.3",
    "nvidia-ml-py",
    "demucs @ git+https://github.com/adefossez/demucs",
    "en_core_web_lg @ https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.7.0/en_core_web_lg-3.7.0-py3-none-any.whl",
    "zh_core_web_lg @ https://github.com/explosion/spacy-models/releases/download/zh_core_web_lg-3.7.0/zh_core_web_lg-3.7.0-py3-none-any.whl"
]

OPTIONAL_DEPENDENCIES = """
[project.optional-dependencies]
ja = ["ja_core_news_md @ https://github.com/explosion/spacy-models/releases/download/ja_core_news_md-3.7.0/ja_core_news_md-3.7.0-py3-none-any.whl"]
ru = ["ru_core_news_md @ https://github.com/explosion/spacy-models/releases/download/ru_core_news_md-3.7.0/ru_core_news_md-3.7.0-py3-none-any.whl"]
fr = ["fr_core_news_md @ https://github.com/explosion/spacy-models/releases/download/fr_core_news_md-3.7.0/fr_core_news_md-3.7.0-py3-none-any.whl"]
es = ["es_core_news_md @ https://github.com/explosion/spacy-models/releases/download/es_core_news_md-3.7.0/es_core_news_md-3.7.0-py3-none-any.whl"]
de = ["de_core_news_md @ https://github.com/explosion/spacy-models/releases/download/de_core_news_md-3.7.0/de_core_news_md-3.7.0-py3-none-any.whl"]
it = ["it_core_news_md @ https://github.com/explosion/spacy-models/releases/download/it_core_news_md-3.7.0/it_core_news_md-3.7.0-py3-none-any.whl"]
all_langs = ["videolingo[ja,ru,fr,es,de,it]"]
"""

# ==========================================
# 2. 模式特有配置 (Mode Specific)
# ==========================================
CONFIGS = {
    "stable": {
        "desc": "稳定版 (Stable - CUDA 11)",
        "python": "==3.10.*",
        "deps": [
            "torch==2.1.2+cu118",
            "torchaudio==2.1.2+cu118",
            "torchvision==0.16.2+cu118",
            "faster-whisper==1.0.3",
            "numpy==1.26.4",
            "whisperx @ git+https://github.com/m-bain/whisperx.git@7307306a9d8dd0d261e588cc933322454f853853"
        ],
        "index": [
            {"name": "pytorch", "url": "https://download.pytorch.org/whl/cu118"}
        ],
        "overrides": [
            "faster-whisper==1.0.3"
        ]
    },
    "rtx50": {
        "desc": "RTX 50 专用版 (Nightly - CUDA 12)",
        "python": "==3.11.*",
        "deps": [
            "torch>=2.6.0.dev",
            "torchaudio>=2.6.0.dev",
            "torchvision>=0.21.0.dev",
            "faster-whisper==1.1.0",
            "numpy<2",
            "ctranslate2>=4.5.0",
            "onnxruntime-gpu>=1.19.0",
            "av==13.1.0",
            "whisperx @ git+https://github.com/m-bain/whisperx.git@7307306a9d8dd0d261e588cc933322454f853853"
        ],
        "index": [
            {"name": "pytorch-nightly", "url": "https://download.pytorch.org/whl/nightly/cu128"}
        ],
        "overrides": [
            "faster-whisper==1.1.0", 
            "numpy<2",
            "torch>=2.6.0.dev",
            "torchaudio>=2.6.0.dev",
            "torchvision>=0.21.0.dev",
            "ctranslate2>=4.5.0"
        ]
    }
}

class Colors:
    BLUE = '\033[94m'; GREEN = '\033[92m'; WARN = '\033[93m'; FAIL = '\033[91m'; ENDC = '\033[0m'

def log(msg, level="INFO"):
    color = Colors.BLUE if level=="INFO" else Colors.GREEN if level=="SUCCESS" else Colors.WARN
    print(f"{color}[{level}] {msg}{Colors.ENDC}")

def run_cmd(cmd, check=True):
    print(f"   [EXEC] {' '.join(cmd)}")
    subprocess.run(cmd, check=check, shell=(os.name=='nt'))

def get_current_mode():
    if os.path.exists(".current_mode"):
        try:
            with open(".current_mode", "r") as f:
                return f.read().strip()
        except: pass
    return None

def set_current_mode(mode):
    with open(".current_mode", "w") as f:
        f.write(mode)

def ensure_config():
    """确保 config.yaml 存在"""
    if os.path.exists("config.yaml"):
        return

    log("检测到 config.yaml 缺失，正在初始化配置...", "WARN")
    if os.path.exists("config.example.yaml"):
        try:
            shutil.copy("config.example.yaml", "config.yaml")
            log("已从 config.example.yaml 创建 config.yaml", "SUCCESS")
        except Exception as e:
            log(f"复制配置文件失败: {e}", "FAIL")
    else:
        # 如果连 example 都没有，创建一个最小可用配置（防止 crash）
        log("未找到模板，正在创建默认 config.yaml...", "WARN")
        with open("config.yaml", "w", encoding="utf-8") as f:
            f.write("# Auto-generated config\n")
            f.write("spacy_model_map:\n  en: en_core_web_lg\n  zh: zh_core_web_lg\n")

def generate_pyproject(mode):
    log(f"正在配置 {mode} 模式的依赖...", "INFO")
    
    config = CONFIGS[mode]
    final_deps = BASE_DEPENDENCIES + config["deps"]
    
    deps_str = "[\n    " + ",\n    ".join([f'"{d}"' for d in final_deps]) + "\n]"

    override_str = ""
    if config.get("overrides"):
        override_items = ",\n    ".join([f'"{o}"' for o in config["overrides"]])
        override_str = f"override-dependencies = [\n    {override_items}\n]"

    index_section = ""
    if config.get("index"):
        index_section += "\n"
        for idx in config["index"]:
            index_section += f"[[tool.uv.index]]\n"
            index_section += f'name = "{idx["name"]}"\n'
            index_section += f'url = "{idx["url"]}"\n\n'

    content = f"""[project]
name = "videolingo"
version = "3.1.9"
description = "VideoLingo: 连接世界的每一帧"
readme = "README.md"
requires-python = "{config['python']}"
dependencies = {deps_str}

{OPTIONAL_DEPENDENCIES}

[tool.uv]
index-strategy = "unsafe-best-match"
{override_str}
{index_section}
"""
    with open("pyproject.toml", "w", encoding="utf-8") as f:
        f.write(content)

def detect_gpu():
    if shutil.which("nvidia-smi"):
        try:
            o = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], encoding='utf-8')
            if "RTX 50" in o: return "rtx50"
        except: pass
    return "stable"

def main():
    print(f"{Colors.GREEN}=== VideoLingo 智能安装程序 (v3.1.9 Patch 2) ==={Colors.ENDC}")
    
    # 0. 先检查配置文件，防止后续 st.py 崩溃
    ensure_config()

    detected_mode = detect_gpu()
    default_opt = "2" if detected_mode == "rtx50" else "1"
    
    opt1_label = f"1. {CONFIGS['stable']['desc']}"
    opt2_label = f"2. {CONFIGS['rtx50']['desc']}"
    
    if detected_mode == "stable":
        opt1_label += f" {Colors.GREEN}(推荐/默认){Colors.ENDC}"
    else:
        opt2_label += f" {Colors.GREEN}(推荐/默认){Colors.ENDC}"

    print("\n请选择安装模式:")
    print(f"  {opt1_label}")
    print(f"  {opt2_label}")
    
    choice = input(f"\n输入数字选择 (回车默认 {default_opt}): ").strip()
    if not choice: choice = default_opt
    
    if choice == "2": mode = "rtx50"
    elif choice == "1": mode = "stable"
    else: mode = detected_mode
    
    log(f"目标模式: {mode}", "INFO")

    old_mode = get_current_mode()
    
    # 1. 重新生成配置
    generate_pyproject(mode)

    # 2. 状态判断
    if old_mode != mode:
        if old_mode is None:
             log("首次运行，初始化环境...", "INFO")
        else:
             log(f"检测到模式切换 ({old_mode} -> {mode})，正在清理旧环境...", "WARN")
        
        if os.path.exists("uv.lock"):
            try: os.remove("uv.lock")
            except: pass
        
        target_py = "3.11" if mode == "rtx50" else "3.10"
        try:
            run_cmd(["uv", "python", "pin", target_py], check=False)
        except Exception as e:
            log(f"Python 锁定警告: {e}", "WARN")
            
        set_current_mode(mode)
    else:
        log("模式未变更，保留锁文件。", "SUCCESS")

    log("开始同步环境...", "INFO")
    try:
        # 这次同步会安装 pip，解决后续报错
        run_cmd(["uv", "sync"])
    except subprocess.CalledProcessError:
        log("uv sync 执行失败。", "FAIL")
        sys.exit(1)

    if os.path.exists("fix_env.py"):
        log("正在执行环境后处理...", "INFO")
        # 此时环境里已经有 pip 了，fix_env.py 不会再报错
        run_cmd(["uv", "run", "python", "fix_env.py", "--mode", mode])
    else:
        log("未找到 fix_env.py，跳过后处理。", "WARN")

    with open(".install_completed", "w") as f: f.write("ok")
    log("✅ 安装完成！请运行: uv run st.py", "SUCCESS")

if __name__ == "__main__":
    main()