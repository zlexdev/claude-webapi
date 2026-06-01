@echo off
REM Start the gateway on Windows. Run from anywhere:  scripts\run.bat
setlocal
cd /d "%~dp0\.."
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" ( echo [ERR] venv missing - run scripts\install.bat first & exit /b 1 )
if not exist ".env" ( echo [ERR] .env missing - copy .env.example to .env & exit /b 1 )
echo [==] starting claude-gateway
"%PY%" -m gateway
endlocal
