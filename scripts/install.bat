@echo off
REM Fresh install on Windows: venv, deps, .env seed, schema bootstrap. Idempotent.
REM Run from the repo root:  scripts\install.bat
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."

where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 ( echo [ERR] Python ^>= 3.11 not found on PATH & exit /b 2 )
  set "PYLAUNCH=python"
) else (
  set "PYLAUNCH=py -3"
)

if not exist ".venv\" (
  echo [==] creating virtualenv
  %PYLAUNCH% -m venv .venv
  if errorlevel 1 ( echo [ERR] venv creation failed & exit /b 1 )
)
set "PY=.venv\Scripts\python.exe"

echo [==] upgrading pip
"%PY%" -m pip install --quiet --upgrade pip
if errorlevel 1 ( echo [ERR] pip upgrade failed & exit /b 1 )

echo [==] installing gateway + dependencies
"%PY%" -m pip install --quiet -e ".[gateway]"
if errorlevel 1 ( echo [ERR] dependency install failed & exit /b 1 )

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  findstr /b /c:"CLAUDE_GATEWAY_DB=postgres" ".env" >nul
  if not errorlevel 1 (
    echo [!!] wrote .env - set CLAUDE_GATEWAY_ADMIN_TOKEN + DATABASE_URL, then re-run
    exit /b 1
  )
  echo [!!] wrote a starter .env ^(memory mode^) - set CLAUDE_GATEWAY_ADMIN_TOKEN before running
)

REM Apply schema only for the postgres backend.
findstr /b /c:"CLAUDE_GATEWAY_DB=postgres" ".env" >nul
if not errorlevel 1 (
  echo [==] applying database schema
  "%PY%" -c "import asyncio; from gateway.shared.config import GatewaySettings; from gateway.shared.db.engine import Database; s=GatewaySettings(); db=Database(s.database_url); asyncio.run(db.create_all())"
  if errorlevel 1 ( echo [ERR] schema bootstrap failed & exit /b 1 )
)

echo [OK] install complete - start with: scripts\run.bat
endlocal
