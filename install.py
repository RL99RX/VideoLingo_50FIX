import os
import sys
import subprocess
import shutil
import time

# ... (Logs 和 run_cmd 函数保持不变，为了省篇幅我省略了，请保留之前的) ...
class Colors:
    HEADER = '\033[95m'; BLUE = '\033[94m'; GREEN = '\033[92m'; 
    WARNING = '\033[93m'; FAIL = '\033[91m'; ENDC = '\033[0m'; BOLD = '\033[1m'

def log(msg, level="INFO"):
    print(f"{Colors.BLUE if level=='INFO' else Colors.GREEN if level=='SUCCESS' else Colors.WARNING if level=='WARN' else Colors.FAIL if level=='ERROR' else Colors.HEADER} [{level}] {msg}{Colors.ENDC}")

def run_cmd(cmd, env=None, check=True):
    print(f"{Colors.BOLD}   [EXEC] {' '.join(cmd)}{Colors.ENDC}")
    try:
        subprocess.run(cmd, check=check, env=env)
    except subprocess.CalledProcessError as e:
        log(f"命令执行失败 (Exit Code: {e.returncode})", "ERROR")
        sys.exit(1)

def install_core():
    log("正在安装通用依赖...", "STEP")
    run_cmd(["uv", "sync"])

def create_override_file(is_rtx50):
    filename = "uv_override.txt"
    if is_rtx50:
        # === RTX 50 (你的 Nightly 配置) ===
        # 关键修改：增加 numpy<2 强制降级
        content = """
faster-whisper==1.1.0
ctranslate2>=4.5.0
torch>=2.6.0.dev
torchaudio>=2.6.0.dev
torchvision>=0.21.0.dev
numpy<2
"""
    else:
        content = """
faster-whisper==1.0.3
torch==2.1.2+cu118
torchaudio==2.1.2+cu118
torchvision==0.16.2+cu118
"""
    with open(filename, "w", encoding="utf-8") as f: f.write(content.strip())
    return filename

def install_torch_stack(is_rtx50):
    log("正在注入核心组件...", "STEP")
    override_file = create_override_file(is_rtx50)
    wx_git = "whisperx @ git+https://github.com/m-bain/whisperx.git@7307306a9d8dd0d261e588cc933322454f853853"
    
    if is_rtx50:
        log("🔥 激活 RTX 50 Nightly 模式 (cu128)", "WARN")
        deps = [
            "torch>=2.6.0.dev", 
            "torchaudio>=2.6.0.dev", 
            "torchvision>=0.21.0.dev",
            "faster-whisper==1.1.0", 
            "onnxruntime-gpu>=1.19.0", 
            "av==13.1.0", 
            "ctranslate2>=4.5.0",
            wx_git
        ]
        cmd = ["uv", "pip", "install"] + deps + [
            "--index-url", "https://download.pytorch.org/whl/nightly/cu128", 
            "--extra-index-url", "https://pypi.org/simple",
            "--prerelease=allow",
            "--override", override_file
        ]
        with open(".enable_nightly", "w") as f: f.write("1")
    else:
        # Stable 逻辑... (保持不变)
        log("🛡️ 激活 Standard Stable 模式", "INFO")
        deps = [
            "torch==2.1.2+cu118", "torchaudio==2.1.2+cu118", "torchvision==0.16.2+cu118",
            "faster-whisper==1.0.3", 
            "onnxruntime-gpu==1.16.3",
            wx_git
        ]
        cmd = ["uv", "pip", "install"] + deps + [
            "--index-url", "https://download.pytorch.org/whl/cu118",
            "--extra-index-url", "https://pypi.org/simple",
            "--override", override_file
        ]
        if os.path.exists(".enable_nightly"): os.remove(".enable_nightly")

    try:
        run_cmd(cmd)
    finally:
        if os.path.exists(override_file): os.remove(override_file)

def main():
    # 简单的显卡检测
    is_rtx50 = False
    if shutil.which("nvidia-smi"):
        try:
            o = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], encoding='utf-8')
            if "RTX 50" in o: is_rtx50 = True
        except: pass

    # 锁定版本
    target_py = "3.11" if is_rtx50 else "3.10"
    run_cmd(["uv", "python", "pin", target_py])

    # 安装流程
    install_core()
    install_torch_stack(is_rtx50)
    
    with open(".install_completed", "w") as f: f.write("ok")
    log("安装完成！", "SUCCESS")

if __name__ == "__main__":
    main()