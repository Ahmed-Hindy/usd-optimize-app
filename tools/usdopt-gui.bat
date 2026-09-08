@echo off
setlocal

set "USD_OPTIMIZE_APP_PRESETS_DIR=%~dp0..\presets"

pushd "%~dp0.."
uv --system-certs run usdopt-gui %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
