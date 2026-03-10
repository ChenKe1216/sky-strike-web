<<<<<<< HEAD
# sky-strike-web
=======
# 飞机大战（无尽模式）

一个使用 Pygame 编写的轻量飞机大战小游戏，包含：

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

## 手机上游玩

- 打开你部署后的网页链接即可游玩。
- 操作方式：手指在屏幕上拖动控制飞机移动，右下角 EMP 按钮释放技能。
>>>>>>> 266aa41 (first upload)
