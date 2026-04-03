@echo off

rem Lingxi Assistant Complete Build Script
set PROJECT_ROOT=%~dp0
set FRONTEND_DIR=%PROJECT_ROOT%lingxi-desktop
set MAIN_DIST_DIR=%PROJECT_ROOT%dist

rem Create main dist directory
echo Creating main dist directory...
mkdir %MAIN_DIST_DIR%
mkdir %MAIN_DIST_DIR%\backend
mkdir %MAIN_DIST_DIR%\frontend

rem 1. Build backend
echo Building backend...
cd %PROJECT_ROOT%

rem Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt
pip install pyinstaller

rem Build backend using PyInstaller
echo Building backend using PyInstaller...
python -m PyInstaller backend.spec

rem Move build results to main dist directory
echo Moving backend build results to main dist directory...
move dist\lingxi-backend %MAIN_DIST_DIR%\backend

rem Create frontend backend directories
echo Creating frontend backend directories...
mkdir %FRONTEND_DIR%\electron\main\backend
mkdir %FRONTEND_DIR%\dist-electron\main\backend

rem Copy build results to frontend
echo Copying backend build results to frontend...
xcopy %MAIN_DIST_DIR%\backend %FRONTEND_DIR%\electron\main\backend /s /e /y
xcopy %MAIN_DIST_DIR%\backend %FRONTEND_DIR%\dist-electron\main\backend /s /e /y

if errorlevel 1 (
    echo Backend build failed!
    pause
    exit /b 1
)

echo Backend build completed

rem 2. Build frontend
echo Building frontend...
cd lingxi-desktop

rem Install frontend dependencies
echo Installing frontend dependencies...

if errorlevel 1 (
    echo Frontend dependency installation failed!
    pause
)

rem Build frontend
echo Building frontend...
npm run build:win

if errorlevel 1 (
    echo Frontend build failed!
    pause
    exit /b 1
)

echo Moving frontend build results to main dist directory...

echo Frontend build completed

echo The entire build process has been completed
echo Build results are located at: %MAIN_DIST_DIR%
echo Backend build: %MAIN_DIST_DIR%\backend
echo Frontend build: %MAIN_DIST_DIR%\frontend

pause