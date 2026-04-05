#!/bin/bash

# Lingxi Assistant Complete Build Script
PROJECT_ROOT=$(pwd)
FRONTEND_DIR="$PROJECT_ROOT/lingxi-desktop"
MAIN_DIST_DIR="$PROJECT_ROOT/dist"

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
pip3 install -r requirements.txt
pip3 install pyinstaller

# Build backend using PyInstaller
echo "Building backend using PyInstaller..."
python3 -m PyInstaller backend.spec

# Move build results to main dist directory
echo "Moving backend build results to main dist directory..."
mv -f dist/lingxi-backend "$MAIN_DIST_DIR/backend"

# Create frontend backend directories
echo "Creating frontend backend directories..."
mkdir -p "$FRONTEND_DIR/electron/main/backend"
mkdir -p "$FRONTEND_DIR/dist-electron/main/backend"

# Copy build results to frontend
echo "Copying backend build results to frontend..."
cp -r "$MAIN_DIST_DIR/backend" "$FRONTEND_DIR/electron/main/"
cp -r "$MAIN_DIST_DIR/backend" "$FRONTEND_DIR/dist-electron/main/"

if [ $? -ne 0 ]; then
    echo "Backend build failed!"
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
