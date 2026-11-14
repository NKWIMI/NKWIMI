@echo off
REM ============================================================
REM  Ebola Guard - build a release APK
REM  Double-click this file (or run it from cmd).
REM  Result: Desktop\EbolaGuard-APK\EbolaGuard-<version>.apk
REM ============================================================
setlocal
set PATH=%PATH%;C:\src\flutter\bin;C:\src\flutter\bin\mingit\cmd
cd /d "%~dp0.."

echo.
echo === 1/4  Getting packages ===
call flutter pub get || goto :error

echo.
echo === 2/4  Running tests ===
call flutter test || goto :error

echo.
echo === 3/4  Building release APK (takes a few minutes) ===
set DEFINES=
if exist config\release.json set DEFINES=--dart-define-from-file=config/release.json
call flutter build apk --release %DEFINES% || goto :error

echo.
echo === 4/4  Copying the APK to your Desktop ===
for /f "tokens=2" %%v in ('findstr /b "version:" pubspec.yaml') do set VER=%%v
set OUT=%USERPROFILE%\Desktop\EbolaGuard-APK
if not exist "%OUT%" mkdir "%OUT%"
copy /y "build\app\outputs\flutter-apk\app-release.apk" "%OUT%\EbolaGuard-%VER%.apk" >nul || goto :error

echo.
echo ============================================================
echo  DONE:  %OUT%\EbolaGuard-%VER%.apk
echo  Next: upload it to Google Drive as a NEW VERSION of the
echo  same file (right-click - Manage versions), so the link
echo  in your questionnaire keeps working.
echo ============================================================
explorer "%OUT%"
pause
exit /b 0

:error
echo.
echo ************************************************************
echo  FAILED. Scroll up, copy the red error text and send it
echo  to Claude.
echo ************************************************************
pause
exit /b 1
