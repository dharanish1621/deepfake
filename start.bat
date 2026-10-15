@echo off
cd /d "%~dp0"
call setup.bat %*
exit /b %ERRORLEVEL%

