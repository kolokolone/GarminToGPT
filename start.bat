@echo off
setlocal EnableExtensions EnableDelayedExpansion

chcp 65001 >nul
cd /d "%~dp0"
set "PAUSE_ON_EXIT=1"
if /I "%~1"=="--no-pause" set "PAUSE_ON_EXIT=0"

echo GarminToGPT - lancement local integral Windows
echo Dossier: %CD%
echo.

call :require_command uv "Installe uv depuis https://docs.astral.sh/uv/"
if errorlevel 1 exit /b 1

call :require_command npm "Installe Node.js 24 depuis https://nodejs.org/"
if errorlevel 1 exit /b 1

if not exist "config\app.yaml" (
  echo [ERREUR] config\app.yaml est introuvable.
  echo Copie config\app.example.yaml vers config\app.yaml puis adapte la configuration.
  exit /b 1
)

if not exist "logs" mkdir "logs"
if not exist "runtime" mkdir "runtime"
if not exist "runtime\pids" mkdir "runtime\pids"
if not exist "data" mkdir "data"
if not exist "data\garmin" mkdir "data\garmin"

set "GARMINTOGPT_ENV=local"
set "GARMINTOGPT_CONFIG=%CD%\config\app.yaml"
set "GARMINTOGPT_LOG_LEVEL=INFO"

echo [1/4] Installation/verifier des dependances Python...
uv sync
if errorlevel 1 (
  echo [ERREUR] uv sync a echoue.
  call :pause_if_needed
  exit /b 1
)

echo.
echo [2/4] Installation/verifier des dependances frontend...
if not exist "frontend\node_modules" (
  call npm --prefix "frontend" install
  if errorlevel 1 (
    echo [ERREUR] npm install a echoue.
    call :pause_if_needed
    exit /b 1
  )
) else (
  echo node_modules deja present.
)

echo.
echo [3/4] Build statique Next.js servi par FastAPI...
call npm --prefix "frontend" run build
if errorlevel 1 (
  echo [ERREUR] Le build frontend a echoue.
  call :pause_if_needed
  exit /b 1
)

if not exist "frontend\out\index.html" (
  echo [ERREUR] frontend\out\index.html est absent apres le build.
  call :pause_if_needed
  exit /b 1
)

echo.
echo [4/4] Demarrage FastAPI en mode local integral...
echo UI + API : http://127.0.0.1:8000
echo Connexion : http://127.0.0.1:8000/connexion
echo Tests : http://127.0.0.1:8000/tests
echo.
echo Le backend controle ensuite MCP et Cloudflare depuis l'UI.
echo Appuie sur Ctrl+C pour arreter GarminToGPT.
echo.

uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="-1" (
  echo GarminToGPT a ete arrete par interruption locale ^(Ctrl+C, fermeture de fenetre ou arret du processus^).
) else if "%EXIT_CODE%"=="0" (
  echo GarminToGPT s'est arrete normalement.
) else (
  echo GarminToGPT s'est arrete avec le code %EXIT_CODE%.
  echo Si ce n'etait pas volontaire, copie les lignes au-dessus de ce message pour diagnostiquer l'erreur.
)
call :pause_if_needed
exit /b %EXIT_CODE%

:require_command
where %~1 >nul 2>nul
if errorlevel 1 (
  echo [ERREUR] Commande requise introuvable: %~1
  echo %~2
  call :pause_if_needed
  exit /b 1
)
exit /b 0

:pause_if_needed
if "%PAUSE_ON_EXIT%"=="1" pause
exit /b 0
