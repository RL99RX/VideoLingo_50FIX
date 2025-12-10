import os
import sys
import types

# ==========================================
# 🚑 紧急医疗包：在导入 whisperx 之前先修好 torchaudio
# ==========================================
import torch
import torchaudio

# 补丁 1: 伪造被删除的 backend 函数 (针对 torchaudio 2.1+)
if not hasattr(torchaudio, "set_audio_backend"):
    torchaudio.set_audio_backend = lambda backend: None
if not hasattr(torchaudio, "get_audio_backend"):
    torchaudio.get_audio_backend = lambda: "soundfile"
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

# 补丁 2: 伪造 torchaudio.backend.common 模块 (针对 pyannote.audio)
if "torchaudio.backend" not in sys.modules:
    mock_backend = types.ModuleType("torchaudio.backend")
    mock_common = types.ModuleType("torchaudio.backend.common")
    
    class MockAudioMetaData:
        def __init__(self, sample_rate, num_frames, num_channels, bits_per_sample, encoding):
            self.sample_rate = sample_rate
            self.num_frames = num_frames
            self.num_channels = num_channels
            self.bits_per_sample = bits_per_sample
            self.encoding = encoding
            
    mock_common.AudioMetaData = MockAudioMetaData
    mock_backend.common = mock_common
    sys.modules["torchaudio.backend"] = mock_backend
    sys.modules["torchaudio.backend.common"] = mock_common

print("✅ Torchaudio 兼容性补丁已注入。")
# ==========================================

# 现在可以安全导入 whisperx 了
import whisperx

def patch_whisperx():
    # 定位 whisperx 库文件位置
    try:
        asr_file = os.path.join(os.path.dirname(whisperx.__file__), "asr.py")
    except NameError:
        # Fallback if __file__ is somehow not accessible, though unlikely after import
        import inspect
        asr_file = os.path.join(os.path.dirname(inspect.getfile(whisperx)), "asr.py")
        
    print(f"🔍 正在定位文件: {asr_file}")

    if not os.path.exists(asr_file):
        print("❌ 未找到 whisperx/asr.py，请确认环境已安装！")
        return

    with open(asr_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 目标代码行
    target_code = "default_asr_options = faster_whisper.transcribe.TranscriptionOptions(**default_asr_options)"
    
    # 替换为兼容代码
    patched_code = """
    # [VideoLingo 50FIX] 自动补全 missing arguments 以兼容 faster-whisper 1.1.0
    if "multilingual" not in default_asr_options: default_asr_options["multilingual"] = True
    if "hotwords" not in default_asr_options: default_asr_options["hotwords"] = None
    default_asr_options = faster_whisper.transcribe.TranscriptionOptions(**default_asr_options)
    """

    if target_code in content:
        new_content = content.replace(target_code, patched_code)
        with open(asr_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("✅ 修复成功！WhisperX 已兼容 faster-whisper 1.1.0")
    elif "[VideoLingo 50FIX]" in content:
        print("✅ 已经修复过了，无需重复操作。")
    else:
        print("⚠️ 未找到目标代码行，可能是 whisperx 版本差异，请手动检查。")

if __name__ == "__main__":
    patch_whisperx()