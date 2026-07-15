@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-carteira-alpha.ps1"
echo.
echo URLs atuais:
type "%~dp0logs\carteira-alpha-urls.txt"
echo.
pause
