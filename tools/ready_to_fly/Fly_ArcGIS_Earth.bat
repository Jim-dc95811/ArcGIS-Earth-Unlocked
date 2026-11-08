@echo off
rem ArcGIS Earth Flight launcher v2.0 - EarthStick 1.3.8 TEST
rem Ready to Fly: finds or installs Python, finds and starts ArcGIS Earth,
rem checks its Automation API and the internet, then starts EarthStick.
title EarthStick 1.3.8 TEST
cd /d "%~dp0System Files"
if /i "%~1"=="/find" goto findonly
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0System Files\Ready_To_Fly.ps1" -Folder "%~dp0System Files" -Tool "EarthStick" -NeedEarth -NeedApi -NeedTk
if errorlevel 1 goto stopped
set /p PYEXE=<"%~dp0System Files\python_path.txt"
if not defined PYEXE goto stopped
"%PYEXE%" EarthStick.py
pause
exit /b 0

:findonly
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0System Files\Ready_To_Fly.ps1" -Folder "%~dp0System Files" -Tool "EarthStick" -EarthOnly
if errorlevel 1 goto stopped
exit /b 0

:stopped
echo.
echo EarthStick did not start - read the message above.
echo A log is in System Files\Ready_To_Fly_log.txt
pause
exit /b 1
