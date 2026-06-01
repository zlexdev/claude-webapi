@echo off
REM Pull + redeploy on Windows: git pull, reinstall, apply schema. Restart manually.
REM Note: no automatic health-gated rollback here (see scripts/update.sh for that);
REM on Windows, restart the process and re-check /health yourself.
setlocal
cd /d "%~dp0\.."
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" ( echo [ERR] venv missing - run scripts\install.bat first & exit /b 1 )

echo [==] recording current revision
git rev-parse HEAD > .last_deploy_rev 2>nul

echo [==] pulling latest
git pull --ff-only
if errorlevel 1 ( echo [ERR] git pull failed & exit /b 1 )

echo [==] reinstalling deps
"%PY%" -m pip install --quiet -e ".[gateway]"
if errorlevel 1 ( echo [ERR] dependency install failed & exit /b 1 )

findstr /b /c:"CLAUDE_GATEWAY_DB=postgres" ".env" >nul
if not errorlevel 1 (
  echo [==] applying schema
  "%PY%" -c "import asyncio; from gateway.shared.config import GatewaySettings; from gateway.shared.db.engine import Database; s=GatewaySettings(); db=Database(s.database_url); asyncio.run(db.create_all())"
)
echo [OK] update complete - restart scripts\run.bat and verify /health
endlocal
