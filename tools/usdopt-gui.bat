@echo off
setlocal

if "%USD_OPTIMIZE_RUNTIME_ROOT%"=="" (
    if exist "%~dp0..\vendor\usd_optimize\package\python" (
        set "USD_OPTIMIZE_RUNTIME_ROOT=%~dp0..\vendor\usd_optimize\package"
    ) else (
        set "USD_OPTIMIZE_RUNTIME_ROOT=%~dp0..\vendor\usd_optimize"
    )
)

set "USD_OPTIMIZE_APP_PRESETS_DIR=%~dp0..\presets"

pushd "%~dp0.."
uv run usdopt-gui
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
