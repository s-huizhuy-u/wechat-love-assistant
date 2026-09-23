# 一键同步到 GitHub
# 用法: pwsh -File sync.ps1 "提交说明"

$ErrorActionPreference = "Stop"

$git = "C:\Users\水煮鱼d\AppData\Local\Programs\Git\cmd\git.exe"
$workdir = "F:\dsh harness work"
Set-Location $workdir

$msg = if ($args.Count -gt 0) { $args[0] } else { "更新代码" }

Write-Output "[Sync] Adding changes..."
& $git add -A

Write-Output "[Sync] Committing..."
& $git -c user.name="s-huizhuy-u" -c user.email="s-huizhuy-u@github.com" commit -m $msg 2>$null

Write-Output "[Sync] Pushing..."
& $git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Output "DONE - synced to GitHub"
} else {
    Write-Output "FAILED - check error above"
}