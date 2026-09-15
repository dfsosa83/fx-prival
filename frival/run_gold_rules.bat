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
echo   Runs continuously while this window stays open.
echo   NOTE: Manual XAUUSD trading is NOT allowed while this runs.
echo ============================================================
echo.

"%PYTHON%" -u run_gold_rules.py
set ERR=%ERRORLEVEL%

if %ERR% neq 0 (
    echo.
    echo [ERROR] Engine exited with code %ERR%
)
pause