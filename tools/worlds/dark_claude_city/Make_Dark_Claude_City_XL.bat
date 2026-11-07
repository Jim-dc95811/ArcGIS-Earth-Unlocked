@echo off
setlocal
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
title Dark Claude City XL

set "PYEXE=py -3"
where py >nul 2>nul || set "PYEXE=python"
%PYEXE% --version >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3 from python.org and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

rem --- needs Pillow - install it once if it is missing ---
%PYEXE% -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo Pillow is not installed yet. Installing it now - one time only...
  %PYEXE% -m pip install Pillow
  %PYEXE% -c "import PIL" >nul 2>nul
  if errorlevel 1 (
    echo.
    echo Pillow could not be installed automatically.
    echo Open Command Prompt and run:  py -3 -m pip install Pillow
    echo If your network blocks downloads, ask IT to install Pillow.
    pause
    exit /b 1
  )
)

echo.
echo  DARK CLAUDE CITY XL - drawn straight into a TPKX for ArcGIS Earth
echo.
echo  City size:  1 = normal (about 33 km wide, 150 MB)    10 = ten times the city (105 km, about 1.6 GB)
echo              anything up to 11 fits one World spot; bigger spills into the next spots.
set "SIZE="
set /p "SIZE=City size (press Enter for 10): "
if not defined SIZE set "SIZE=10"
set "SPOT="
set /p "SPOT=World spot 1-20 (press Enter for 6): "
if not defined SPOT set "SPOT=6"
echo.
%PYEXE% "System Files\world_tiles.py" --size %SIZE% --spot %SPOT%
echo.
pause
endlocal
