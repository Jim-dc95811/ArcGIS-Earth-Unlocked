@echo off
setlocal
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
title Where's the Firefighter? picture maker

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
echo  WHERE'S THE FIREFIGHTER?  Build your own town.
echo  The same name always makes the same town.
echo.
set "TOWN="
set /p "TOWN=Name your town (or press Enter for New Claude City): "
echo.
if defined TOWN (
  %PYEXE% "System Files\wheres_the_firefighter.py" --name "%TOWN%"
) else (
  %PYEXE% "System Files\wheres_the_firefighter.py"
)
echo.
pause
endlocal
