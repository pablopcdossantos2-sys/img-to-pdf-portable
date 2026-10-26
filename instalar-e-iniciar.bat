@echo off
setlocal
cd /d "%~dp0"
title PDF Hub - Instalacao

echo ================================================
echo       PDF Hub
echo       Preparando a primeira execucao
echo ================================================
echo.
echo Este processo precisa de Python 3.11 ou superior
echo instalado no Windows e de uma conexao com a internet.
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher nao encontrado.
    echo Instale Python 3.11 ou superior em https://www.python.org/downloads/windows/
    echo Durante a instalacao, habilite o Python Launcher.
    pause
    exit /b 1
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 (
    echo A versao padrao de Python e antiga demais.
    echo Instale Python 3.11 ou superior e execute este arquivo novamente.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import PySide6, pypdf, PIL" >nul 2>nul
    if errorlevel 1 (
        echo O ambiente Python existente parece incompleto ou foi movido.
        echo Apague manualmente a pasta .venv e execute este instalador novamente.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Criando ambiente isolado...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Nao foi possivel criar o ambiente Python.
        echo Verifique se Python 3.11 ou superior esta instalado.
        pause
        exit /b 1
    )
)

echo [2/3] Instalando ou atualizando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Falha ao atualizar o pip.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Falha ao instalar as dependencias.
    echo Confira a conexao com a internet e tente novamente.
    pause
    exit /b 1
)

echo [3/3] Abrindo o aplicativo...
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo O aplicativo encerrou com erro.
    echo Se esta pasta foi movida, apague .venv e execute este instalador novamente.
    echo Copie a mensagem acima para solicitar ajuda.
    pause
)
endlocal
