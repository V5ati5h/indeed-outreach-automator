@echo off
setlocal
REM Relaunch YOUR Chrome (same profile, stays logged in) with remote debugging
REM so: python run.py indeed-login
set CHROME=
for %%P in ("%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" "C:\Program Files\Google\Chrome\Application\chrome.exe" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") do if exist %%~P set CHROME=%%~P
if not defined CHROME for /f "delims=" %%C in ('where chrome 2^>nul') do if not defined CHROME set CHROME=%%C
if not defined CHROME (
  echo Chrome not found. Install Google Chrome first.
  pause
  exit /b 1
)
echo Using: %CHROME%
echo This uses a SEPARATE debug profile - your main Chrome stays open, no work lost.
start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\ChromeDebug" --no-first-run
timeout /t 3 /nobreak >nul
curl -s http://127.0.0.1:9222/json/version 2>nul | findstr "Browser" >nul
if %errorlevel%==0 (
  echo PORT OPEN. Now run: python run.py indeed-login
) else (
  echo Port NOT open. Run: python run.py indeed-login --fresh  (no debug port needed)
)
pause
