@echo off
setlocal
cd /d "%~dp0"

set "PYTHONPATH=%~dp0src"
set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "ROOT_VENV=%~dp0.venv\Scripts\python.exe"

if exist "%BUNDLED_PYTHON%" (
    "%BUNDLED_PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
) else if exist "%ROOT_VENV%" (
    "%ROOT_VENV%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
) else (
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
)
