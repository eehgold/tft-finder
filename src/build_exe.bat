@echo off
setlocal
cd /d "%~dp0"

set "WORK_DIR=.build\work"
set "APP_VERSION=1.0.0"

if "%APP_VERSION%"=="" (
  echo APP_VERSION is empty in build_exe.bat
  goto :error
)

set "APP_EXE_NAME=TFT-Finder-v%APP_VERSION%"

echo [1/2] Checking PyInstaller...
python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
  echo PyInstaller not found. Installing...
  python -m pip install pyinstaller
  if errorlevel 1 goto :error
)

echo [2/2] Building %APP_EXE_NAME%.exe...
if not exist "data\icons\app.ico" (
  echo Missing icon: data\icons\app.ico
  goto :error
)
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "%APP_EXE_NAME%" ^
  --icon "data\icons\app.ico" ^
  --add-data "data;data" ^
  --distpath ".." ^
  --workpath "%WORK_DIR%" ^
  app.py
if errorlevel 1 goto :error

echo Build successful.
echo Executable: ..\%APP_EXE_NAME%.exe
exit /b 0

:error
echo Build failed.
exit /b 1
