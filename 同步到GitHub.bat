@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo ========================================
echo   同步代码到 GitHub
echo ========================================
echo.

echo [1/4] 检查状态...
git status --short
echo.

echo [2/4] 添加所有变更...
git add -A
echo.

echo [3/4] 提交...
set /p msg="请输入提交说明（直接回车用默认）："
if "%msg%"=="" set msg=更新代码 %date% %time%
git commit -m "%msg%"
if errorlevel 1 (
    echo.
    echo 没有需要提交的变更，直接推送...
)

echo.
echo [4/4] 推送到 GitHub...
git push origin main

echo.
echo ========================================
if errorlevel 1 (
    echo   推送失败，请检查上面的错误信息
) else (
    echo   同步完成！
)
echo ========================================
echo.
pause
