@echo off
REM ============================================================
REM  Ebola Guard - run the app for testing
REM  Starts the emulator if no phone/emulator is connected,
REM  then runs the app. In the window: r = reload, q = quit.
REM ============================================================
setlocal
set PATH=%PATH%;C:\src\flutter\bin;C:\src\flutter\bin\mingit\cmd
cd /d "%~dp0.."
set ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe

"%ADB%" start-server >nul 2>&1
"%ADB%" devices | findstr /r /c:"	device$" >nul
if errorlevel 1 (
  echo Starting the emulator, please wait...
  start "Emulator" "%LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe" -avd Medium_Phone_API_37.0
  "%ADB%" wait-for-device
  echo Waiting for Android to finish starting...
  timeout /t 30 /nobreak >nul
)

call flutter pub get
call flutter run
pause
