@echo off
cd /d "%~dp0"
set ROOT=%cd%
cd Backend

where python >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=python
    goto :indit
)

where py >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=py
    goto :indit
)

echo.
echo Nem talalhato Python a gepen.
echo Toltsd le innen: https://www.python.org/downloads/
echo Telepiteskor pipald be az "Add python.exe to PATH" opciot.
echo.
pause
exit /b 1

:indit
echo Fuggosegek ellenorzese / telepitese...
%PYCMD% -m pip install -r "%ROOT%\requirements.txt" --quiet
if errorlevel 1 (
    echo.
    echo Hiba tortent a csomagok telepitese kozben.
    echo Ellenorizd az internetkapcsolatot, majd probald ujra.
    pause
    exit /b 1
)

start "" cmd /c "timeout /t 2 >nul && start http://localhost:5000"

echo Jatekgyujtemeny inditasa (%PYCMD%)...
echo Ha hiba van, a hibauzenet itt lathato lesz.
echo.
%PYCMD% app.py

echo.
echo A szerver leallt.
pause
