@echo off
setlocal
cd /d "%~dp0"

echo OpenUPS Clone - Windows 11 read-only test
echo.
echo IMPORTANT: Disconnect the OpenUPS USB device from the Windows 7 VM first.
echo Close the legacy OpenUPS program before continuing.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python environment...
    py -3.12 -m venv .venv
    if errorlevel 1 py -m venv .venv
    if errorlevel 1 goto :failed
)

echo Installing/checking required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Starting native Windows 11 vendor-HID telemetry...
".venv\Scripts\python.exe" main.py --debug-hid
if errorlevel 1 goto :failed
goto :end

:failed
echo.
echo Setup or launch failed. Please send a screenshot of this whole window.
pause

:end
endlocal
