@echo off
cd /d "%~dp0System Files"
title Claude Flight Test 0.11 - Obstacle Course
where py >nul 2>&1
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% claude_flight.py read
echo.
echo Bringing ArcGIS Earth to the front - OBSTACLE COURSE v1: 7 hoops over Dark Jacksonville, scored. Start recording now - Claude takes off in 10 seconds.
echo Touch the mouse to take over.
powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).AppActivate('ArcGIS Earth') | Out-Null"
timeout /t 10 >nul
%PY% claude_flight.py course 100
echo.
echo Done. This window closes in 60 seconds.
timeout /t 60
