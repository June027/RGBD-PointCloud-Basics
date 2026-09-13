@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0rgbd_to_pointcloud.py"
) else (
  python "%~dp0rgbd_to_pointcloud.py"
)
if errorlevel 1 (
  echo Install dependencies with: pip install -r requirements.txt
  pause
  exit /b 1
)
start "" "%~dp0results\viewer.html"
pause
