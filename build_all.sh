#!/bin/bash

# Lingxi Assistant Complete Build Script
PROJECT_ROOT=$(pwd)
FRONTEND_DIR="$PROJECT_ROOT/lingxi-desktop"
MAIN_DIST_DIR="$PROJECT_ROOT/dist"

# Clean previous build artifacts
echo "Cleaning previous build artifacts..."
rm -rf "$MAIN_DIST_DIR" "$PROJECT_ROOT/build"
rm -rf "$FRONTEND_DIR/electron/main/backend" "$FRONTEND_DIR/dist-electron/main/backend"
rm -rf "$FRONTEND_DIR/dist" "$FRONTEND_DIR/dist-electron" "$FRONTEND_DIR/release"

# Create main dist directory
echo "Creating main dist directory..."
mkdir -p "$MAIN_DIST_DIR"
mkdir -p "$MAIN_DIST_DIR/backend"
mkdir -p "$MAIN_DIST_DIR/frontend"

# 1. Build backend
echo "Building backend..."
cd "$PROJECT_ROOT"

# Install dependencies
echo "Installing Python dependencies..."
which pip || { echo "Error: pip not found. Please install Python 3 and pip first."; echo "Press Enter to exit..."; read; exit 1; }
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies."
    echo "Press Enter to exit..."
    read
    exit 1
fi

pip install pyinstaller
if [ $? -ne 0 ]; then
    echo "Error: Failed to install PyInstaller."
    echo "Press Enter to exit..."
    read
    exit 1
fi

# Build backend using PyInstaller
echo "Building backend using PyInstaller..."
python -m PyInstaller backend.spec
if [ $? -ne 0 ]; then
    echo "Error: Failed to build backend using PyInstaller."
    echo "Press Enter to exit..."
    read
    exit 1
fi

# Check if the build result exists
if [ ! -d "dist/backend" ]; then
    echo "Error: Backend build result not found."
    echo "Press Enter to exit..."
    read
    exit 1
fi

# Create frontend backend directories
echo "Creating frontend backend directories..."
mkdir -p "$FRONTEND_DIR/electron/main/backend"
mkdir -p "$FRONTEND_DIR/dist-electron/main/backend"

# Copy build results to frontend
echo "Copying backend build results to frontend..."
cp -r "$MAIN_DIST_DIR/backend" "$FRONTEND_DIR/electron/main/"
if [ $? -ne 0 ]; then
    echo "Error: Failed to copy backend build results to frontend."
    echo "Press Enter to exit..."
    read
    exit 1
fi

cp -r "$MAIN_DIST_DIR/backend" "$FRONTEND_DIR/dist-electron/main/"
if [ $? -ne 0 ]; then
    echo "Error: Failed to copy backend build results to frontend."
    echo "Press Enter to exit..."
    read
    exit 1
fi

echo "Backend build completed"

# 2. Build frontend
echo "Building frontend..."
cd "$FRONTEND_DIR"

# Install frontend dependencies
echo "Installing frontend dependencies..."
which npm || { echo "Error: npm not found. Please install Node.js first."; echo "Press Enter to exit..."; read; exit 1; }
npm install
if [ $? -ne 0 ]; then
    echo "Frontend dependency installation failed!"
    echo "Press Enter to exit..."
    read
    exit 1
fi

# Build frontend
echo "Building frontend..."
npm run build:linux
if [ $? -ne 0 ]; then
    echo "Frontend build failed!"
    echo "Press Enter to exit..."
    read
    exit 1
fi

echo "Moving frontend build results to main dist directory..."

# Assuming the frontend build output is in dist directory
if [ -d "dist" ]; then
    cp -r dist/* "$MAIN_DIST_DIR/frontend/"
fi

echo "Frontend build completed"

echo "The entire build process has been completed"
echo "Build results are located at: $MAIN_DIST_DIR"
echo "Backend build: $MAIN_DIST_DIR/backend"
echo "Frontend build: $MAIN_DIST_DIR/frontend"

echo "Press Enter to exit..."
read
