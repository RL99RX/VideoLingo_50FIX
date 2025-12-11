import os
import shutil
import subprocess
import sys
from pathlib import Path
import site
import zipfile

def get_venv_torch_lib():
    """获取本地 Torch 库路径"""
    try:
        site_packages = site.getsitepackages()
        for sp in site_packages:
            torch_lib = Path(sp) / "torch" / "lib"
            if torch_lib.exists(): return torch_lib
    except: pass
    return None

def extract_from_wheel(target_files, download_url, download_package):
    """安全下载并解压 whl，不安装"""
    temp_dir = Path("temp_dll_fix")
    dest_dir = Path(".")
    
    print(f"🌍 正在下载兼容性包 ({download_package})...")
    if temp_dir.exists(): shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "download", 
            download_package, "--index-url", download_url,
            "--dest", str(temp_dir), "--no-deps"
        ])
        
        whl_file = next(temp_dir.glob("*.whl"))
        print(f"📦 正在提取 DLL...")
        
        with zipfile.ZipFile(whl_file, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if any(file_info.filename.endswith(t) for t in target_files):
                    filename = os.path.basename(file_info.filename)
                    with open(dest_dir / filename, "wb") as f_out:
                        f_out.write(zip_ref.read(file_info))
                    print(f"   -> 已提取: {filename}")
    except Exception as e:
        print(f"❌ 提取失败: {e}")
    finally:
        if temp_dir.exists(): shutil.rmtree(temp_dir)

def fix_all_dlls():
    print("🚑 启动 DLL 修复程序 (安全版)...")
    dest_dir = Path(".")
    venv_lib = get_venv_torch_lib()
    
    # 0. 判断当前环境是哪种
    is_nightly = False
    try:
        import torch
        if "dev" in torch.__version__ or torch.version.cuda.startswith("12"):
            is_nightly = True
    except: pass

    # ==========================
    # 任务 1: CUDA 11 兼容性 (所有人都需要)
    # ==========================
    print("\n[1/2] 检查 CUDA 11 兼容性...")
    target_v11 = ["cudnn64_8.dll", "cublas64_11.dll", "cublasLt64_11.dll", "zlibwapi.dll"]
    
    if all((dest_dir / f).exists() for f in target_v11):
        print("✅ CUDA 11 库已就绪。")
    elif venv_lib and (venv_lib / "cudnn64_8.dll").exists():
        # Stable 用户优势：本地就有
        print("🔍 从本地 Torch 复制...")
        for f in target_v11:
            if (venv_lib / f).exists(): shutil.copy2(venv_lib / f, dest_dir / f)
    else:
        # RTX 50 用户劣势：本地全是新的，必须去下载旧的
        print("⚠️ 需要下载旧版 Torch 提取 CUDA 11 库...")
        extract_from_wheel(
            target_v11, 
            "https://download.pytorch.org/whl/cu118", 
            "torch==2.1.2"
        )

    # ==========================
    # 任务 2: CUDA 12 兼容性 (CTranslate2 需要)
    # ==========================
    print("\n[2/2] 检查 CUDA 12 兼容性...")
    target_v12 = ["cublas64_12.dll", "cublasLt64_12.dll"]

    if all((dest_dir / f).exists() for f in target_v12):
        print("✅ CUDA 12 库已就绪。")
    elif venv_lib and (venv_lib / "cublas64_12.dll").exists():
        # RTX 50 用户优势：本地 Torch 2.6 自带这些！
        print("🔍 从本地 Nightly Torch 复制...")
        for f in target_v12:
            if (venv_lib / f).exists(): shutil.copy2(venv_lib / f, dest_dir / f)
            print(f"   -> 已同步: {f}")
    else:
        # Stable 用户劣势：本地太旧，去下载补丁
        print("⚠️ 需要下载补丁提取 CUDA 12 库...")
        extract_from_wheel(
            target_v12, 
            "https://pypi.org/simple", 
            "nvidia-cublas-cu12==12.1.3.1"
        )

    print("\n🎉 修复完成。")

if __name__ == "__main__":
    fix_all_dlls()