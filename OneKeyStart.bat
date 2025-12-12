@echo off
setlocal
chcp 65001 >nul
title VideoLingo Launcher

echo ========================================================
echo        VideoLingo Launcher (Universal Mode)
echo ========================================================
echo.

:: 1. Check uv
echo [INFO] Checking uv...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] uv not found, installing...
    python -m pip install uv
)

:: 2. Config & Install
echo [INFO] Environment Check...
:: === 优化点在这里 ===
:: 以前是: uv run install.py (慢，因为要先加载虚拟环境)
:: 现在是: python install.py (快，直接用系统python运行配置脚本)
uv run --no-project install.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed.
    pause
    exit /b
)

:: 3. Patches
echo.
echo [INFO] Checking patches...
:: 补丁仍然需要用 uv run，因为它们依赖 venv 里的库
if exist "fix_cudnn.py" uv run python fix_cudnn.py
if exist "fix_whisperx.py" uv run python fix_whisperx.py

:: 4. Start
echo.
echo [INFO] Starting VideoLingo...
set HF_ENDPOINT=https://hf-mirror.com
:: 启动主程序必须用 uv run
uv run streamlit run st.py

pause