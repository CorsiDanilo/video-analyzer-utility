@echo off
REM Path to the virtual environment
set VENV_DIR=%~dp0.venv

REM Activate the virtual environment
call "%VENV_DIR%\Scripts\activate"

REM Install PyInstaller if not present
echo Installing PyInstaller...
"%VENV_DIR%\Scripts\python.exe" -m pip install pyinstaller

REM Run PyInstaller with the spec file
echo Running PyInstaller...
"%VENV_DIR%\Scripts\python.exe" -m PyInstaller --noconfirm video_analyzer.spec

REM Verify if PyInstaller completed successfully
if errorlevel 1 (
    echo [ERROR] Error occurred during executable creation.
    pause
    exit /b 1
)

REM Copy settings folder to the distribution folder
echo Copying configuration folders...
xcopy /E /I /Y "settings" "dist\VideoAnalyzer\settings"
if exist "secrets" xcopy /E /I /Y "secrets" "dist\VideoAnalyzer\secrets"

echo.
echo 🎉 Operation completed successfully!
echo The executable is located in: dist\VideoAnalyzer\VideoAnalyzer.exe
echo.
pause

