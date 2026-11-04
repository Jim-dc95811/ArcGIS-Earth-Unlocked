@echo off
rem ArcGIS Earth Flight launcher v1.0: makes a desktop shortcut "ArcGIS Earth Flight" (ArcGIS Earth icon)
rem that runs Fly_ArcGIS_Earth.bat. Right-click it and choose Pin to taskbar.
setlocal
title ArcGIS Earth Flight - make shortcut
cd /d "%~dp0"
if exist "%~dp0Fly_ArcGIS_Earth.bat" goto :have_fly
echo Fly_ArcGIS_Earth.bat must be in the same folder as this file.
pause
exit /b 1
:have_fly
call "%~dp0Fly_ArcGIS_Earth.bat" /find
if errorlevel 1 exit /b 1
set /p AE=<"%~dp0ArcGIS_Earth_path.txt"
set "FLY=%~dp0Fly_ArcGIS_Earth.bat"
set "DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop');" ^
  "$l = $s.CreateShortcut((Join-Path $d 'ArcGIS Earth Flight.lnk'));" ^
  "$l.TargetPath = $env:ComSpec; $l.Arguments = '/c ' + [char]34 + $env:FLY + [char]34;" ^
  "$l.WorkingDirectory = $env:DIR; $l.IconLocation = $env:AE + ',0';" ^
  "$l.Description = 'Start ArcGIS Earth, then EarthStick'; $l.Save(); Write-Host ('Made: ' + $l.FullName)"
if not errorlevel 1 goto :made
echo Could not make the shortcut.
pause
exit /b 1
:made
echo.
echo Done. On your desktop: "ArcGIS Earth Flight".
echo To put it on the taskbar: right-click it, Show more options, Pin to taskbar.
echo (You can then delete the desktop copy.)
pause
