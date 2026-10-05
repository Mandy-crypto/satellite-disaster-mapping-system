@echo off
setlocal
cd /d "%~dp0"
python run_demo.py %*
if errorlevel 1 (
  echo Demo failed. Make sure the project dependencies are installed.
  exit /b 1
)
endlocal
