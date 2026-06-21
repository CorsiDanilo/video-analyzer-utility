@echo off
REM Path to the virtual environment
set VENV_DIR=%~dp0.venv

REM Activate the virtual environment
call "%VENV_DIR%\Scripts\activate"

REM Install PyInstaller if not present
echo Installazione di PyInstaller...
"%VENV_DIR%\Scripts\python.exe" -m pip install pyinstaller

REM Run PyInstaller with the spec file
echo Avvio di PyInstaller...
"%VENV_DIR%\Scripts\python.exe" -m PyInstaller --noconfirm video_analyzer.spec

REM Verify if PyInstaller completed successfully
if errorlevel 1 (
    echo [ERRORE] Errore durante la creazione dell'eseguibile.
    pause
    exit /b 1
)

REM Copy settings folder to the distribution folder
echo Copia delle cartelle di configurazione...
xcopy /E /I /Y "settings" "dist\VideoAnalyzer\settings"
if exist "secrets" xcopy /E /I /Y "secrets" "dist\VideoAnalyzer\secrets"

echo.
echo 🎉 Operazione completata con successo!
echo L'eseguibile si trova in: dist\VideoAnalyzer\VideoAnalyzer.exe
echo.
pause
