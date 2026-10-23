@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" run.py %*
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" exit /b 0
echo.
echo Klienten avsluttet med kode %RC%. Se meldingen over.
pause
exit /b %RC%
:missing
echo Kjor install.bat forst.
pause
exit /b 1
