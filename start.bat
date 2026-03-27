@echo off

rem Start Lingxi Assistant

echo Starting Lingxi Assistant...

rem Start backend service
start "Backend" python -m lingxi --web

rem Wait for 2 seconds
ping -n 3 127.0.0.1 > nul

rem Start frontend service
start "Frontend" cmd /k "cd lingxi-desktop && npm run dev"

echo Services started successfully!
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173

echo Press any key to close this window...
pause