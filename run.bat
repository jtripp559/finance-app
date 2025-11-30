@echo off
REM Personal Finance App - Windows Launcher
REM This script sets up the environment and runs the Flask app

echo ========================================
echo Personal Finance App Launcher
echo ========================================
echo.

REM Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Create data directory if it doesn't exist
if not exist "data" (
    echo Creating data directory...
    mkdir data
)

REM Set environment variables
set FLASK_APP=backend.app
set FLASK_ENV=development
set SECRET_KEY=dev-secret-key-change-in-production

REM Initialize database and seed data
echo Initializing database...
python -c "from backend.app import create_app; from backend.db_init import seed_database; app = create_app(); seed_database(app)"
if errorlevel 1 (
    echo WARNING: Database initialization had issues, but continuing...
)

echo.
echo ========================================
echo Starting Personal Finance App...
echo Open http://localhost:5000 in your browser
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Run the Flask app
python -m flask run --host=0.0.0.0 --port=5000

REM Deactivate virtual environment on exit
deactivate
