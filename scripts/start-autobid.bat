@echo off
rem AutoBid Intelligence launcher - runs the servers hidden, then opens the browser.

if /I "%~1"=="worker" goto :worker

rem First click: relaunch this script hidden so no console window lingers, then exit.
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList 'worker' -WindowStyle Hidden"
exit /b

:worker
setlocal
set "ROOT=C:\Users\msi20\OneDrive\Desktop\Dealership"
set "API=%ROOT%\apps\api"
set "WEB=%ROOT%\apps\web"
set "PY=%API%\.venv\Scripts\python.exe"

rem If it is already running, just open the browser.
powershell -NoProfile -Command "try{ Invoke-WebRequest http://localhost:3000 -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 }catch{ exit 1 }"
if %errorlevel%==0 goto :open

if not exist "%PY%" exit /b 1

rem Seed the database on first run (idempotent).
pushd "%API%"
"%PY%" -m app.seed --if-empty
popd

rem Start the API and web app hidden and detached (no windows).
powershell -NoProfile -Command "Start-Process -FilePath '%PY%' -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory '%API%' -WindowStyle Hidden"
powershell -NoProfile -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm run dev' -WorkingDirectory '%WEB%' -WindowStyle Hidden"

rem Wait until the web app answers, then open the browser.
powershell -NoProfile -Command "for($i=0;$i -lt 90;$i++){ try{ if((Invoke-WebRequest http://localhost:3000 -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200){ break } }catch{}; Start-Sleep -Seconds 1 }"

:open
start "" http://localhost:3000
endlocal
exit /b
