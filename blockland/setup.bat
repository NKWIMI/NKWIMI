@echo off
REM ============================================================
REM  Blockland - one-time setup on a new Windows computer
REM  Double-click this file, or run:  setup.bat
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/6] Checking the tools...
where py >nul 2>nul || (echo   Python 3.13 is missing. Install it:  winget install -e --id Python.Python.3.13 & goto :fail)
where node >nul 2>nul || (echo   Node.js is missing. Install it:  winget install -e --id OpenJS.NodeJS.LTS & goto :fail)
where git >nul 2>nul || (echo   Git is missing ^(needed for one package^). Install it:  winget install -e --id Git.Git & goto :fail)
py -3.13 --version || (echo   Python 3.13 is needed: winget install -e --id Python.Python.3.13 & goto :fail)

echo.
echo [2/6] Creating the Python environment (venv)...
if not exist venv\Scripts\python.exe py -3.13 -m venv venv || goto :fail
call venv\Scripts\activate.bat

echo.
echo [3/6] Installing Python packages (10-30 minutes the first time)...
python -m pip install --upgrade pip
pip install -r requirements.txt || goto :fail

echo.
echo [4/6] Installing the blockchain tools (Hardhat)...
if exist package.json call npm install
pushd blockchain
call npm install || (popd & goto :fail)
call npx hardhat compile || (popd & goto :fail)
popd

echo.
echo [5/6] Settings files...
if not exist .env (copy .env.example .env >nul & echo   Created .env  -  OPEN IT AND FILL IN THE VALUES) else (echo   .env already exists - kept)
if not exist blockchain\.env (copy blockchain\.env.example blockchain\.env >nul & echo   Created blockchain\.env  -  fill in PRIVATE_KEY) else (echo   blockchain\.env already exists - kept)

echo.
echo [6/6] Creating the database tables...
python manage.py migrate || goto :fail

echo.
echo ============================================================
echo  Setup finished. Next steps are in SETUP.md:
echo   - fill in .env and blockchain\.env
echo   - start Ganache and CouchDB
echo   - deploy the contract, then: run.bat
echo ============================================================
pause
exit /b 0

:fail
echo.
echo  SETUP STOPPED - read the message above.
pause
exit /b 1
