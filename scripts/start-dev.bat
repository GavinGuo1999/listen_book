@echo off
setlocal

set "ROOT=%~dp0.."
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"

echo Starting Listen Book worker, backend and frontend...
echo.

pushd "%BACKEND%"
..\.venv\Scripts\alembic.exe upgrade head
if errorlevel 1 (
  popd
  echo Database migration failed. Development services were not started.
  exit /b 1
)
popd

start "Listen Book Worker" cmd /k "cd /d "%BACKEND%" && ..\.venv\Scripts\python.exe -m app.workers.jobs"
start "Listen Book Backend" cmd /k "cd /d "%BACKEND%" && ..\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000"
start "Listen Book Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev -- --host 127.0.0.1"

echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
echo.
echo Three command windows were opened. Keep them open while developing.

endlocal
