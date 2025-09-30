@echo off

cd %~dp0

pushd ..\nvim-portable

call start-shell.bat
popd

call .venv\Scripts\activate.bat
start "" goneovim.exe
exit /b
