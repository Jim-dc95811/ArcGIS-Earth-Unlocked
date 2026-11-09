@echo off
cd /d "%~dp0System Files"
title Claude flies: Babel to the Shard (take 4)
where py >nul 2>&1
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% babel_to_shard.py read
echo.
echo Bringing ArcGIS Earth to the front. START RECORDING now, park the mouse in a corner.
echo Claude takes off in 10 seconds. Touch the mouse to take over.
powershell -NoProfile -Command "(New-Object -ComObject WScript.Shell).AppActivate('ArcGIS Earth') | Out-Null"
timeout /t 10 >nul
%PY% babel_to_shard.py
echo.
echo Done. This window closes in 60 seconds.
timeout /t 60
