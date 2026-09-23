# 一键同步到 GitHub

## 三种方式

### 方式 1：双击运行
双击 `sync.bat`，输入提交说明即可。

### 方式 2：命令行一行搞定
```powershell
cd "F:\dsh harness work" && git add -A && git commit -m "更新代码" && git push origin main
```

### 方式 3：告诉 AI 助手
对我说 **"同步"** 或 **"push"** 或 **"推送到 GitHub"**，我会自动帮你完成。

## 注意事项
- Token 已配置在本地 `.git/config`，无需重复输入
- 图片、缓存、日志等自动忽略
- 代码、配置、归档、提示词记录都会上传
