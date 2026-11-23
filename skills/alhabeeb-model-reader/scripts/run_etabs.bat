@echo off
rem Drag an ETABS .EDB file onto this file, or run:  run_etabs.bat "D:\Projects\Tower\Tower.EDB" 200
rem Second argument = net allowable soil pressure kN/m2 (default 200 - change it from the soil report!)
setlocal
if "%~1"=="" (
  echo Drag a .EDB file onto run_etabs.bat
  pause
  exit /b 1
)
set QALLOW=%~2
if "%QALLOW%"=="" set QALLOW=200
python -m pip install -q comtypes openpyxl ezdxf matplotlib
python "%~dp0etabs_live.py" --edb "%~f1" --fix --q-allow %QALLOW% --project "%~n1" --project-code PRJ -o "%~dp1%~n1_design"
echo.
echo Results in "%~dp1%~n1_design"
pause
