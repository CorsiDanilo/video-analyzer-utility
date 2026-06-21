#!/bin/bash
# Windows Build Script (runs in Git Bash / WSL)

# Exit on error
set -e

echo "🪟 Setting up build environment for Windows..."

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment '.venv' not found."
    echo "Please create it using: python -m venv .venv"
    echo "And install dependencies: pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/Scripts/activate

# Run PyInstaller
echo "Running PyInstaller..."
pyinstaller --noconfirm video_analyzer.spec

# Check build status
if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

# Create directories
echo "Creating output directories..."
mkdir -p dist/VideoAnalyzer/settings

# Copy configuration files
echo "Copying assets..."
cp -r settings/* dist/VideoAnalyzer/settings/
if [ -d "secrets" ]; then
    mkdir -p dist/VideoAnalyzer/secrets
    cp -r secrets/* dist/VideoAnalyzer/secrets/
fi

echo "🎉 Build complete! Executable located in dist/VideoAnalyzer/VideoAnalyzer.exe"
