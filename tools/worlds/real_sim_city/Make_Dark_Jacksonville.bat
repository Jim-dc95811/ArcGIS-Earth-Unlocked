@echo off
setlocal
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
title Dark Jacksonville - Real Sim City

set "PYEXE=py -3"
where py >nul 2>nul || set "PYEXE=python"
%PYEXE% --version >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3 from python.org and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

rem --- needs Pillow and numpy - install them once if missing ---
for %%M in (PIL numpy) do (
  %PYEXE% -c "import %%M" >nul 2>nul
  if errorlevel 1 (
    echo Installing %%M - one time only...
    if "%%M"=="PIL" (%PYEXE% -m pip install Pillow) else (%PYEXE% -m pip install numpy)
  )
)
%PYEXE% -c "import PIL, numpy" >nul 2>nul
if errorlevel 1 (
  echo.
  echo Pillow or numpy could not be installed automatically.
  echo Open Command Prompt and run:  py -3 -m pip install Pillow numpy
  echo If your network blocks downloads, ask IT to install them.
  pause
  exit /b 1
)

echo.
echo  DARK JACKSONVILLE - a fictional night city on the real lot lines
echo  Needs beside this file: the Parcel100 .geojson and the street map .mbtiles
echo.
%PYEXE% "System Files\realsim.py" %*
echo.
pause
endlocal
