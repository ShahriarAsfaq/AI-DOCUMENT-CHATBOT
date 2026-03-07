@echo off
echo Starting AI Document Chatbot...

REM Start Django backend in background
start cmd /k "cd /d %~dp0 && .\.venv\Scripts\python.exe manage.py runserver"

REM Wait a moment for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend
cd frontend
npm run dev