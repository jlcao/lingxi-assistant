@echo off

rem Lingxi Assistant Complete Build Script
set PROJECT_ROOT=%~dp0
set FRONTEND_DIR=%PROJECT_ROOT%lingxi-desktop

rem Clean up previous builds
echo Cleaning up previous builds...
if exist %FRONTEND_DIR%\electron\main\backend rmdir /s /q %FRONTEND_DIR%\electron\main\backend
if exist %FRONTEND_DIR%\release rmdir /s /q %FRONTEND_DIR%\release

rem 1. Build backend
echo Building backend...
cd %PROJECT_ROOT%

rem Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt
pip install pyinstaller

rem Build backend using PyInstaller
echo Building backend using PyInstaller...
pyinstaller backend.spec

rem Create frontend backend directories
echo Creating frontend backend directories...
mkdir %FRONTEND_DIR%\electron\main\backend
mkdir %FRONTEND_DIR%\dist-electron\main\backend

rem Copy build results to frontend
echo Copying backend build results to frontend...
xcopy dist\lingxi-backend %FRONTEND_DIR%\electron\main\backend /s /e /y
xcopy dist\lingxi-backend %FRONTEND_DIR%\dist-electron\main\backend /s /e /y

if errorlevel 1 (
    echo Backend build failed!
    pause
    exit /b 1
)

echo Backend build completed

rem 2. Build frontend
echo Building frontend...
cd %FRONTEND_DIR%

rem Install frontend dependencies
echo Installing frontend dependencies...
npm install

if errorlevel 1 (
    echo Frontend dependency installation failed!
    pause
    exit /b 1
)

echo Frontend dependency installation completed

rem Build frontend
echo Building frontend...
npm run electron:build:win

if errorlevel 1 (
    echo Frontend build failed!
    pause
    exit /b 1
)

echo Frontend build completed

echo The entire build process has been completed
echo Build results are located at: %FRONTEND_DIR%\release

pause