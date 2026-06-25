#!/bin/bash

# Path to the virtual environment
VENV_DIR=".venv"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install PyInstaller if not present
echo "Installing PyInstaller..."
pip install pyinstaller

# Run PyInstaller with the spec file
echo "Running PyInstaller..."
pyinstaller --noconfirm video_analyzer.spec

# Verify if PyInstaller completed successfully
if [ $? -ne 0 ]; then
    echo "[ERROR] Error occurred during executable creation."
    exit 1
fi

# Copy settings folder to the distribution folder
echo "Copying configuration folders..."
mkdir -p dist/VideoAnalyzer
cp -r settings dist/VideoAnalyzer/settings
if [ -d "secrets" ]; then
    cp -r secrets dist/VideoAnalyzer/secrets
fi

echo ""
echo "🎉 Operation completed successfully!"
echo "The executable is located in: dist/VideoAnalyzer/VideoAnalyzer"
echo ""

