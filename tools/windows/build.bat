@echo off
setlocal
cd /d "%~dp0..\.."

REM One-click local build of the Windows version, run from the repo root. ASCII only: Chinese Windows cmd is GBK.
REM Output: dist\chat-wingman\chat-wingman.exe

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtualenv .venv ...
    python -m venv .venv || goto :fail
)
call ".venv\Scripts\activate.bat" || goto :fail

echo Installing dependencies ...
python -m pip install -r requirements-windows.txt pyinstaller || goto :fail

echo Building ...
pyinstaller --noconfirm --clean tools\windows\wingman.spec || goto :fail

echo.
echo Build OK.
echo   %cd%\dist\chat-wingman\chat-wingman.exe
echo Ship the whole dist\chat-wingman folder: the exe needs the files next to it.
pause
exit /b 0

:fail
echo.
echo Build FAILED. Scroll up for the error.
pause
exit /b 1
