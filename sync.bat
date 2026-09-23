@echo off
chcp 65001 >nul
setlocal

REM 一键同步到 GitHub
REM 用法: 双击运行，或 "同步.bat [提交说明]"

cd /d "%~dp0"

set "MSG=%~1"
if "%MSG%"=="" set "MSG=更新代码"

echo [同步] 添加变更...
git add -A

echo [同步] 提交...
git commit -m "%MSG%" 2>nul

echo [同步] 推送...
git push origin main

if %errorlevel% equ 0 (
    echo.
    echo ✅ 同步完成！
) else (
    echo.
    echo ❌ 同步失败，请检查网络或 token 权限
)
pause
