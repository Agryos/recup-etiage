@echo off
rem Lance la WebUI de Recup-Etiage.
rem Usage : double-cliquer sur run_webui.bat
rem
rem Pre-requis : le venv doit etre cree et les dependances installees
rem (voir install.bat + requirements-webui.txt).

cd /d "%~dp0"

rem Charge le .env (proxy eventuel) via python-dotenv au demarrage de l'app.

if exist "venv\Scripts\python.exe" (
    set "PYTHON=venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo Lancement de la WebUI sur http://127.0.0.1:8000 ...
echo Appuyez sur Ctrl+C pour arreter.
"%PYTHON%" -m webui.app
pause
