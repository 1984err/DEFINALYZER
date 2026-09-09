@echo off
setlocal
set "DEFINALYZER_STOP_ROOT=%~dp0"
set "DEFINALYZER_STOP_CHECK="
if /i "%~1"=="/check" set "DEFINALYZER_STOP_CHECK=1"

powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; try { $exe=Join-Path $env:DEFINALYZER_STOP_ROOT '.venv\Scripts\python.exe'; $targets=@(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $exe -and $_.CommandLine -match 'main\.py[\x22\x27]?\s+dashboard(?:\s|$)' }); if (!$targets.Count) { Write-Host 'No DEFINALYZER dashboard is running for this folder.'; exit 0 }; foreach ($target in $targets) { if ($env:DEFINALYZER_STOP_CHECK) { Write-Host ('Would stop dashboard and its child processes: PID '+$target.ProcessId) } else { Write-Host ('Stopping DEFINALYZER dashboard: PID '+$target.ProcessId); & taskkill.exe /PID $target.ProcessId /T /F; if ($LASTEXITCODE -ne 0) { throw 'Windows could not stop the dashboard.' } } }; if (!$env:DEFINALYZER_STOP_CHECK) { Write-Host 'Dashboard stopped. Previously saved files are retained.' } } catch { Write-Host ('Unable to stop DEFINALYZER: '+$_.Exception.Message); exit 1 }"
set "DEFINALYZER_STOP_RESULT=%ERRORLEVEL%"
if not defined DEFINALYZER_STOP_CHECK pause
exit /b %DEFINALYZER_STOP_RESULT%
