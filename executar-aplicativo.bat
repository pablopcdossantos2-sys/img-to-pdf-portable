@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo O ambiente ainda nao foi configurado.
    echo Execute primeiro o arquivo instalar-e-iniciar.bat.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -c "import sys, PySide6, pypdf, PIL, cryptography, reportlab; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 (
    echo O ambiente virtual esta incompleto ou pode ter sido movido.
    echo Apague a pasta .venv e execute instalar-e-iniciar.bat novamente.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo Se a pasta do projeto foi movida, apague .venv e rode instalar-e-iniciar.bat.
    pause
)
endlocal
