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
:: --prerelease=allow 允许下载 nightly 版 torch
uv sync --prerelease=allow

echo [INFO] 检查 Spacy 模型...
if not exist ".venv\Lib\site-packages\zh_core_web_sm" (
    uv run python -m spacy download zh_core_web_sm
)

:: RTX 50 环境变量
set TORCHAUDIO_USE_BACKEND_DISPATCHER=1
set TORCH_CUDA_ARCH_LIST=7.0 7.5 8.0 8.6 8.9 9.0+PTX
set NVIDIA_ALLOW_UNSUPPORTED_ARCHS=true

echo.
echo [SUCCESS] 启动 VideoLingo...
uv run streamlit run st.py
pause