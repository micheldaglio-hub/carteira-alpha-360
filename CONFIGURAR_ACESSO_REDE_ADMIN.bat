@echo off
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath PowerShell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%ROOT%scripts\ensure-lan-firewall.ps1"" -Pause'"
