@echo off
rem Double-click this to authorize one YouTube channel.
rem
rem A YouTube token is bound to the channel you pick at Google's consent
rem screen, so run this once per channel and choose a different one each time.
rem
rem Written as a .cmd deliberately: the equivalent one-liner is easy to get
rem wrong in PowerShell, which has no && operator and needs .\ before a
rem relative executable. This file must stay CRLF + plain ASCII or cmd
rem mis-parses it.

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   Cannot find .venv\Scripts\python.exe in:
    echo   %~dp0
    echo.
    echo   Create the virtual environment first:
    echo       py -3 -m venv .venv
    echo       .venv\Scripts\pip install google-auth google-auth-oauthlib google-api-python-client
    echo.
    pause
    exit /b 1
)

echo.
echo   ============================================================
echo    A browser window is about to open.
echo.
echo    1. Sign in with the Google account that owns the channel.
echo    2. If it shows a list of channels or Brand Accounts, pick
echo       the RIGHT one. That choice binds this token permanently,
echo       and a video cannot be moved between channels later.
echo   ============================================================
echo.

".venv\Scripts\python.exe" channel_auth.py add %*

echo.
echo   Run check-channels.cmd any time to see what is authorized.
echo.
pause