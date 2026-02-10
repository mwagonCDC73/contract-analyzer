@echo off
echo Installing dependencies for Contract Analyzer...
echo.

cd /d "%~dp0"

REM --- Backend (FastAPI) ---
echo [1/2] Installing backend dependencies...
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r api\requirements.txt
echo Backend dependencies installed.
echo.

REM --- Frontend (Next.js) ---
echo [2/2] Installing frontend dependencies...
if not exist "web\node_modules" (
    cd web
    npm install
    cd ..
) else (
    echo Frontend node_modules already exists. Run "cd web && npm install" to update.
)

echo.
echo ========================================
echo Installation complete! Starting services...
echo ========================================
echo.

REM Launch backend in current tab, frontend in a new tab (requires Windows Terminal)
where wt >nul 2>nul
if %errorlevel%==0 (
    echo Starting frontend in a new tab...
    wt -w 0 new-tab --title "Frontend" cmd /k "cd /d %~dp0web && npm run dev"
    echo Starting backend in this tab...
    cd /d %~dp0api
    call %~dp0venv\Scripts\activate.bat
    uvicorn main:app --reload
) else (
    echo Windows Terminal not found. Starting services in separate windows...
    start "Frontend" cmd /k "cd /d %~dp0web && npm run dev"
    echo Starting backend in this window...
    cd /d %~dp0api
    call %~dp0venv\Scripts\activate.bat
    uvicorn main:app --reload
)
