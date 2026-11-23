@echo off
rem Drag an SAFE .FDB file onto this file, or run:  run_safe.bat "D:\Projects\Tower\Raft.FDB" 200
rem Second argument = net allowable soil pressure kN/m2 (default 200 - change it from the soil report!)
setlocal
if "%~1"=="" (
  echo Drag a .FDB file onto run_safe.bat
  pause
  exit /b 1
)
set QALLOW=%~2
if "%QALLOW%"=="" set QALLOW=200
python -m pip install -q comtypes openpyxl ezdxf matplotlib
python "%~dp0safe_live.py" --fdb "%~f1" --q-allow %QALLOW% --project "%~n1" --project-code PRJ -o "%~dp1%~n1_design"
echo.
echo Results in "%~dp1%~n1_design"
pause
