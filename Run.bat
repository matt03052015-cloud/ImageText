
@echo off
title ImageText Debug
cd /d "%~dp0"

echo Starting ImageText...
echo.

python -u ImageText.py

echo.
echo Python exited with code %errorlevel%.
echo.
pause
