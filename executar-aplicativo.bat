@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo O ambiente ainda nao foi configurado.
    echo Execute primeiro o arquivo instalar-e-iniciar.bat.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
endlocal
