@echo off
title Frival Book Dashboard
setlocal
cd /d "%~dp0\dashboard"

set "PYTHON=C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe"
if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    pause
    exit /b 1
)

echo ============================================================
echo   Frival Book Dashboard — read-only portfolio visibility
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:3000  (opens automatically)
echo   Close this window to stop the dashboard.
echo ============================================================
echo.

REM 1) Start the FastAPI backend in this window
start "Dashboard Backend" cmd /k ""%PYTHON%" -m uvicorn --app-dir backend main:app --host 0.0.0.0 --port 8000"

REM 2) Give the backend a moment, then start the frontend
timeout /t 3 /nobreak >nul
start "Dashboard Frontend" cmd /k "cd /d "%cd%\frontend" && npm start"

REM 3) Open the browser once the frontend is up
timeout /t 7 /nobreak >nul
start http://localhost:3000

echo [OK] Dashboard launched. Two helper windows should now be open.
echo      Keep all windows running; close the helper windows to stop.
pause