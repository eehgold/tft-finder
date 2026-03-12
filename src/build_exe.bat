@echo off
setlocal
cd /d "%~dp0"

set "WORK_DIR=.build\work"

echo [1/2] Checking PyInstaller...
python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
  echo PyInstaller not found. Installing...
  python -m pip install pyinstaller
  if errorlevel 1 goto :error
)

echo [2/2] Building TFT-Finder.exe...
if not exist "data\icons\app.ico" (
  echo Missing icon: data\icons\app.ico
  goto :error
)
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "TFT-Finder" ^
  --icon "data\icons\app.ico" ^
  --add-data "data;data" ^
  --distpath ".." ^
  --workpath "%WORK_DIR%" ^
  app.py
if errorlevel 1 goto :error

echo Build successful.
echo Executable: ..\TFT-Finder.exe
exit /b 0

:error
echo Build failed.
exit /b 1
