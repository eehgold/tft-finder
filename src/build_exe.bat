@echo off
setlocal
cd /d "%~dp0"

set "WORK_DIR=.build\work"
set "APP_VERSION="

for /f "tokens=1,2,* delims= " %%A in ('findstr /B /C:"APP_VERSION" app.py') do (
  set "APP_VERSION=%%C"
)
set "APP_VERSION=%APP_VERSION:"=%"
for /f "tokens=* delims= " %%V in ("%APP_VERSION%") do set "APP_VERSION=%%V"

if "%APP_VERSION%"=="" (
  echo Could not read APP_VERSION from app.py
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
