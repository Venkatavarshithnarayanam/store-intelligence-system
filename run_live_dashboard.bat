@echo off
REM Live Dashboard Quick Start Script for Windows
REM Runs the complete end-to-end demo in one command

setlocal enabledelayedexpansion

set STORE_ID=STORE_BLR_002
set API_URL=http://localhost:8000
set API_PORT=8000

echo.
echo ==========================================
echo STORE INTELLIGENCE - LIVE DASHBOARD
echo ==========================================
echo.

echo Starting API server on port %API_PORT%...
start "Store Intelligence API" python -m uvicorn app.main:app --reload --port %API_PORT%
timeout /t 3 /nobreak

echo.
echo Generating test events...
python pipeline/run.py --num-frames 100 --output demo_events.jsonl

echo.
echo Ingesting events into API...
curl -X POST %API_URL%/events/ingest ^
  -H "Content-Type: application/json" ^
  -d @demo_events.jsonl

echo.
echo ==========================================
echo LIVE DASHBOARD - CHOOSE FORMAT
echo ==========================================
echo.
echo 1. Terminal Dashboard (ASCII art)
echo 2. Web Dashboard (HTML in browser)
echo 3. JSON Dashboard (API endpoint)
echo 4. Exit
echo.

set /p choice="Select option (1-4): "

if "%choice%"=="1" (
    echo.
    echo === TERMINAL DASHBOARD ===
    curl -s %API_URL%/stores/%STORE_ID%/dashboard/terminal
    echo.
    set /p refresh="Auto-refresh? (y/n): "
    if "!refresh!"=="y" (
        echo Refreshing every 5 seconds (Ctrl+C to stop)...
        :refresh_loop
        cls
        curl -s %API_URL%/stores/%STORE_ID%/dashboard/terminal
        timeout /t 5 /nobreak
        goto refresh_loop
    )
) else if "%choice%"=="2" (
    echo.
    echo === WEB DASHBOARD ===
    echo Opening in browser: %API_URL%/stores/%STORE_ID%/dashboard.html
    start %API_URL%/stores/%STORE_ID%/dashboard.html
) else if "%choice%"=="3" (
    echo.
    echo === JSON DASHBOARD ===
    curl -s %API_URL%/stores/%STORE_ID%/dashboard
) else (
    echo Exiting...
)

echo.
echo ==========================================
echo Dashboard session ended
echo ==========================================
echo.
echo Done!
pause
