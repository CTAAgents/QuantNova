@echo off
REM 启动文件监控自动 Git 推送脚本
REM 此脚本会在后台启动 auto_git_push.py

setlocal

set REPO_DIR=%~dp0..
set SCRIPT_DIR=%~dp0
set PYTHON_EXE=C:\Program Files\Python312\python.exe
set SCRIPT_PATH=%SCRIPT_DIR%auto_git_push.py
set LOG_FILE=%REPO_DIR%\.workbuddy\memory\auto_git_push.log

REM 创建日志目录
if not exist "%REPO_DIR%\.workbuddy\memory" mkdir "%REPO_DIR%\.workbuddy\memory"

REM 检查是否已在运行
tasklist /FI "WINDOWTITLE eq auto_git_push*" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] auto_git_push.py 已在运行，跳过启动 >> "%LOG_FILE%"
    exit /b 0
)

REM 启动脚本
echo [%date% %time%] 启动 auto_git_push.py... >> "%LOG_FILE%"
start "auto_git_push" /B "%PYTHON_EXE%" "%SCRIPT_PATH%" --debounce 5 --branch main >> "%LOG_FILE%" 2>&1

REM 等待几秒检查是否启动成功
timeout /t 3 /nobreak >NUL
tasklist /FI "WINDOWTITLE eq auto_git_push*" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] auto_git_push.py 启动成功 >> "%LOG_FILE%"
) else (
    echo [%date% %time%] auto_git_push.py 启动失败 >> "%LOG_FILE%"
)

endlocal
