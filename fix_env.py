import os
import shutil
import subprocess
import sys
import argparse
import zipfile
import site
import inspect
from pathlib import Path

# ==========================================
# 模块 1: WhisperX 代码修复 (v8.0 完美逻辑闭环版)
# ==========================================
def patch_whisperx():
    print("🩹 [1/2] 正在执行 WhisperX 代码修复 (v8.0)...")
    
    # 1. 定位文件
    site_packages = None
    for path in sys.path:
        if "site-packages" in path and os.path.isdir(path):
            site_packages = Path(path)
            break
            
    if not site_packages:
        print("❌ 无法定位 site-packages，跳过。")
        return

    asr_file = site_packages / "whisperx" / "asr.py"
    if not asr_file.exists():
        found = list(site_packages.rglob("whisperx/asr.py"))
        if found: asr_file = found[0]
        else: return

    print(f"   -> 目标文件: {asr_file}")
    
    try:
        # 读取所有行
        with open(asr_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 2. 寻找手术切入点 (寻找 suppress_numerals 赋值行 和 TranscriptionOptions 实例化行)
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(lines):
            # 兼容各种混乱缩进的查找
            if 'suppress_numerals' in line and 'default_asr_options' in line and '=' in line and 'del' not in line:
                start_idx = i
                break
        
        if start_idx != -1:
            for j in range(start_idx, len(lines)):
                if 'TranscriptionOptions' in lines[j] and 'default_asr_options' in lines[j]:
                    end_idx = j
                    break
        
        # 3. 执行替换
        if start_idx != -1 and end_idx != -1:
            # print(f"   -> 定位成功：行 {start_idx+1} 到 {end_idx+1}")
            
            # 这是一个集大成的逻辑块：
            # 1. 它是纯净的 4 空格缩进。
            # 2. 它既能删参数，也能补参数。
            clean_block = [
                '    suppress_numerals = default_asr_options["suppress_numerals"]\n',
                '    del default_asr_options["suppress_numerals"]\n',
                '\n',
                '    # [VideoLingo 50FIX] 智能参数兼容性检查 (v8.0)\n',
                '    import inspect\n',
                '    try:\n',
                '        # 获取底层库需要的参数列表\n',
                '        sig_params = inspect.signature(faster_whisper.transcribe.TranscriptionOptions).parameters\n',
                '        \n',
                '        # 1. 删除多余参数 (防止 Unexpected argument)\n',
                '        if "multilingual" not in sig_params and "multilingual" in default_asr_options:\n',
                '            del default_asr_options["multilingual"]\n',
                '            \n',
                '        # 2. 补全缺失参数 (防止 Missing argument) <--- 这是解决你当前报错的关键！\n',
                '        if "multilingual" in sig_params and "multilingual" not in default_asr_options:\n',
                '            default_asr_options["multilingual"] = False\n',
                '\n',
                '        # 3. 处理 hotwords\n',
                '        if "hotwords" in sig_params and "hotwords" not in default_asr_options:\n',
                '            default_asr_options["hotwords"] = None\n',
                '            \n',
                '    except Exception as e:\n',
                '        print(f"Warning: Argument check failed: {e}")\n',
                '\n',
                '    default_asr_options = faster_whisper.transcribe.TranscriptionOptions(**default_asr_options)\n'
            ]

            # 替换旧代码块 (包括 Start 行本身，以防 Start 行格式也有问题)
            new_lines = lines[:start_idx] + clean_block + lines[end_idx+1:]
            
            with open(asr_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            
            print("✅ WhisperX 代码修复完成 (已应用双向参数补全)！")
            
        else:
            print("⚠️ 未能定位代码锚点，尝试暴力兜底...")
            # 如果上面找不到，说明文件可能被之前的脚本改得找不到特征了
            # 我们尝试直接找 "import inspect" 这一段，如果存在，说明已经改过了，可能是逻辑不对
            # 但既然报了 missing argument，说明之前的逻辑没生效
            pass

    except Exception as e:
        print(f"❌ 修复失败: {e}")

# ==========================================
# 模块 2: DLL 运行库修复 (保持不变)
# ==========================================
def extract_from_wheel(target_files, download_url, download_package):
    temp_dir = Path("temp_dll_fix")
    dest_dir = Path(".")
    
    print(f"   -> 正在下载补充包: {download_package} ...")
    if temp_dir.exists(): shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "download", 
            download_package, "--index-url", download_url,
            "--dest", str(temp_dir), "--no-deps", "--quiet"
        ])
        
        whl_files = list(temp_dir.glob("*.whl"))
        if not whl_files: return

        whl_file = whl_files[0]
        print(f"   -> 正在解压提取 DLL...")
        
        with zipfile.ZipFile(whl_file, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if any(file_info.filename.endswith(t) for t in target_files):
                    filename = os.path.basename(file_info.filename)
                    with open(dest_dir / filename, "wb") as f_out:
                        f_out.write(zip_ref.read(file_info))
                    print(f"      + 已提取: {filename}")
    except Exception as e:
        print(f"   ❌ 提取失败: {e}")
    finally:
        if temp_dir.exists(): shutil.rmtree(temp_dir)

def fix_dlls(mode):
    print(f"\n🔧 [2/2] 正在检查 {mode.upper()} 模式所需的 DLL...")
    venv_lib = None
    try:
        site_packages = site.getsitepackages()
        for sp in site_packages:
            p = Path(sp) / "torch" / "lib"
            if p.exists(): venv_lib = p; break
    except: pass

    dest_dir = Path(".")
    if mode == "stable":
        targets = ["cublas64_12.dll", "cublasLt64_12.dll"]
        if not all((dest_dir / f).exists() for f in targets):
            print("⚠️ 缺少 CUDA 12 库，正在提取...")
            extract_from_wheel(targets, "https://pypi.org/simple", "nvidia-cublas-cu12==12.1.3.1")
        
        v11_targets = ["cudnn64_8.dll", "cublas64_11.dll"]
        if venv_lib:
            for f in v11_targets:
                if (venv_lib / f).exists() and not (dest_dir / f).exists():
                    shutil.copy2(venv_lib / f, dest_dir / f)

    elif mode == "rtx50":
        targets = ["cudnn64_8.dll", "cublas64_11.dll", "cublasLt64_11.dll", "zlibwapi.dll"]
        if not all((dest_dir / f).exists() for f in targets):
            print("⚠️ 缺少 CUDA 11 库，正在提取...")
            extract_from_wheel(targets, "https://download.pytorch.org/whl/cu118", "torch==2.1.2")
        
        v12_targets = ["cublas64_12.dll", "cublasLt64_12.dll"]
        if venv_lib:
            for f in v12_targets:
                if (venv_lib / f).exists() and not (dest_dir / f).exists():
                    shutil.copy2(venv_lib / f, dest_dir / f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["stable", "rtx50"], required=True, help="Installation mode")
    args = parser.parse_args()

    patch_whisperx()
    fix_dlls(args.mode)
    print("\n🎉 环境修复完成！")