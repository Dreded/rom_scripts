@echo off
setlocal enabledelayedexpansion

REM Check argument
if "%~1"=="" (
    echo Usage: %~nx0 [working_folder]
    exit /b 1
)

set "WORK_FOLDER=%~1"

REM Remove trailing backslash if exists
if "%WORK_FOLDER:~-1%"=="\" set "WORK_FOLDER=%WORK_FOLDER:~0,-1%"

REM Process .cue, .gdi, and .iso
for /r "%WORK_FOLDER%" %%i in (*.cue *.gdi *.iso) do (
    echo.
    echo Processing: "%%i"

    set "INPUT_FILE=%%i"
    set "OUTPUT_FILE=%%~dpni.chd"

    chdman createcd -i "%%i" -o "!OUTPUT_FILE!" >nul 2>&1

    if exist "!OUTPUT_FILE!" (
        echo Successfully created CHD: "!OUTPUT_FILE!"
        echo Deleting original: "%%i"
        del "%%i"
    ) else (
        echo Failed to create CHD for: "%%i"
    )
)

echo.
echo All done.
