@echo off
chcp 65001 >nul
title VideoLingo UV Launcher (RTX 50 Fixed)

echo [INFO] 正在检查 UV...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未安装 uv，正在安装...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
)

echo [INFO] 锁定 Python 3.11...
uv python pin 3.11

echo [INFO] 极速同步环境...
uv sync --prerelease=allow

:: ---------------------------------------------------------
:: [核心修复] 强制设置 HuggingFace 镜像
:: 这行命令必须在启动 python 之前执行，否则 faster-whisper 会无视它
set HF_ENDPOINT=https://hf-mirror.com
:: ---------------------------------------------------------

:: RTX 50 环境变量
set TORCHAUDIO_USE_BACKEND_DISPATCHER=1
set TORCH_CUDA_ARCH_LIST=7.0 7.5 8.0 8.6 8.9 9.0+PTX
set NVIDIA_ALLOW_UNSUPPORTED_ARCHS=true

echo.
echo [SUCCESS] 启动 VideoLingo (Mirror Mode)...
echo.

uv run streamlit run st.py --server.fileWatcherType none

pause