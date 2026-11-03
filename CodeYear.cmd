@echo off
cd /d "%~dp0"
where pythonw >nul 2>&1
if %errorlevel%==0 (
  start "" pythonw -m codeyear gui
) else (
  python -m codeyear gui
  if errorlevel 1 pause
)
