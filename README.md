# 代码仓库

## 目录结构

```
├── wechat-love-assistant/    # 微信恋爱助手（主项目）
│   ├── app.py                # 主程序
│   ├── README.md             # 项目说明
│   ├── requirements.txt      # Python 依赖
│   ├── 使用说明.md
│   ├── 启动.bat
│   ├── screenshots/          # 截图记录
│   └── __pycache__/          # Python 缓存（已忽略）
├── tools/                    # 工具脚本
│   ├── download-repo.cjs     # 仓库下载脚本 (CommonJS)
│   ├── download-repo.mjs     # 仓库下载脚本 (ESM)
│   ├── vision-test.mjs       # 视觉测试工具
│   ├── heart.html            # 爱心动画页面
│   └── heart.py              # 爱心生成脚本
├── configs/                  # 配置文件
│   ├── settings.optimized.yaml
│   └── settings.original-backup.yaml
├── archives/                 # 归档文件
│   └── goutoujunshi.zip      # 勾勾军师项目备份
├── .gitignore
└── README.md
```

## 快速开始

### 微信恋爱助手
```bash
cd wechat-love-assistant
pip install -r requirements.txt
python app.py
# 或直接双击 启动.bat
```

## 说明

- 所有 Python 缓存 (`__pycache__/`) 已自动忽略
- 截图文件已忽略，保留文本记录
- 配置文件存放在 `configs/` 目录
- 工具脚本存放在 `tools/` 目录
