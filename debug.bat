@echo off

cd "F:\dsh harness work"

echo Current dir: %CD%

set GIT=C:\Users\Ë®ÖóÓãd\AppData\Local\Programs\Git\cmd\git.exe

echo Git path: %GIT%

dir "F:\dsh harness work" > nul 2>&1

if errorlevel 1 echo Dir not found

if not errorlevel 1 echo Dir exists

pause