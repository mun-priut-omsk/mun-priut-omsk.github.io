@echo off
chcp 65001 >nul
set "DOG_PYTHONW=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if not exist "%DOG_PYTHONW%" (
  echo Не найден Python для редактора. Сообщите об этом в чате.
  pause
  exit /b 1
)
start "" "%DOG_PYTHONW%" "%~dp0manage.py"
