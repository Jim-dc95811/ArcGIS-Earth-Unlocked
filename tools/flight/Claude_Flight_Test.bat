@echo off
cd /d "%~dp0System Files"
title Claude Flight Test 0.8
where py >nul 2>&1
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% claude_flight.py read
echo.
echo Bringing ArcGIS Earth to the front - Lesson 7: gate run - Claude shows the World Gates, flies north to the Jacksonville ATL gate, lines up, goes through and comes out over Atlanta (about 80 s). Starts in 10 seconds.
echo Touch the mouse to take over.
powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).AppActivate('ArcGIS Earth') | Out-Null"
timeout /t 10 >nul
%PY% claude_flight.py gaterun
echo.
echo Done. This window closes in 60 seconds.
timeout /t 60
