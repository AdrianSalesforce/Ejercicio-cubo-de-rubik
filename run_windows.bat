@echo off
chcp 65001 >nul
cd /d "%~dp0"
python main.py
if errorlevel 1 (
  echo.
  echo No se pudo iniciar. Comprueba que Python 3.10 o superior está instalado y en PATH.
  pause
)
