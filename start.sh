#!/bin/bash

echo "Starting AI Document Chatbot..."

# Start Django backend in background
./.venv/bin/python manage.py runserver &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both servers"

# Wait for user to stop
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" INT
wait