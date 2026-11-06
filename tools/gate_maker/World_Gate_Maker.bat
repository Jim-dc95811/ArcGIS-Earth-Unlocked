@echo off
cd /d "%~dp0"
title World Gate Maker 1.2
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 "System Files\World_Gate_Maker.py"
) else (
    python "System Files\World_Gate_Maker.py"
)
pause
