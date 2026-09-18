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
echo   Frival Daily Pipeline — Scheduler Mode ^(24/7 rolling^)
echo   Pairs: EURUSD GBPUSD USDCHF USDCAD EURUSD_AGNOSTIC
echo   Window: 02:01-16:01 Panama ^(UTC-5^) — London/NY session,
echo           the exact window the models were calibrated on.
echo   Leave open: it rolls over to the next day automatically.
echo   Auto-restarts after unexpected exits (max 5 in a row).
echo ============================================================
echo.

REM ── Auto-restart wrapper (bounded) — mirrors run_gold_rules.bat ──
set /a STRIKES=0
set /a MAX_STRIKES=5

:LOOP
"%PYTHON%" -u run_daily_scheduler.py 2>"%~dp0scheduler_stderr.log"
set ERR=%ERRORLEVEL%

if %ERR%==0 (
    echo.
    echo [scheduler] exited cleanly (code 0) — stopping wrapper.
    pause
    exit /b 0
)

echo.
echo [ERROR] Scheduler exited with code %ERR%
echo [ERROR] stderr saved to scheduler_stderr.log — READ THIS FILE
echo         before assuming the cause.
set /a STRIKES+=1
echo [ERROR] restart %STRIKES% / %MAX_STRIKES%

if %STRIKES% geq %MAX_STRIKES% (
    echo [ERROR] Too many consecutive crashes — giving up. Check the log.
    pause
    exit /b 1
)

echo [scheduler] restarting in 10s...
timeout /t 10 /nobreak >nul
goto LOOP