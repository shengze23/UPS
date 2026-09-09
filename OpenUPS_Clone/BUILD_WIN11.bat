@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 (
    echo.
    echo Build failed. Please send a screenshot of this whole window.
    pause
    exit /b 1
)
echo.
echo Build complete: dist\OpenUPS-Clone\OpenUPS-Clone.exe
pause
endlocal
