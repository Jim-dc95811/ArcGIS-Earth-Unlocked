@echo off
cd /d "%~dp0"
title World Gate Maker 1.1
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 World_Gate_Maker.py
) else (
    python World_Gate_Maker.py
)
pause
