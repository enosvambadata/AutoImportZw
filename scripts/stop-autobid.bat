@echo off
title Stop AutoBid
echo Stopping AutoBid servers on ports 8000 and 3000...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -Expand OwningProcess -Unique | ForEach-Object { try{ Stop-Process -Id $_ -Force; Write-Host ('Stopped PID ' + $_) } catch {} }"
echo Done. You can close the two server windows if they are still open.
timeout /t 3 >nul
