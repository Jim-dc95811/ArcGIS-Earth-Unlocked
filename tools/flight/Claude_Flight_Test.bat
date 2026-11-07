@echo off
cd /d "%~dp0System Files"
title Claude Flight Test 0.9
where py >nul 2>&1
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% claude_flight.py read
echo.
echo Bringing ArcGIS Earth to the front - Lesson 8: the first tour - JAX gate home, downtown, chopper orbit, neighbourhood drive-by, climb-out (about 5 minutes). Starts in 10 seconds.
echo Touch the mouse to take over.
powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).AppActivate('ArcGIS Earth') | Out-Null"
timeout /t 10 >nul
%PY% claude_flight.py tour
echo.
echo Done. This window closes in 60 seconds.
timeout /t 60
