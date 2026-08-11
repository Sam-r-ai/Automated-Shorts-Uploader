@echo off
rem Double-click to authorize the CarouselStudiosLab channel (The Trend Desk
rem drops from GimHoTrends upload here).
rem
rem Pins the slug to "carousel-studios-lab" with --name, so the token filename
rem is predictable no matter how the channel title is spelled - GimHoTrends'
rem production\channel.json already points at that exact slug.
rem
rem Re-run this any time the token expires (Google drops a refresh token after
rem ~6 months unused; check-channels.cmd shows health).
rem
rem Must stay CRLF + plain ASCII or cmd mis-parses it.

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   Cannot find .venv\Scripts\python.exe in:
    echo   %~dp0
    echo.
    pause
    exit /b 1
)

echo.
echo   ============================================================
echo    A browser window is about to open.
echo.
echo    1. Sign in with the Google account that owns CarouselStudiosLab.
echo    2. If it lists channels or Brand Accounts, pick CarouselStudiosLab.
echo       That choice binds this token permanently.
echo    3. On "Google hasn't verified this app": click Advanced, then
echo       "Go to ... (unsafe)". That screen is expected - it is your
echo       own unpublished Google Cloud project, not a third party.
echo   ============================================================
echo.

".venv\Scripts\python.exe" channel_auth.py add --name carousel-studios-lab

echo.
echo   Run check-channels.cmd any time to see what is authorized.
echo.
pause
