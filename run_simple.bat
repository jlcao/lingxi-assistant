@echo off

start "Backend" python -m lingxi --web

ping -n 3 127.0.0.1 > nul

start "Frontend" cmd /k "cd lingxi-desktop && npm run dev"

echo Services started!
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173

pause