@echo off
rem ArcGIS Earth Flight launcher v2.0 - EarthStick 1.3.9 TEST
rem Ready to Fly: finds or installs Python, finds and starts ArcGIS Earth,
rem checks its Automation API and the internet, then starts EarthStick.
title EarthStick 1.3.9 TEST
echo Starting Ready to Fly - on an older PC this first step can take a few minutes, please wait...
echo (Windows Defender may check the files first and slow the PC. That is normal - do not close this window.)
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
