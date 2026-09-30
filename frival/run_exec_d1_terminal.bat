@echo off
title Frival EXEC-D1 Terminal Execution (DEMO account)
setlocal
cd /d "%~dp0"

set "PYTHON=C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    pause
    exit /b 1
)

echo ============================================================
echo   Frival EXEC-D1   Terminal Execution Monitor (DEMO)
echo   Account: 7409623 ^| FPMarketsSC-Demo ^| $5,000 demo money
echo   Entry: quote in zone -^> market now; else pending 10 min
echo         from signal time; no touch -^> EXPIRED_UNFILLED.
echo   Pairs: EURUSD GBPUSD USDCHF USDCAD
echo   AUTHORIZED 2026-09-29. Legacy paper fills are SKIPPED.
echo   Run ALONGSIDE run_daily.bat (signals) - keep both open.
echo   Emergency stop: delete frival\data\emergency_stop.txt to
echo         resume after it is created.
echo ============================================================
echo.

REM    Auto-restart wrapper (bounded)   mirrors run_daily.bat   
set /a STRIKES=0
set /a MAX_STRIKES=5

:LOOP
"%PYTHON%" -u execution_bot\run_exec_d1_terminal.py 2>"%~dp0exec_d1_stderr.log"
set ERR=%ERRORLEVEL%

if %ERR%==0 (
    echo.
    echo [exec_d1] exited cleanly (code 0)   stopping wrapper.
    pause
    exit /b 0
)

echo.
echo [ERROR] EXEC-D1 monitor exited with code %ERR%
echo [ERROR] stderr saved to exec_d1_stderr.log   READ THIS FILE
echo         before assuming the cause.
set /a STRIKES+=1
echo [ERROR] restart %STRIKES% / %MAX_STRIKES%

if %STRIKES% geq %MAX_STRIKES% (
    echo [ERROR] Too many consecutive crashes   giving up. Check the log.
    pause
    exit /b 1
)

echo [exec_d1] restarting in 10s...
timeout /t 10 /nobreak >nul
goto LOOP