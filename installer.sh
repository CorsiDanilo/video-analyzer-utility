#!/bin/bash

# Path to the virtual environment
VENV_DIR=".venv"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install PyInstaller if not present
echo "Installazione di PyInstaller..."
pip install pyinstaller

# Run PyInstaller with the spec file
echo "Avvio di PyInstaller..."
pyinstaller --noconfirm video_analyzer.spec

# Verify if PyInstaller completed successfully
if [ $? -ne 0 ]; then
    echo "[ERRORE] Errore durante la creazione dell'eseguibile."
    exit 1
fi

# Copy config and settings folders to the distribution folder
echo "Copia delle cartelle di configurazione..."
mkdir -p dist/VideoAnalyzer
cp -r config dist/VideoAnalyzer/config
cp -r settings dist/VideoAnalyzer/settings

echo ""
echo "🎉 Operazione completata con successo!"
echo "L'eseguibile si trova in: dist/VideoAnalyzer/VideoAnalyzer"
echo ""
