import os
import sys
import platform
import subprocess
import shutil

# 确保当前目录在 sys.path 中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

ascii_logo = """
__     ___     _            _     _                    
\ \   / (_) __| | ___  ___ | |   (_)_ __   __ _  ___   
 \ \ / /| |/ _` |/ _ \/ _ \| |   | | '_ \ / _` |/ _ \  
  \ V / | | (_| |  __/ (_) | |___| | | | | (_| | (_) |
   \_/  |_|\__,_|\___|\___/|_____|_|_| |_|\__, |\___/  
                                          |___/        
"""

def run_cmd(cmd, env=None, ignore_errors=False):
    """封装subprocess调用"""
    print(f"👉 Running: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd, env=env)
    except subprocess.CalledProcessError as e:
        if ignore_errors:
            print(f"⚠️ Command failed but ignored: {e}")
        else:
            print(f"❌ Command failed: {e}")
            raise e

def install_package(*packages, index_url=None, no_deps=False, force=False):
    """智能pip安装函数"""
    cmd = [sys.executable, "-m", "pip", "install"]
    if no_deps: cmd.append("--no-deps")
    if force: cmd.append("--force-reinstall")
    for pkg in packages:
        cmd.append(pkg)
    if index_url:
        cmd.extend(["--index-url", index_url])
    run_cmd(cmd)

def uninstall_package(*packages):
    """强制卸载包"""
    cmd = [sys.executable, "-m", "pip", "uninstall", "-y"]
    for pkg in packages:
        cmd.append(pkg)
    run_cmd(cmd, ignore_errors=True)

def is_conda_env():
    return os.path.exists(os.path.join(sys.prefix, 'conda-meta'))

def check_system_ffmpeg():
    """检查系统 FFmpeg"""
    if not shutil.which("ffmpeg"): return False
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if "conda" not in result.stdout.lower(): return True
        return False
    except: return False

def remove_conda_ffmpeg():
    """清理 Conda 的残废 FFmpeg"""
    if platform.system() == "Windows":
        conda_bin = os.path.join(sys.prefix, 'Library', 'bin')
        for target in ["ffmpeg.exe", "ffplay.exe", "ffprobe.exe"]:
            target_path = os.path.join(conda_bin, target)
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                    print(f"🗑️ 已删除 Conda 自带文件: {target}")
                except: pass

def check_nvidia_gpu():
    """检测GPU"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nvidia-ml-py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import pynvml
        pynvml.nvmlInit()
        if pynvml.nvmlDeviceGetCount() > 0:
            for i in range(pynvml.nvmlDeviceGetCount()):
                name = pynvml.nvmlDeviceGetName(pynvml.nvmlDeviceGetHandleByIndex(i))
                if "RTX 50" in name.upper():
                    return True, True
            return True, False
    except: pass
    return False, False

def install_smart_requirements():
    """读取 requirements.txt 并安装，但跳过核心冲突包"""
    req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(req_path): return

    with open(req_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    safe_reqs = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"): continue
        if "git+" in line: continue 
        # 跳过核心冲突包，留给后面手动处理
        if any(x in line.lower() for x in ["torch", "numpy", "av", "whisperx", "demucs", "spacy"]): 
            continue 
        safe_reqs.append(line)
    
    if safe_reqs:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
            tmp.write('\n'.join(safe_reqs))
            tmp_path = tmp.name
        try:
            run_cmd([sys.executable, "-m", "pip", "install", "-r", tmp_path])
        finally:
            os.remove(tmp_path)

def finalize_environment():
    """【核心逻辑】执行最终的环境补全和定型"""
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    
    console.print(Panel("🛡️ 执行最终环境定型 (Smart Constraint)...", style="magenta"))
    
    # 1. 暴力卸载 Numpy (清除 2.0 版本的残留)
    console.print("正在清理环境...")
    uninstall_package("numpy", "spacy", "thinc", "weasel")
    
    # 2. 【关键策略】同时安装 Spacy 和 锁定的 Numpy
    # 这样 pip 会自动计算依赖，安装 langcodes 等小弟，但绝不会升级 Numpy
    console.print("正在智能安装 Spacy 生态...")
    
    # 这里的技巧是：把 numpy==1.26.4 和 spacy 一起传给 pip
    # pip 会自动找到 spacy 依赖中兼容 numpy 1.26.4 的版本
    packages_to_install = [
        "numpy==1.26.4", 
        "spacy==3.7.4", 
        "thinc==8.2.3",
        "weasel==0.3.4" # 显式指定几个核心包，防止 pip 犯傻
    ]
    
    # 注意：这里把 no_deps 去掉了！让 pip 自动去补全 langcodes, catalogue 等
    install_package(*packages_to_install, force=True)
    
    # 3. 补漏 (matplotlib)
    install_package("matplotlib")
    
    # 4. 下载模型
    subprocess.run([sys.executable, "-m", "spacy", "download", "zh_core_web_sm"])
    
    console.print("[green]✅ 环境修复完成！依赖链已自动修复且锁定。[/green]")

def install_core_dependencies():
    from rich.console import Console
    from rich.panel import Panel
    console = Console()

    # 0. 系统检查
    if not check_system_ffmpeg():
        console.print(Panel("❌ 未检测到系统 FFmpeg！请先运行: choco install ffmpeg-full -y", style="bold red"))
        input("按 Enter 键继续...")

    # 1. Conda 二进制依赖
    if is_conda_env():
        console.print(Panel("1. 安装 Conda 依赖...", style="cyan"))
        try:
            subprocess.check_call(["conda", "install", "av=11.0.0", "cudnn=8.9.7.29", "-c", "conda-forge", "-y"])
            remove_conda_ffmpeg()
            console.print("[green]✅ Conda 依赖安装成功[/green]")
        except: pass

    # 2. 预装 Numpy
    install_package("numpy==1.26.4")

    # 3. 安装 Git 包
    console.print(Panel("2. 安装 WhisperX 和 Demucs...", style="cyan"))
    install_package("git+https://github.com/m-bain/whisperx.git@7307306a9d8dd0d261e588cc933322454f853853")
    install_package("git+https://github.com/adefossez/demucs.git")

    # 4. 补全 requirements
    console.print(Panel("3. 补全普通依赖...", style="cyan"))
    install_smart_requirements()

    # 5. 强制重装 PyTorch (50系特供)
    has_gpu, is_rtx50 = check_nvidia_gpu()
    if has_gpu and is_rtx50:
        console.print(Panel("4. 🔥 RTX 50 detected! 强制重装 PyTorch Nightly...", style="red"))
        install_package("torch", "torchvision", "torchaudio", 
                      index_url="https://download.pytorch.org/whl/nightly/cu128", 
                      force=True) 
    elif has_gpu:
        install_package("torch==2.0.0", "torchaudio==2.0.0", "torchvision", index_url="https://download.pytorch.org/whl/cu118")
    else:
        install_package("torch==2.1.2", "torchaudio==2.1.2", "torchvision")

    # 6. 挂载项目
    install_package("-e", ".", no_deps=True)
    
    # 7. 【最后一步】执行外科手术式修复
    finalize_environment()

def main():
    try:
        import rich
        import requests
        import ruamel.yaml
        import InquirerPy
    except ImportError:
        install_package("requests", "rich", "ruamel.yaml", "InquirerPy")

    from rich.console import Console
    from rich.panel import Panel
    from InquirerPy import inquirer
    
    console = Console()
    console.print(Panel(ascii_logo, title="[bold green]VideoLingo Ultimate Installer (Surgical Fix)[/bold green]", border_style="bright_blue"))

    if inquirer.confirm(message="Do you need to auto-configure PyPI mirrors?", default=False).execute():
        from core.utils.pypi_autochoose import main as choose_mirror
        choose_mirror()

    try:
        install_core_dependencies()
        console.print(Panel("Installation Completed! 🎉", title="Success", style="bold green"))
        subprocess.Popen(["streamlit", "run", "st.py", "--server.fileWatcherType", "none"])
    except Exception as e:
        console.print(Panel(f"Installation Failed: {e}", title="Error", style="bold red"))

if __name__ == "__main__":
    main()