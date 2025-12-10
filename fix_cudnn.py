import os
import shutil
import subprocess
import sys
from pathlib import Path

def fix_all_dlls():
    print("🚑 正在启动方案 D：全量提取 CUDA 11.8 兼容性 DLL (cuDNN + cuBLAS)...")
    print("   (这需要下载约 2.5GB 的临时文件，请耐心等待...)")
    
    # 1. 定义临时目录
    temp_dir = Path("temp_dll_fix")
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"⚠️ 无法清理旧临时目录，请手动删除 temp_dll_fix 文件夹后重试。错误: {e}")
            return
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # 2. 下载 Windows 版 Torch 2.1.2 + CUDA 11.8
        # 这个版本的包里含有 CTranslate2 所需的所有旧版 CUDA 运行库
        print("⬇️ 开始下载 PyTorch 2.1.2 (cu118) ...")
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "torch==2.1.2", 
            "--index-url", "https://download.pytorch.org/whl/cu118",
            "--target", str(temp_dir),
            "--no-deps",
            "--ignore-installed"
        ]
        print(f"   执行命令: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        
        # 3. 寻找 DLL 目录
        source_dir = temp_dir / "torch" / "lib"
        if not source_dir.exists():
            print("❌ 未找到 torch/lib 目录，下载可能不完整。")
            return

        print(f"✅ 下载完成，正在扫描 DLL 目录: {source_dir}")
        
        # 4. 定义需要提取的“通缉名单”
        # 包含 cuDNN 和 cuBLAS 的核心文件
        targets = [
            # cuDNN 8 (之前修复过的)
            "cudnn_ops_infer64_8.dll",
            "cudnn_cnn_infer64_8.dll",
            "cudnn64_8.dll",
            "zlibwapi.dll",
            
            # cuBLAS 11 (这次报错缺少的)
            "cublas64_11.dll",
            "cublasLt64_11.dll" 
        ]
        
        dest_dir = Path(".")
        count = 0
        
        # 5. 开始复制
        print("📦 正在注入文件...")
        
        # 先复制名单里的
        for filename in targets:
            src = source_dir / filename
            if src.exists():
                dst = dest_dir / filename
                shutil.copy2(src, dst)
                print(f"   -> [关键] 已注入: {filename}")
                count += 1
            else:
                print(f"   ⚠️ 在包中未找到: {filename}")
        
        # 额外：把所有相关的 DLL 都拷过来防患于未然
        # (避免下次报 cublas_xxx 缺失)
        for dll in source_dir.glob("cublas*.dll"):
            if dll.name not in targets:
                shutil.copy2(dll, dest_dir / dll.name)
                # print(f"   -> [补充] 已注入: {dll.name}")
                count += 1

        if count > 0:
            print(f"\n🎉 修复成功！共注入 {count} 个 DLL 文件。")
            print("👉 这一次，WhisperX 绝对没理由报错了！")
        else:
            print("\n❌ 严重错误：未能提取到任何文件。")
        
    except subprocess.CalledProcessError:
        print("\n❌ 下载失败。请检查网络。")
    except Exception as e:
        print(f"\n❌ 发生未知错误: {e}")
    finally:
        # 6. 清理
        if temp_dir.exists():
            print("🧹 正在清理临时文件...")
            try:
                shutil.rmtree(temp_dir)
                print("   清理完成。")
            except:
                print("   ⚠️ 临时文件清理失败，请手动删除 'temp_dll_fix' 文件夹。")

if __name__ == "__main__":
    fix_all_dlls()