@echo off
setlocal
cd /d "%~dp0"
title Ferramentas de Arquivo - Instalação

echo ================================================
echo       Ferramentas de Arquivo
echo       Preparando a primeira execucao
echo ================================================
echo.
echo Este processo precisa de Python 3.13 ou superior
echo instalado no Windows e de uma conexao com a internet.
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher nao encontrado.
    echo Instale Python 3.13 em https://www.python.org/downloads/windows/
    echo Durante a instalacao, habilite o Python Launcher.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Criando ambiente isolado...
    py -3.13 -m venv .venv
    if errorlevel 1 (
        echo Nao foi possivel criar o ambiente Python.
        echo Verifique se Python 3.13 esta instalado.
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
    echo O aplicativo encerrou com erro. Copie a mensagem acima para solicitar ajuda.
    pause
)
endlocal
