# 太空舰队大战三体人

一个使用 Pygame 编写的轻量太空射击游戏，包含：

- 无尽模式敌机刷新与难度递增
- 玩家生命值、攻击力成长、连击分数
- EMP 技能（清弹 + 全屏伤害 + 短暂无敌）
- 带动画效果的主菜单入口界面
- 结算页与快速重开
- 网页版支持（可在手机浏览器游玩）

## 运行方式

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动游戏

```bash
python main.py
```

## 操作说明

- 移动：WASD 或 方向键
- 射击：自动发射
- 技能 EMP：F（网页版可点右下角按钮）
- 结算后重开：R
- 结算返回菜单：ESC

## 网页版打包（手机可玩）

1. 安装网页构建依赖

```bash
pip install -r requirements-web.txt
```

2. 在项目目录执行打包

```bash
pygbag --build main.py
```

Windows 本地若遇到 `UnicodeDecodeError: 'gbk' codec can't decode ...`，请改用：

```powershell
./build_web.ps1
```

3. 本地预览

打包后，在项目目录执行：

```powershell
./preview_web.ps1
```

然后打开浏览器访问 `http://localhost:8000` 即可预览网页版游戏。

此命令会在 `build/web` 目录启动 HTTP 服务器，可用于本地测试。生成的内容也可部署到 GitHub Pages、Vercel、Netlify。

说明：浏览器环境通常拿不到 Windows 自带的中文字体。本项目现在已内置 `assets/fonts/NotoSansCJKsc-Regular.otf` 作为网页端中文字体；如果这个文件缺失，网页版会自动切换到英文界面，避免中文显示成方块。

## 手机上游玩

- 打开你部署后的网页链接即可游玩。
- 操作方式：手指在屏幕上拖动控制飞机移动，右下角 EMP 按钮释放技能。
