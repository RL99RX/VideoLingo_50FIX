import os
import warnings
import time
import subprocess
import torch
import whisperx
import librosa
from rich import print as rprint
from core.utils import *

warnings.filterwarnings("ignore")
MODEL_DIR = load_key("model_dir")

@except_handler("failed to check hf mirror", default_return=None)
def check_hf_mirror():
    mirrors = {'Official': 'huggingface.co', 'Mirror': 'hf-mirror.com'}
    fastest_url = f"https://{mirrors['Official']}"
    best_time = float('inf')
    rprint("[cyan]🔍 Checking HuggingFace mirrors...[/cyan]")
    for name, domain in mirrors.items():
        if os.name == 'nt':
            cmd = ['ping', '-n', '1', '-w', '3000', domain]
        else:
            cmd = ['ping', '-c', '1', '-W', '3', domain]
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        response_time = time.time() - start
        if result.returncode == 0:
            if response_time < best_time:
                best_time = response_time
                fastest_url = f"https://{domain}"
            rprint(f"[green]✓ {name}:[/green] {response_time:.2f}s")
    if best_time == float('inf'):
        rprint("[yellow]⚠️ All mirrors failed, using default[/yellow]")
    rprint(f"[cyan]🚀 Selected mirror:[/cyan] {fastest_url} ({best_time:.2f}s)")
    return fastest_url

@except_handler("WhisperX processing error:")
def transcribe_audio(raw_audio_file, vocal_audio_file, start, end):
    os.environ['HF_ENDPOINT'] = check_hf_mirror()
    WHISPER_LANGUAGE = load_key("whisper.language")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    rprint(f"🚀 Starting WhisperX using device: {device} ...")
    
    if device == "cuda":
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
        # --- ⚖️ 显存策略调整 (用户自定义 Batch 12) ---
        if gpu_mem > 14:
            # 16G 显存：用户指定 12，追求速度与稳定性的平衡
            batch_size = 12 
        elif gpu_mem > 7:
            batch_size = 6
        elif gpu_mem > 5:
            batch_size = 4
        else:
            batch_size = 2
            
        compute_type = "float16" if torch.cuda.is_bf16_supported() else "int8"
        rprint(f"[cyan]🎮 GPU memory:[/cyan] {gpu_mem:.2f} GB, [cyan]📦 Batch size:[/cyan] {batch_size}, [cyan]⚙️ Compute type:[/cyan] {compute_type}")
    else:
        batch_size = 1
        compute_type = "int8"
        rprint(f"[cyan]📦 Batch size:[/cyan] {batch_size}, [cyan]⚙️ Compute type:[/cyan] {compute_type}")
    
    rprint(f"[green]▶️ Starting WhisperX for segment {start:.2f}s to {end:.2f}s...[/green]")
    
    # ------------------------------------------------------
    # 🔓 恢复动态读取 Config
    # ------------------------------------------------------
    if WHISPER_LANGUAGE == 'zh':
        model_name = "Huan69/Belle-whisper-large-v3-zh-punct-fasterwhisper"
        local_model = os.path.join(MODEL_DIR, "Belle-whisper-large-v3-zh-punct-fasterwhisper")
    else:
        # 这里恢复读取配置文件，不再强制锁死。
        # 请确保你在 config.yaml 或前端设置中选择了 'large-v3'
        model_name = load_key("whisper.model")
        local_model = os.path.join(MODEL_DIR, model_name)
        
    if os.path.exists(local_model):
        rprint(f"[green]📥 Loading local WHISPER model:[/green] {local_model} ...")
        model_name = local_model
    else:
        rprint(f"[green]📥 Using WHISPER model from HuggingFace:[/green] {model_name} ...")

    # ------------------------------------------------------
    # 🛡️ 国象专用 Prompt (V3 终极微调版)
    # ------------------------------------------------------
    # 针对性修复：
    # 1. "rare lines" -> 明确写入 lines 搭配
    # 2. "crushing move" -> 明确写入 crushing 搭配，防止 crunchy
    # 3. "develop" -> 强化动词概念
    chess_prompt = (
        "Chess commentary. Sides: White, Black. "
        "Moves: Knight c3, Bishop b5, a5, b5, c5, d4, e4, f3, g2, h1. "
        "Terms: checkmate, castling, en passant, zugzwang, blunder. "
        "Phrases: rare lines, main lines, crushing move, crushing advantage, "
        "develop pieces, attack, defend, sacrifice, counterplay."
    )
    
    # VAD 参数：严格门槛，过滤噪音
    vad_options = {"vad_onset": 0.600, "vad_offset": 0.200}
    
    asr_options = {
        "temperatures": [0], 
        "initial_prompt": chess_prompt,
        # 核心防复读参数：适用于 V3 和 Turbo
        "repetition_penalty": 1.2,          
        "condition_on_previous_text": False 
    }
    
    whisper_language = None if 'auto' in WHISPER_LANGUAGE else WHISPER_LANGUAGE
    rprint("[bold yellow] You can ignore warning of `Model was trained with torch 1.10.0+cu102, yours is 2.0.0+cu118...`[/bold yellow]")
    
    # 加载模型
    model = whisperx.load_model(model_name, device, compute_type=compute_type, language=whisper_language, vad_options=vad_options, asr_options=asr_options, download_root=MODEL_DIR)

    def load_audio_segment(audio_file, start, end):
        audio, _ = librosa.load(audio_file, sr=16000, offset=start, duration=end - start, mono=True)
        return audio

    raw_audio_segment = load_audio_segment(raw_audio_file, start, end)
    vocal_audio_segment = load_audio_segment(vocal_audio_file, start, end)
    
    # -------------------------
    # 1. transcribe raw audio
    # -------------------------
    transcribe_start_time = time.time()
    rprint("[bold green]Note: You will see Progress if working correctly ↓[/bold green]")
    
    result = model.transcribe(raw_audio_segment, batch_size=batch_size, print_progress=True)
    
    transcribe_time = time.time() - transcribe_start_time
    rprint(f"[cyan]⏱️ time transcribe:[/cyan] {transcribe_time:.2f}s")

    del model
    torch.cuda.empty_cache()

    update_key("whisper.language", result['language'])
    if result['language'] == 'zh' and WHISPER_LANGUAGE != 'zh':
        raise ValueError("Please specify the transcription language as zh and try again!")

    # -------------------------
    # 2. align by vocal audio
    # -------------------------
    align_start_time = time.time()
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    result = whisperx.align(result["segments"], model_a, metadata, vocal_audio_segment, device, return_char_alignments=False)
    align_time = time.time() - align_start_time
    rprint(f"[cyan]⏱️ time align:[/cyan] {align_time:.2f}s")

    torch.cuda.empty_cache()
    del model_a

    for segment in result['segments']:
        segment['start'] += start
        segment['end'] += start
        for word in segment['words']:
            if 'start' in word:
                word['start'] += start
            if 'end' in word:
                word['end'] += start
    return result