@echo off
echo ====================================================
echo    Iniciando AsistIA V5 - PodiaAI Clinic
echo ====================================================

:: Inicializa variables para Conda
set CONDA_ENV=podia-pos
call conda activate %CONDA_ENV%

if %errorlevel% neq 0 (
    echo [ERROR] No se pudo activar el entorno conda "%CONDA_ENV%".
    echo Por favor, cambie el nombre del entorno en este archivo si es diferente.
    pause
    exit /b 1
)

echo [OK] Entorno conda '%CONDA_ENV%' activado.
echo [INFO] Iniciando servidor de aplicacion local...

python app.py

if %errorlevel% neq 0 (
    echo [ERROR] La aplicacion se cerro con errores.
    pause
) else (
    echo [OK] Aplicacion finalizada correctamente.
)
