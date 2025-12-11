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
:: 使用 --no-project 确保 install.py 可以自由修改环境而不受 lock 文件限制
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
:: 关键！必须加 --no-project，否则 uv 会试图把 torch 降级回去！
if exist "fix_cudnn.py" uv run --no-project python fix_cudnn.py
if exist "fix_whisperx.py" uv run --no-project python fix_whisperx.py

:: 4. Start
echo.
echo [INFO] Starting VideoLingo...
set HF_ENDPOINT=https://hf-mirror.com
:: 同样加 --no-project，保持当前“魔改”后的环境状态运行
uv run --no-project streamlit run st.py

pause