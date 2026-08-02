@echo off
rem Double-click this to see which YouTube channels are authorized and
rem whether each token still works. Read-only. It also refreshes anything
rem it can, which is what keeps tokens alive: Google drops a refresh token
rem that has gone six months unused.
rem
rem Must stay CRLF + plain ASCII or cmd mis-parses it.

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo   Cannot find .venv\Scripts\python.exe in %~dp0
    pause
    exit /b 1
)

".venv\Scripts\python.exe" channel_auth.py list

echo.
pause