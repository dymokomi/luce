@echo off
rem Install Luce on Windows from Command Prompt, in one line:
rem
rem   curl -fsSLo "%TEMP%\luce-install.cmd" https://luce.luciaos.com/install.cmd && "%TEMP%\luce-install.cmd"
rem
rem It runs install.ps1 through Windows PowerShell (the compilers and luc), then reads the
rem user PATH back into this window, so `luc` works here at once as it will in every new window.
rem install.ps1's overrides apply (LUCE_INSTALL_DIR, LUC_HOME, ...); LUCE_INSTALL_SCRIPT_URL
rem names another install.ps1. No setlocal: the PATH it sets is this window's.
set "LUCE_INSTALL_PS1=%TEMP%\luce-install-%RANDOM%%RANDOM%.ps1"
set "LUCE_INSTALL_FROM=%LUCE_INSTALL_SCRIPT_URL%"
if not defined LUCE_INSTALL_FROM set "LUCE_INSTALL_FROM=https://luce.luciaos.com/install.ps1"
curl.exe -fsSL -o "%LUCE_INSTALL_PS1%" "%LUCE_INSTALL_FROM%"
if errorlevel 1 (
    echo luce: could not download %LUCE_INSTALL_FROM%
    set "LUCE_INSTALL_PS1="
    set "LUCE_INSTALL_FROM="
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%LUCE_INSTALL_PS1%"
set "LUCE_INSTALL_STATUS=%ERRORLEVEL%"
del "%LUCE_INSTALL_PS1%" 2>nul
set "LUCE_INSTALL_PS1="
set "LUCE_INSTALL_FROM="
if not "%LUCE_INSTALL_STATUS%"=="0" (
    echo luce: the installation did not finish, see the message above; run this command again
    set "LUCE_INSTALL_STATUS="
    exit /b 1
)
set "LUCE_INSTALL_STATUS="
for /f "usebackq delims=" %%p in (`powershell.exe -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','User')"`) do set "PATH=%%p;%PATH%"
echo.
echo Luce is ready in this window and in new ones. To install an application:
echo     luc install dymokomi/luced-photo
