import os
import sys
from pathlib import Path

def get_site_packages():
    """不通过 import 获取 site-packages 路径"""
    for path in sys.path:
        if "site-packages" in path and os.path.isdir(path):
            return Path(path)
    return None

def patch_whisperx():
    print("🔍 正在定位 whisperx 文件...")
    
    site_pkg = get_site_packages()
    if not site_pkg:
        print("❌ 无法定位 site-packages 目录，跳过修复。")
        return

    # 直接拼接路径
    asr_file = site_pkg / "whisperx" / "asr.py"
    
    if not asr_file.exists():
        print(f"⚠️ 未找到文件: {asr_file}")
        # 深度搜索
        found = list(site_pkg.rglob("whisperx/asr.py"))
        if found:
            asr_file = found[0]
            print(f"✅ 通过搜索找到文件: {asr_file}")
        else:
            print("❌ 彻底未找到 whisperx/asr.py，请确认已安装 whisperx。")
            return

    print(f"🔧 处理文件: {asr_file}")
    
    try:
        with open(asr_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        PATCH_MARKER = "# [VideoLingo 50FIX]"
        TARGET_SIG = "faster_whisper.transcribe.TranscriptionOptions"
        
        # 目标代码块 (注意缩进，通常是8个空格)
        # 我们稍微调整一下 NEW_BLOCK 的格式，使其更通用
        NEW_BLOCK_LINES = [
            "        # [VideoLingo 50FIX] 智能参数清洗\n",
            "        if \"multilingual\" in default_asr_options: del default_asr_options[\"multilingual\"]\n",
            "        if \"hotwords\" not in default_asr_options: default_asr_options[\"hotwords\"] = None\n",
            "        default_asr_options = faster_whisper.transcribe.TranscriptionOptions(**default_asr_options)\n"
        ]

        # 1. 检查文件状态
        content = "".join(lines)
        if PATCH_MARKER in content:
            if 'del default_asr_options["multilingual"]' in content:
                print("✅ 文件已是最新修复版本，跳过。")
                return
            else:
                print("🔄 检测到旧版补丁 (逻辑过时)，正在执行智能升级...")
                # === 核心修复逻辑：流式替换 ===
                new_lines = []
                skip_mode = False
                patched = False
                
                for line in lines:
                    # 如果遇到了旧补丁的标记，开始跳过旧代码
                    if PATCH_MARKER in line:
                        skip_mode = True
                        continue
                    
                    # 如果在跳过模式中，直到遇到了关键结束行
                    if skip_mode and TARGET_SIG in line:
                        skip_mode = False
                        # 插入新代码块
                        new_lines.extend(NEW_BLOCK_LINES)
                        patched = True
                        continue
                    
                    # 正常行直接保留
                    if not skip_mode:
                        new_lines.append(line)
                
                if patched:
                    with open(asr_file, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    print("✅ 已成功将旧补丁升级为新补丁！")
                    return
                else:
                    print("⚠️ 升级失败：未找到代码闭合点，建议重装 whisperx。")
                    return

        # 2. 如果完全没修过 (全新安装的情况)
        if any(TARGET_SIG in line for line in lines):
            # 查找目标行并替换
            new_lines = []
            for line in lines:
                if TARGET_SIG in line and PATCH_MARKER not in line:
                    # 找到了原始代码行，替换成我们的 Block
                    # 为了保持缩进，我们要获取原行的前导空格
                    indent = line[:line.find(line.lstrip())]
                    # 动态调整 NEW_BLOCK 的缩进
                    adjusted_block = [indent + l.lstrip() for l in NEW_BLOCK_LINES]
                    new_lines.extend(adjusted_block)
                    print("✅ 原始文件修复成功！")
                else:
                    new_lines.append(line)
            
            with open(asr_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        else:
            print("⚠️ 未在文件中找到目标代码行，可能 whisperx 版本已大幅更新？")

    except Exception as e:
        print(f"❌ 修复过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    patch_whisperx()