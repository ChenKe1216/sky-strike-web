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

3. 本地预览

```bash
pygbag main.py
```

执行后会生成 `build/web` 目录，可将里面内容部署到 GitHub Pages、Vercel、Netlify。

说明：浏览器环境通常拿不到 Windows 自带的中文字体。如果项目里没有额外打包可分发的中文字体文件（例如 `assets/fonts/NotoSansSC-Regular.ttf`），网页版会自动切换到英文界面，避免中文显示成方块。

## 手机上游玩

- 打开你部署后的网页链接即可游玩。
- 操作方式：手指在屏幕上拖动控制飞机移动，右下角 EMP 按钮释放技能。
