import os
import sys
import torch
import gc
from rich.console import Console
from rich import print as rprint
from demucs.pretrained import get_model
from demucs.audio import save_audio
from demucs.api import Separator
from demucs.apply import BagOfModels
from typing import Optional
from core.utils.models import *

def check_rtx50_compatibility():
    """检查并设置RTX 50系列GPU的兼容性环境变量"""
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            
            if "RTX 50" in str(name).upper():
                rprint(f"[yellow]🔥 检测到 RTX 50 系列 GPU: {name}，强制启用 Blackwell 架构兼容模式...[/yellow]")
                os.environ['TORCH_CUDA_ARCH_LIST'] = '9.0+PTX'
                os.environ['NVIDIA_ALLOW_UNSUPPORTED_ARCHS'] = 'true'
                return True
        
        pynvml.nvmlShutdown()
    except ImportError:
        rprint("[yellow]⚠️ 缺少 nvidia-ml-py 库，跳过 RTX 50 硬件检测。[/yellow]")
    except Exception as e:
        rprint(f"[yellow]⚠️ GPU 检测遇到轻微问题 (不影响运行): {e}[/yellow]")
    return False

class PreloadedSeparator(Separator):
    def __init__(self, model: BagOfModels, device="cpu", shifts: int = 1, overlap: float = 0.25,
                 split: bool = True, segment: Optional[int] = None, jobs: int = 0):
        self._model, self._audio_channels, self._samplerate = model, model.audio_channels, model.samplerate
        self.update_parameter(device=device, shifts=shifts, overlap=overlap, split=split,
                            segment=segment, jobs=jobs, progress=True, callback=None, callback_arg=None)

def demucs_audio():
    console = Console()
    
    # 1. 兼容性检查
    check_rtx50_compatibility()
    
    # 2. 打印详细的 PyTorch 版本信息 (用于调试)
    cuda_version = torch.version.cuda if torch.version.cuda else "None"
    rprint(f"[white]ℹ️ PyTorch Version: {torch.__version__} | CUDA Version: {cuda_version}[/white]")

    # 3. 设备检测
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        rprint(f"[bold green]🚀 CUDA 加速已开启！使用设备: {gpu_name}[/bold green]")
    else:
        device = "cpu"
        rprint("[bold red]🐢 PyTorch 未识别到 GPU，正在使用 CPU 慢速模式！[/bold red]")
        rprint(f"[yellow]   当前 PyTorch 版本: {torch.__version__} (如果包含 'cpu' 字样说明版本不对)[/yellow]")

    if os.path.exists(_VOCAL_AUDIO_FILE) and os.path.exists(_BACKGROUND_AUDIO_FILE):
        rprint(f"[yellow]⚠️ {_VOCAL_AUDIO_FILE} 和 {_BACKGROUND_AUDIO_FILE} 已存在，跳过 Demucs 处理。[/yellow]")
        return
    
    os.makedirs(_AUDIO_DIR, exist_ok=True)
    
    console.print("🤖 Loading <htdemucs> model...")
    model = get_model('htdemucs')
    
    separator = PreloadedSeparator(model=model, device=device, shifts=1, overlap=0.25)
    
    console.print(f"🎵 Separating audio on {device.upper()}...")
    _, outputs = separator.separate_audio_file(_RAW_AUDIO_FILE)
    
    kwargs = {"samplerate": model.samplerate, "bitrate": 128, "preset": 2, 
             "clip": "rescale", "as_float": False, "bits_per_sample": 16}
    
    console.print("🎤 Saving vocals track...")
    save_audio(outputs['vocals'].cpu(), _VOCAL_AUDIO_FILE, **kwargs)
    
    console.print("🎹 Saving background music...")
    background = sum(audio for source, audio in outputs.items() if source != 'vocals')
    save_audio(background.cpu(), _BACKGROUND_AUDIO_FILE, **kwargs)
    
    del outputs, background, model, separator
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    console.print("[green]✨ Audio separation completed![/green]")

if __name__ == "__main__":
    demucs_audio()