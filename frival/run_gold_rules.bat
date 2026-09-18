@echo off
title Gold Rules Engine — XAUUSD (LIVE)
setlocal
cd /d "%~dp0\gold_rules"

set "PYTHON=C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    pause
    exit /b 1
)

echo ============================================================
echo   Gold Rules Engine — XAUUSD (EXP-2026-03-RULEENGINE)
echo   Mode: LIVE (0.01 lot, $25 risk, $50 daily cap, 1 position)
echo   Auto-restarts after unexpected exits (max 5 in a row).
echo   NOTE: Manual XAUUSD trading is NOT allowed while this runs.
echo ============================================================
echo.

REM ── Auto-restart wrapper (bounded) ──────────────────────────────
REM The engine loop already self-heals Python-side. A crash at the MT5
REM native layer produces NO Python traceback (observed 2026-09-18).
REM This wrapper restarts quickly while halting on persistent failure
REM so a broken engine cannot loop silently forever.
set /a STRIKES=0
set /a MAX_STRIKES=5

:LOOP
"%PYTHON%" -u run_gold_rules.py 2>"%~dp0gold_rules\engine_stderr.log"
set ERR=%ERRORLEVEL%

if %ERR%==0 (
    echo.
    echo [gold] engine exited cleanly (code 0) — stopping wrapper.
    pause
    exit /b 0
)

echo.
echo [ERROR] Engine exited with code %ERR%
echo [ERROR] stderr saved to gold_rules\engine_stderr.log — READ THIS FILE
echo         before assuming the cause. The Python traceback (if any) lives there.
set /a STRIKES+=1
echo [ERROR] restart %STRIKES% / %MAX_STRIKES%

if %STRIKES% geq %MAX_STRIKES% (
    echo [ERROR] Too many consecutive crashes — giving up. Check the log.
    pause
    exit /b 1
)

echo [gold] restarting in 10s...
timeout /t 10 /nobreak >nul
goto LOOP