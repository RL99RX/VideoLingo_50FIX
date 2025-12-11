import os
import sys
import subprocess
import shutil

# ==========================================
# 0. 优先清理
# ==========================================
if os.path.exists("pyproject.toml"):
    try: os.remove("pyproject.toml")
    except: pass

# ==========================================
# 1. 基础配置 (通用库)
# ==========================================
BASE_DEPENDENCIES = [
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
    # 移除了 "pip"，uv 不需要它
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
        # === 关键修复点 ===
        # 强制覆盖所有冲突依赖，包括 ctranslate2
        "overrides": [
            "faster-whisper==1.1.0", 
            "numpy<2",
            "torch>=2.6.0.dev",
            "torchaudio>=2.6.0.dev",
            "torchvision>=0.21.0.dev",
            "ctranslate2>=4.5.0"  # <--- 必须加这行，否则 whisperx 会锁死 4.4.0
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

def generate_pyproject(mode):
    if os.path.exists("pyproject.toml"):
        try: os.remove("pyproject.toml")
        except: pass

    log(f"正在构建 {mode} 模式的依赖配置...", "INFO")
    
    config = CONFIGS[mode]
    
    # === 优化点：不再强行绑定 sys_platform ===
    # uv sync 默认针对当前环境解析，保持依赖列表纯净
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
    print(f"{Colors.GREEN}=== VideoLingo 智能安装程序 (v3.1.9) ==={Colors.ENDC}")
    
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
    
    log(f"已锁定模式: {mode}", "INFO")

    # 总是清理旧的锁文件，因为我们动态修改了 pyproject.toml
    if os.path.exists("uv.lock"):
        try:
            os.remove("uv.lock")
            log("已自动清理旧锁文件以适应新模式。", "SUCCESS")
        except Exception as e:
            log(f"清理锁文件失败: {e}", "WARN")

    target_py = "3.11" if mode == "rtx50" else "3.10"
    try:
        # 使用 allow-existing 防止重复 pin 报错
        run_cmd(["uv", "python", "pin", target_py]) 
    except Exception as e:
        log(f"Python 版本锁定警告: {e}", "WARN")

    generate_pyproject(mode)

    log("开始同步环境...", "INFO")
    try:
        run_cmd(["uv", "sync"])
    except subprocess.CalledProcessError:
        log("uv sync 执行失败，请检查上方红字报错。", "FAIL")
        sys.exit(1)

    if os.path.exists("fix_env.py"):
        log("正在执行环境后处理...", "INFO")
        run_cmd(["uv", "run", "python", "fix_env.py", "--mode", mode])
    else:
        log("未找到 fix_env.py，跳过后处理步骤。", "WARN")

    with open(".install_completed", "w") as f: f.write("ok")
    log("✅ 安装完成！请运行: uv run st.py", "SUCCESS")

if __name__ == "__main__":
    main()