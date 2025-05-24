@echo off
setlocal enabledelayedexpansion

:: Define source and target
set "ESDE_SRC=..\ES-DE"
set "ESDE_DST=/sdcard/ES-DE"

:: Sync ROMs
rem python adb-sync.py --delete ../ROMs/ /sdcard/ROMs/

:: Sync everything in ES-DE except downloaded_media
for /d %%D in ("%ESDE_SRC%\*") do (
    if /I not "%%~nxD"=="downloaded_media" (
        set "SRC=%%~fD"
        set "SRC=!SRC:\=/!"
        python adb-sync.py --delete "!SRC!" "%ESDE_DST%/%%~nxD"
    )
)

:: Handle downloaded_media separately
if exist "%ESDE_SRC%\downloaded_media" (
    for /d %%D in ("%ESDE_SRC%\downloaded_media\*") do (
        set "FOLDER=%%~nxD"
        if /I not "!FOLDER!"=="videos" if /I not "!FOLDER!"=="manuals" (
            set "SRC=%%~fD"
            set "SRC=!SRC:\=/!"
            python adb-sync.py --delete "!SRC!" "%ESDE_DST%/downloaded_media/!FOLDER!"
        )
    )
)

endlocal
