@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" tools\run_tests.py
set "RC=%ERRORLEVEL%"
echo.
echo Rapport ligger under docs\test-results.
pause
exit /b %RC%
:missing
echo Kjor install.bat forst.
pause
exit /b 1
