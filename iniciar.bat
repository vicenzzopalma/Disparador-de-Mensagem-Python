@echo off
:: Script de inicialização automática para o RealezaSender
title RealezaSender Launcher
echo ====================================================
echo            INICIANDO REALEZASENDER
echo ====================================================
echo.

:: Verificar se o Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado! Por favor, instale o Python.
    echo Acesse https://www.python.org/downloads/ e certifique-se de marcar a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b
)

:: Criar ambiente virtual se nao existir
if not exist .venv (
    echo [1/3] Criando ambiente virtual Python (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b
    )
)

:: Ativar ambiente virtual e instalar dependencias
echo [2/3] Ativando ambiente virtual e verificando dependencias...
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias do requirements.txt.
    pause
    exit /b
)

:: Iniciar a interface Web e abrir no navegador
echo [3/3] Iniciando o servidor do aplicativo...
echo Servidor rodando em http://127.0.0.1:5005/
echo.

:: Abrir o navegador automaticamente
start http://127.0.0.1:5005/

:: Iniciar app do Flask
python WaSender_UI/app.py
pause
