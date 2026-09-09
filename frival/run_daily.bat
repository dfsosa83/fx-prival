@echo off
title Frival Daily Pipeline
setlocal
cd /d "%~dp0"

set "PYTHON=C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    pause
    exit /b 1
)

echo ============================================================
echo   Frival Daily Pipeline — Scheduler Mode
echo   Pairs: EURUSD GBPUSD USDCHF USDCAD EURUSD_AGNOSTIC
echo   Window: 08:01-11:01 AM Panama ^(UTC-5^)
echo ============================================================
echo.

"%PYTHON%" -u run_daily_scheduler.py
set ERR=%ERRORLEVEL%

if %ERR% neq 0 (
    echo.
    echo [ERROR] Scheduler exited with code %ERR%
)
pause