@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if exist ".venv\Scripts\python.exe" goto verify
py -3 -c "import sys; raise SystemExit(not sys.version_info >= (3, 11))" >nul 2>&1
if errorlevel 1 goto try_python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto verify
:try_python
python -c "import sys; raise SystemExit(not sys.version_info >= (3, 11))" >nul 2>&1
if errorlevel 1 goto missing_python
python -m venv .venv
if errorlevel 1 goto failed
:verify
".venv\Scripts\python.exe" tools\check_runtime.py
if errorlevel 1 goto failed
echo.
echo Installasjon kontrollert. Ingen tredjepartspakker trengs i a1.
echo Kjor test.bat, deretter start.bat.
pause
exit /b 0
:missing_python
echo Python 3.11 eller nyere med Tcl/Tk ble ikke funnet.
echo Installer Python for Windows, og inkluder Tcl/Tk.
pause
exit /b 1
:failed
echo Installasjonskontroll feilet. Ingen lokale oppsettdata er slettet.
pause
exit /b 1
