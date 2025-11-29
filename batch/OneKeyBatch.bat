@echo off
cd /D "%~dp0"
:: 回退到项目根目录 VideoLingo_50FIX
cd ..

call conda activate videolingo

:: 【关键修改】设置 PYTHONPATH 为当前目录（也就是项目根目录）
:: 这样 Python 就能找到 'batch' 模块了
set PYTHONPATH=%cd%

echo Current PYTHONPATH: %PYTHONPATH%
echo Running Batch Processor...

call python batch\utils\batch_processor.py

:end
pause