"""太空舰队大战三体人 - 基于 Pygame 的无尽射击游戏

游戏特性：
  - 无尽模式：敌机不断刷新，难度持续增加
  - 玩家成长：击杀敌机获得分数，累积分数升级以提升攻击力
  - 特殊技能：EMP 技能可清除全屏敌弹并伤害敌机
  - 掉落系统：击杀敌机可能掉落加弹道、恢复生命值的 buff
  - 历史记录：保存历史成绩排行（Top 10）
  - 网页版支持：可通过 pygbag 打包为网页版，手机浏览器可玩

第三方库说明：
    - pygame: 游戏引擎库，负责窗口、输入事件、图形绘制、声音播放与碰撞矩形
    - pygbag: 网页构建工具（不在运行时导入），用于把 pygame 项目打包到浏览器环境

主要类:
  - Particle: 爆炸粒子效果
  - Bullet: 子弹（玩家和敌机都有）
  - Enemy: 敌机（包括普通敌机和 Boss）
  - Pickup: 掉落物（buff）
  - Player: 玩家飞机
  - Game: 主游戏逻辑控制
"""

import math
import json
import os
import random
import sys
from array import array
from dataclasses import dataclass

import pygame

# 第三方库导入说明：
# pygame 是本项目运行时唯一必须的第三方库。
# 其余导入均为 Python 标准库。

IS_WEB = sys.platform in ("emscripten", "wasi") or hasattr(sys, "_emscripten_info")
if IS_WEB:
    import asyncio


WIDTH, HEIGHT = 410, 720
FPS = 50 if IS_WEB else 60
RECORD_FILE = "records.json"
MAX_RECORDS = 10
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CJK_FONT_FILES = (
    os.path.join("assets", "fonts", "NotoSansSC-Regular.ttf"),
    os.path.join("assets", "fonts", "NotoSansSC-Medium.ttf"),
    os.path.join("assets", "fonts", "NotoSansCJKsc-Regular.otf"),
    os.path.join("assets", "fonts", "SourceHanSansSC-Regular.otf"),
    "NotoSansSC-Regular.ttf",
    "NotoSansSC-Medium.ttf",
    "NotoSansCJKsc-Regular.otf",
    "SourceHanSansSC-Regular.otf",
)


@dataclass
class Particle:
    """爆炸粒子：用于显示爆炸效果的粒子
    
    属性：
        x, y: 粒子当前位置
        vx, vy: 粒子速度（像素/秒）
        life: 粒子剩余生命（秒）
        max_life: 粒子初始生命（用于透明度计算）
        color: 粒子颜色 (R, G, B)
        size: 粒子初始大小（像素）
    """
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple
    size: float

    def update(self, dt):
        """更新粒子状态：位置、速度、生命
        
        Args:
            dt: 帧时间间隔（秒）
        """
        self.x += self.vx * dt  # 水平移动
        self.y += self.vy * dt  # 竖直移动
        self.vy += 140 * dt     # 重力加速度（下落效果）
        self.life -= dt         # 生命递减

    def draw(self, screen):
        t = max(0.0, self.life / self.max_life)
        radius = max(1, int(self.size * t))
        alpha = int(220 * t)
        surf = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (radius + 1, radius + 1), radius)
        screen.blit(surf, (self.x - radius, self.y - radius))


class Bullet:
    """子弹类：包括玩家子弹和敌机子弹
    
    属性：
        x, y: 子弹位置
        vx, vy: 子弹速度（像素/秒）
        dmg: 子弹伤害值
        friendly: True 表示玩家子弹，False 表示敌机子弹
        alive: 子弹是否存活（超出屏幕会被标记为死亡）
        radius: 子弹碰撞半径（用于判定伤害和碰撞）
    """
    def __init__(self, x, y, vy, dmg, friendly=True, vx=0.0):
        """初始化子弹
        
        Args:
            x, y: 起始位置
            vy: 竖直速度（负数表示向上，正数表示向下）
            dmg: 伤害值
            friendly: 是否是玩家子弹（默认 True）
            vx: 水平速度（默认 0，用于敌机斜射）
        """
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.dmg = dmg
        self.friendly = friendly
        self.alive = True
        self.radius = 4 if friendly else 6

    @property
    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < -30 or self.y > HEIGHT + 30 or self.x < -40 or self.x > WIDTH + 40:
            self.alive = False

    def draw(self, screen):
        if self.friendly:
            nose = (235, 248, 255)
            body = (120, 215, 245)
            trail = (75, 145, 190)
            x = int(self.x)
            y = int(self.y)
            pygame.draw.polygon(screen, trail, [(x - 2, y + 10), (x + 2, y + 10), (x, y + 18)])
            pygame.draw.rect(screen, body, (x - 2, y - 8, 4, 14), border_radius=2)
            pygame.draw.polygon(screen, body, [(x - 4, y - 2), (x + 4, y - 2), (x, y + 2)])
            pygame.draw.polygon(screen, nose, [(x - 2, y - 8), (x + 2, y - 8), (x, y - 13)])
        else:
            color = (255, 130, 80)
            trail = (170, 80, 55)
            pygame.draw.circle(screen, trail, (int(self.x), int(self.y - 8)), self.radius)
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)


class Enemy:
    """敌机类：包括三种小敌机和 Boss
    
    敌机类型（kind）:
        "scout": 侦察机 - 快速、血量少、火力快
        "fighter": 战斗机 - 平衡型（大多数小敌机）
        "tank": 坦克 - 慢速、血量多、火力强
        "boss": Boss 
    
    属性：
        x, y: 敌机位置
        w, h: 敌机尺寸（用于渲染和碰撞）
        speed: 敌机移动速度
        max_hp, hp: 敌机生命值
        shoot_cd, shoot_t: 开火冷却（秒）
        is_boss: 是否是 Boss
        fire_mode: 开火模式（"single"、"fast"、"dual"、"boss"）
    """
    def __init__(self, level=1, kind="fighter", is_boss=False):
        self.kind = kind
        self.is_boss = is_boss
        self.fire_mode = "single"
        self.x = random.randint(30, WIDTH - 30)
        self.y = random.randint(-220, -40)

        if is_boss:
            self.w = 96
            self.h = 74
            self.speed = 60 + level * 1.5
            self.max_hp = 920 + level * 52
            self.shoot_cd = 0.72
            self.fire_mode = "boss"
        elif kind == "scout":
            self.w = random.randint(30, 40)
            self.h = random.randint(22, 30)
            self.speed = random.uniform(195, 260) + level * 4.8
            self.max_hp = random.randint(14, 24) + level * 2
            self.shoot_cd = random.uniform(0.95, 1.45)
            self.fire_mode = "fast"
        elif kind == "tank":
            self.w = random.randint(52, 66)
            self.h = random.randint(38, 50)
            self.speed = random.uniform(90, 130) + level * 3.2
            self.max_hp = random.randint(52, 76) + level * 5
            self.shoot_cd = random.uniform(1.35, 1.95)
            self.fire_mode = "dual"
        else:
            self.w = random.randint(38, 54)
            self.h = random.randint(30, 42)
            self.speed = random.uniform(130, 188) + level * 4.2
            self.max_hp = random.randint(24, 44) + level * 3
            self.shoot_cd = random.uniform(1.0, 1.7)
            self.fire_mode = "single"

        self.hp = self.max_hp
        self.shoot_t = random.uniform(0.2, 1.5)
        self.alive = True
        self.phase = random.random() * math.tau

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)

    def update(self, dt):
        self.phase += dt
        if self.is_boss:
            self.x += math.sin(self.phase * 1.6) * 42 * dt
            self.x = max(66, min(WIDTH - 66, self.x))
        self.y += self.speed * dt
        self.shoot_t -= dt
        if self.y > HEIGHT + 60:
            self.alive = False

    def draw(self, screen):
        body = self.rect
        if self.is_boss:
            color = (188, 68, 88)
            wing = (226, 110, 128)
            pygame.draw.rect(screen, color, body, border_radius=8)
            pygame.draw.polygon(screen, wing, [(body.left - 18, body.centery + 8), (body.left + 8, body.top + 14), (body.left + 8, body.bottom - 4)])
            pygame.draw.polygon(screen, wing, [(body.right + 18, body.centery + 8), (body.right - 8, body.top + 14), (body.right - 8, body.bottom - 4)])
            pygame.draw.circle(screen, (255, 212, 120), (body.centerx, body.centery), 7)
        else:
            if self.kind == "scout":
                color = (255, 120, 98)
            elif self.kind == "tank":
                color = (196, 80, 120)
            else:
                color = (220, 75, 80)
            pygame.draw.polygon(
                screen,
                color,
                [
                    (body.centerx, body.top),
                    (body.right, body.centery + 6),
                    (body.centerx, body.bottom),
                    (body.left, body.centery + 6),
                ],
            )
        hp_ratio = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(screen, (45, 30, 40), (body.left, body.top - 8, body.width, 4), border_radius=2)
        pygame.draw.rect(screen, (255, 160, 120), (body.left, body.top - 8, int(body.width * hp_ratio), 4), border_radius=2)


class Pickup:
    """掉落物（Buff）：敌机击杀时可能掉落
    
    掉落类型（kind）:
        "multishot": 加弹道 - 增加一条射击弹道（最多 5 条）
        "heal": 恢复生命 - 恢复玩家 22 点生命值
    
    属性：
        x, y: 掉落物位置
        kind: 掉落物类型
        speed: 下落速度（像素/秒）
        alive: 是否存活（超出屏幕或被拾取会标记为死亡）
        radius: 掉落物碰撞半径
    """
    _label_font = None  # 类变量：缓存字体对象，用于显示 "+B" 或 "+H" 标签

    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind  # "multishot" or "heal"
        self.speed = 150
        self.alive = True
        self.radius = 13 if kind == "multishot" else 11

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt):
        self.y += self.speed * dt
        if self.y > HEIGHT + 24:
            self.alive = False

    def draw(self, screen, t):
        pulse = 0.85 + 0.15 * math.sin(t * 8 + self.x * 0.02)
        r = max(8, int(self.radius * pulse))
        if self.kind == "multishot":
            outer, inner = (255, 220, 120), (255, 168, 66)
            label = "+B"
        else:
            outer, inner = (120, 255, 175), (70, 205, 130)
            label = "+H"
        pygame.draw.circle(screen, outer, (int(self.x), int(self.y)), r)
        pygame.draw.circle(screen, inner, (int(self.x), int(self.y)), max(6, r - 4))
        if Pickup._label_font is None:
            Pickup._label_font = pygame.font.SysFont("consolas", 14, bold=True)
        txt = Pickup._label_font.render(label, True, (30, 35, 45))
        screen.blit(txt, (int(self.x - txt.get_width() / 2), int(self.y - txt.get_height() / 2)))


class Player:
    """玩家飞机类
    
    属性：
        x, y: 玩家位置
        w, h: 玩家尺寸（用于渲染和碰撞）
        speed: 移动速度（像素/秒）
        max_hp, hp: 生命值
        attack: 攻击力（影响子弹伤害）
        level: 等级（提升攻击力和连击分数倍数）
        fire_cd, fire_t: 开火冷却（秒）
        bullet_lanes: 弹道数（1-5）
        invuln: 无敌剩余时间（被击中时设为 2.0 秒）
        skill_t, skill_cd: EMP 技能冷却（秒）
    """
    def __init__(self):
        """初始化玩家飞机"""
        self.x = WIDTH // 2
        self.y = HEIGHT - 90
        self.w = 40
        self.h = 46
        self.speed = 380
        self.max_hp = 100
        self.hp = self.max_hp
        self.attack = 14
        self.level = 1
        self.fire_cd = 0.16
        self.fire_t = 0.0
        self.base_lanes = 2
        self.bullet_lanes = self.base_lanes
        self.invuln = 0.0
        self.skill_cd = 9.0
        self.skill_t = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)

    def update(self, dt, keys):
        dx = 0
        dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1

        if dx != 0 and dy != 0:
            inv = 1 / math.sqrt(2)
            dx *= inv
            dy *= inv

        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        self.x = max(28, min(WIDTH - 28, self.x))
        self.y = max(38, min(HEIGHT - 30, self.y))

        self.fire_t = max(0.0, self.fire_t - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.skill_t = max(0.0, self.skill_t - dt)

    def draw(self, screen, t):
        body = self.rect
        x = body.centerx
        wing_shift = int(math.sin(t * 7.5) * 2)

        # Fighter silhouette with fuselage, wings, canopy and engine flame.
        pygame.draw.polygon(
            screen,
            (42, 92, 132),
            [
                (x, body.top),
                (x + 8, body.top + 11),
                (x + 10, body.bottom - 8),
                (x, body.bottom),
                (x - 10, body.bottom - 8),
                (x - 8, body.top + 11),
            ],
        )
        pygame.draw.polygon(
            screen,
            (68, 176, 225),
            [
                (x - 18, body.centery + 7 + wing_shift),
                (x - 2, body.centery - 3),
                (x - 3, body.centery + 15),
            ],
        )
        pygame.draw.polygon(
            screen,
            (68, 176, 225),
            [
                (x + 18, body.centery + 7 + wing_shift),
                (x + 2, body.centery - 3),
                (x + 3, body.centery + 15),
            ],
        )
        pygame.draw.polygon(
            screen,
            (92, 205, 245),
            [
                (x, body.top + 4),
                (x + 5, body.top + 16),
                (x, body.top + 20),
                (x - 5, body.top + 16),
            ],
        )
        flame_h = 8 + int(abs(math.sin(t * 16)) * 4)
        pygame.draw.polygon(
            screen,
            (255, 175, 90),
            [(x - 3, body.bottom - 3), (x + 3, body.bottom - 3), (x, body.bottom + flame_h)],
        )

        if self.invuln > 0:
            pulse = 40 + int(30 * abs(math.sin(t * 16)))
            pygame.draw.circle(screen, (120, 230, 255, pulse), (int(self.x), int(self.y)), 34, width=2)


class Game:
    """主游戏类：控制游戏的整体流程和状态
    
    游戏状态（state）:
        "menu": 菜单界面
        "playing": 游戏进行中
        "paused": 暂停
        "settings": 音频设置界面
        "game_over": 游戏结束
    
    主要负责：
        - 事件处理（键盘、鼠标、触摸）
        - 游戏逻辑更新（敌机生成、碰撞、伤害等）
        - 界面渲染（菜单、游戏界面、结算界面）
        - 音频管理（BGM、音效）
        - 历史记录保存
    """
    def __init__(self):
        # pygame 初始化流程：启动视频/输入子系统并创建主窗口。
        pygame.init()
        pygame.display.set_caption("太空舰队大战三体人 - 无尽模式")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.audio_ready = False
        self.music_started = False
        self.bgm_channel = None
        self.bgm_sound = None
        self.sfx_button = None
        self.sfx_kill = None
        self.sfx_hurt = None
        self.sfx_boss = None
        self.bgm_volume = 0.24
        self.sfx_volume = 0.42
        self.bgm_enabled = True
        self.sfx_enabled = True
        self.dragging_slider = None

        if not IS_WEB:
            self.setup_audio()

        self.cjk_font_path = self.find_cjk_font_asset()
        self.ascii_ui = IS_WEB and self.cjk_font_path is None
        if IS_WEB and self.cjk_font_path is None:
            print("[web-font] No bundled CJK font asset found; falling back to ASCII UI.")
        elif IS_WEB:
            print(f"[web-font] Using bundled CJK font: {os.path.basename(self.cjk_font_path)}")
        self.title_font = self.load_ui_font(48, bold=True, prefer_cjk=True)
        self.menu_title_font = self.load_ui_font(34, bold=True, prefer_cjk=True)
        self.h1_font = self.load_ui_font(24, bold=True, prefer_cjk=True)
        self.ui_font = self.load_ui_font(22, prefer_cjk=True)
        self.small_font = self.load_ui_font(18, mono=True)
        self.small_font_cjk = self.load_ui_font(20, prefer_cjk=True)

        self.bg_base = self.build_bg_base()
        star_count = 36 if IS_WEB else 90
        big_star_count = 10 if IS_WEB else 24
        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(35, 180)] for _ in range(star_count)]
        self.big_stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(12, 28)] for _ in range(big_star_count)]

        self.running = True
        self.state = "menu"
        self.time = 0.0
        self.menu_flash = 0.0

        self.start_button = pygame.Rect(WIDTH // 2 - 100, 280, 200, 52)
        self.quit_button = pygame.Rect(WIDTH // 2 - 100, 344, 200, 46)
        self.settings_button = pygame.Rect(WIDTH // 2 - 100, 400, 200, 42)
        self.skill_button = pygame.Rect(WIDTH - 78, HEIGHT - 78, 58, 58)
        self.pause_button = pygame.Rect(WIDTH - 144, HEIGHT - 78, 58, 58)
        self.home_button = pygame.Rect(20, HEIGHT - 78, 58, 58)
        self.settings_back_button = pygame.Rect(WIDTH // 2 - 90, HEIGHT - 88, 180, 44)
        self.bgm_toggle_button = pygame.Rect(42, 246, WIDTH - 84, 44)
        self.sfx_toggle_button = pygame.Rect(42, 306, WIDTH - 84, 44)
        self.bgm_slider_rect = pygame.Rect(42, 392, WIDTH - 84, 12)
        self.sfx_slider_rect = pygame.Rect(42, 448, WIDTH - 84, 12)
        self.touch_active = False
        self.touch_pos = (WIDTH // 2, HEIGHT - 90)
        self.history_page = 0
        self.history_page_size = 2
        self.history_panel_rect = pygame.Rect(0, 0, 0, 0)
        self.history_drag_start_y = None
        self.history_dragging = False

        self.history = self.load_history()

        self.reset_game()

    def find_cjk_font_asset(self):
        for relative_path in CJK_FONT_FILES:
            font_path = os.path.join(PROJECT_DIR, relative_path)
            if os.path.exists(font_path):
                return font_path
        return None

    def load_ui_font(self, size, bold=False, prefer_cjk=False, mono=False):
        if prefer_cjk and self.cjk_font_path is not None:
            font = pygame.font.Font(self.cjk_font_path, size)
            font.set_bold(bold)
            return font

        if mono:
            candidates = ["consolas", "couriernew", "dejavusansmono", "liberationmono"]
        elif prefer_cjk:
            candidates = [
                "microsoftyaheiui",
                "microsoftyahei",
                "notosanscjksc",
                "sourcehansanssc",
                "simhei",
                "arialunicode",
                "arial",
            ]
        else:
            candidates = ["consolas", "arial", "dejavusans"]

        for name in candidates:
            matched = pygame.font.match_font(name, bold=bold)
            if matched:
                font = pygame.font.Font(matched, size)
                font.set_bold(bold)
                return font

        font = pygame.font.Font(None, size)
        font.set_bold(bold)
        return font

    def set_touch_from_finger(self, fx, fy):
        # Pygame finger coordinates are normalized to [0, 1].
        self.touch_pos = (int(fx * WIDTH), int(fy * HEIGHT))

    def try_touch_action(self, pos):
        if self.home_button.collidepoint(pos):
            self.play_button_sfx()
            self.save_current_run_if_needed()
            self.state = "menu"
            self.stop_bgm()
            self.touch_active = False
            self.set_bgm_paused(False)
            return True
        if self.pause_button.collidepoint(pos):
            self.play_button_sfx()
            self.state = "playing" if self.state == "paused" else "paused"
            self.set_bgm_paused(self.state == "paused")
            return True
        if self.state == "playing" and self.skill_button.collidepoint(pos):
            self.play_button_sfx()
            self.cast_emp()
            return True
        return False

    def setup_audio(self):
        """初始化音频系统并创建 BGM 和音效
        
        - 网页端采用较低的采样率（11025 Hz）以减少加载时间
        - 桌面端使用较高采样率（22050 Hz）以获得更好音质
        """
        if self.audio_ready:
            return  # 已初始化过，直接返回
        try:
            if not pygame.mixer.get_init():
                # Use a lighter mixer config on web to improve startup speed.
                if IS_WEB:
                    pygame.mixer.init(frequency=11025, size=-16, channels=1)
                else:
                    pygame.mixer.init(frequency=22050, size=-16, channels=1)
            self.bgm_sound = self.create_bgm_sound()
            self.sfx_button = self.create_tone_sound(920, 0.08, 2400)
            self.sfx_kill = self.create_tone_sound(420, 0.12, 3600, 760)
            self.sfx_hurt = self.create_tone_sound(180, 0.14, 4200, 120)
            self.sfx_boss = self.create_tone_sound(120, 0.45, 4300, 260)
            self.audio_ready = True
        except pygame.error:
            self.bgm_sound = None
            self.sfx_button = None
            self.sfx_kill = None
            self.sfx_hurt = None
            self.sfx_boss = None
            self.audio_ready = False

    def create_bgm_sound(self):
        """合成背景音乐
        
        使用和弦+旋律+节奏的方式生成 5-8 秒的背景音乐
        - 网页端时长为 5 秒（到达最后会循环播放）
        - 桌面端时长为 8 秒
        
        组成部分：
          - pad: 和弦垫底音（4 条音轨）
          - lead: 主旋律（8 个音符循环）
          - kick: 鼓声（低频节奏）
          - snare: 镲声（高频点缀）
          - bass: 贝司（和弦下根）
        """
        # 算法说明：采用“分轨加法合成”（pad/lead/kick/snare/bass）逐采样生成 PCM。
        # 每个采样点都按时间 t 计算波形并叠加，再裁剪到 int16 范围交给 pygame.mixer.Sound。
        sample_rate = 11025 if IS_WEB else 22050
        duration = 5.0 if IS_WEB else 8.0
        total = int(sample_rate * duration)
        notes = {
            "C4": 261.63,
            "E4": 329.63,
            "G4": 392.00,
            "A3": 220.00,
            "F4": 349.23,
            "D4": 293.66,
            "B3": 246.94,
        }
        progression = [
            [notes["A3"], notes["C4"], notes["E4"]],
            [notes["F4"], notes["A3"], notes["C4"]],
            [notes["D4"], notes["F4"], notes["A3"]],
            [notes["G4"], notes["B3"], notes["D4"]],
        ]

        melody = [notes["E4"], notes["G4"], notes["A3"], notes["C4"], notes["D4"], notes["F4"], notes["E4"], notes["C4"]]

        buf = array("h")
        beat_len = 0.25
        rng = random.Random(42)
        for i in range(total):
            t = i / sample_rate
            chord = progression[int(t // 2) % len(progression)]
            beat_idx = int(t / beat_len)
            lead = melody[beat_idx % len(melody)]
            lead_gate = 1.0 - ((t % beat_len) / beat_len)
            kick = 0.62 * math.exp(-30 * (t % 0.5)) * math.sin(2 * math.pi * (72 - 12 * (t % 0.5)) * t)
            snare_env = math.exp(-38 * ((t + 0.25) % 0.5))
            snare = (rng.uniform(-1.0, 1.0) * 0.13 + 0.03 * math.sin(2 * math.pi * 180 * t)) * snare_env
            bass = 0.42 * math.sin(2 * math.pi * (chord[0] * 0.5) * t)
            pad = (
                math.sin(2 * math.pi * chord[0] * t)
                + 0.65 * math.sin(2 * math.pi * chord[1] * t)
                + 0.45 * math.sin(2 * math.pi * chord[2] * t)
            ) / 2.1
            lead_wave = math.sin(2 * math.pi * lead * t) * (0.6 * lead_gate)
            wave = 0.38 * pad + 0.26 * lead_wave + 0.24 * kick + 0.2 * bass + snare
            val = int(5200 * wave)
            buf.append(max(-32768, min(32767, val)))

        return pygame.mixer.Sound(buffer=buf.tobytes())

    def create_tone_sound(self, freq, duration, amp, end_freq=None):
        sample_rate = 22050
        total = int(sample_rate * duration)
        buf = array("h")
        rng = random.Random(int(freq * 10 + duration * 1000))
        for i in range(total):
            t = i / sample_rate
            p = i / max(1, total - 1)
            f = freq if end_freq is None else (freq + (end_freq - freq) * p)
            env = math.exp(-5.8 * p)
            tonal = 0.72 * math.sin(2 * math.pi * f * t) + 0.21 * math.sin(2 * math.pi * f * 2.02 * t)
            noise = 0.12 * rng.uniform(-1.0, 1.0) * math.exp(-10 * p)
            wave = (tonal + noise) * env
            buf.append(int(max(-32768, min(32767, amp * wave))))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def ensure_bgm(self):
        self.setup_audio()
        if self.music_started or self.bgm_sound is None or not self.bgm_enabled:
            return
        try:
            self.bgm_sound.set_volume(self.bgm_volume)
            self.bgm_channel = self.bgm_sound.play(loops=-1)
            self.music_started = True
        except pygame.error:
            self.music_started = False

    def stop_bgm(self):
        if self.bgm_channel is not None:
            try:
                self.bgm_channel.stop()
            except pygame.error:
                pass
        self.bgm_channel = None
        self.music_started = False

    def set_bgm_paused(self, paused):
        if self.bgm_channel is None:
            return
        try:
            if paused:
                self.bgm_channel.pause()
            else:
                self.bgm_channel.unpause()
        except pygame.error:
            pass

    def apply_audio_settings(self):
        if not self.bgm_enabled:
            if self.bgm_channel is not None:
                try:
                    self.bgm_channel.stop()
                except pygame.error:
                    pass
            self.bgm_channel = None
            self.music_started = False
        else:
            if self.music_started and self.bgm_channel is not None:
                try:
                    self.bgm_channel.set_volume(self.bgm_volume)
                except pygame.error:
                    pass

    def update_slider_by_x(self, key, x):
        if key == "bgm":
            rect = self.bgm_slider_rect
            self.bgm_volume = max(0.0, min(1.0, (x - rect.left) / max(1, rect.width)))
        elif key == "sfx":
            rect = self.sfx_slider_rect
            self.sfx_volume = max(0.0, min(1.0, (x - rect.left) / max(1, rect.width)))
        self.apply_audio_settings()

    def play_button_sfx(self):
        if self.sfx_button is None or not self.sfx_enabled:
            return
        try:
            self.sfx_button.set_volume(self.sfx_volume * 0.75)
            self.sfx_button.play()
        except pygame.error:
            pass

    def play_kill_sfx(self):
        if self.sfx_kill is None or not self.sfx_enabled:
            return
        try:
            self.sfx_kill.set_volume(self.sfx_volume)
            self.sfx_kill.play()
        except pygame.error:
            pass

    def play_hurt_sfx(self):
        if self.sfx_hurt is None or not self.sfx_enabled:
            return
        try:
            self.sfx_hurt.set_volume(self.sfx_volume * 0.95)
            self.sfx_hurt.play()
        except pygame.error:
            pass

    def play_boss_sfx(self):
        if self.sfx_boss is None or not self.sfx_enabled:
            return
        try:
            self.sfx_boss.set_volume(self.sfx_volume)
            self.sfx_boss.play()
        except pygame.error:
            pass

    def tr(self, zh, en):
        return en if self.ascii_ui else zh

    def render_small(self, text, color):
        has_non_ascii = any(ord(ch) > 127 for ch in text)
        font = self.small_font_cjk if has_non_ascii else self.small_font
        return font.render(text, True, color)

    def reset_game(self):
        """重置游戏状态
        """
        self.player = Player()
        self.enemies = []
        self.pickups = []
        self.player_bullets = []
        self.enemy_bullets = []
        self.particles = []
        self.spawn_t = 0.0
        self.spawn_cd = 0.9
        self.score = 0
        self.kills = 0
        self.survive_time = 0.0
        self.combo = 0
        self.combo_t = 0.0
        self.game_over_timer = 0.0
        self.game_recorded = False
        self.next_boss_time = random.uniform(44, 56)

    def load_history(self):
        if IS_WEB:
            return []
        if not os.path.exists(RECORD_FILE):
            return []
        try:
            with open(RECORD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data[:MAX_RECORDS]
        except (OSError, json.JSONDecodeError):
            return []
        return []

    def save_history(self):
        if IS_WEB:
            return
        try:
            with open(RECORD_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history[:MAX_RECORDS], f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def append_history(self):
        """将当前游戏成绩添加到历史记录（且保存到文件）
        
        记录包含：
          - score: 最终分数
          - kills: 击杀数
          - time: 游戏执行时间
        
        记录会自动按分数排序，且仅保留前 10 条
        """
        entry = {
            "score": int(self.score),
            "kills": int(self.kills),
            "time": int(self.survive_time),
        }
        self.history.append(entry)
        # 排行算法：按分数降序排序，只保留 Top N（N=MAX_RECORDS）。
        self.history.sort(key=lambda item: item.get("score", 0), reverse=True)
        self.history = self.history[:MAX_RECORDS]
        self.save_history()

    def save_current_run_if_needed(self):
        if self.state in ("playing", "paused") and not self.game_recorded and self.survive_time > 0.5:
            self.append_history()
            self.game_recorded = True

    def add_explosion(self, x, y, count, color):
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(40, 260)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd,
                    life=random.uniform(0.35, 0.75),
                    max_life=0.75,
                    color=color,
                    size=random.uniform(2, 4),
                )
            )

    def get_alive_boss(self):
        for e in self.enemies:
            if e.alive and e.is_boss:
                return e
        return None

    def create_regular_enemy(self, level):
        roll = random.random()
        if roll < 0.38:
            kind = "scout"
        elif roll < 0.78:
            kind = "fighter"
        else:
            kind = "tank"
        return Enemy(level, kind=kind, is_boss=False)

    def spawn_enemy_shot(self, enemy):
        base_speed = 180 + self.survive_time * 1.4
        if enemy.fire_mode == "fast":
            self.enemy_bullets.append(Bullet(enemy.x, enemy.y + 14, base_speed + 65, 9, False, vx=random.uniform(-24, 24)))
        elif enemy.fire_mode == "dual":
            self.enemy_bullets.append(Bullet(enemy.x - 10, enemy.y + 18, base_speed - 5, 12, False, vx=-20))
            self.enemy_bullets.append(Bullet(enemy.x + 10, enemy.y + 18, base_speed - 5, 12, False, vx=20))
        elif enemy.fire_mode == "boss":
            spread = [-0.52, -0.26, 0.0, 0.26, 0.52]
            for a in spread:
                self.enemy_bullets.append(Bullet(enemy.x, enemy.y + 26, base_speed + 35, 13, False, vx=math.sin(a) * 170))
        else:
            self.enemy_bullets.append(Bullet(enemy.x, enemy.y + 16, base_speed, 11, False, vx=random.uniform(-12, 12)))

    def build_bg_base(self):
        grad = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            r = int(8 + 14 * y / HEIGHT)
            g = int(22 + 16 * y / HEIGHT)
            b = int(42 + 24 * y / HEIGHT)
            pygame.draw.line(grad, (r, g, b), (0, y), (WIDTH, y))

        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (55, 125, 180, 60), (-160, -120, 520, 320))
        pygame.draw.ellipse(glow, (255, 150, 90, 35), (WIDTH - 340, HEIGHT - 200, 360, 250))
        grad.blit(glow, (0, 0))
        return grad

    def draw_background(self):
        self.screen.blit(self.bg_base, (0, 0))

        for x, y, speed in self.stars:
            pygame.draw.circle(self.screen, (220, 235, 255), (int(x), int(y)), 1)
        for x, y, speed in self.big_stars:
            pygame.draw.circle(self.screen, (190, 215, 255), (int(x), int(y)), 2)

    def update_stars(self, dt):
        for s in self.stars:
            s[1] += s[2] * dt
            if s[1] > HEIGHT + 2:
                s[0] = random.randint(0, WIDTH)
                s[1] = -2
        for s in self.big_stars:
            s[1] += s[2] * dt
            if s[1] > HEIGHT + 2:
                s[0] = random.randint(0, WIDTH)
                s[1] = -2

    def draw_menu(self):
        """绘制菜单界面序列
        
        1. 背景
        2. 标题
        3. 按钮
        4. 历史成绩
        5. 操作提示
        """
        self.draw_background()

        center_x = WIDTH // 2
        wobble = int(math.sin(self.time * 2.3) * 6)
        title_text = self.tr("太空舰队大战三体人", "SPACE FLEET VS TRISOLARANS")
        title = self.menu_title_font.render(title_text, True, (240, 248, 255))
        shadow = self.menu_title_font.render(title_text, True, (70, 110, 160))
        self.screen.blit(shadow, (center_x - title.get_width() // 2 + 3, 120 + wobble + 3))
        self.screen.blit(title, (center_x - title.get_width() // 2, 120 + wobble))

        subtitle = self.ui_font.render(self.tr("无尽模式 · 刷新最高分", "ENDLESS MODE - BEAT YOUR BEST"), True, (190, 215, 245))
        self.screen.blit(subtitle, (center_x - subtitle.get_width() // 2, 205 + wobble))

        mouse_pos = pygame.mouse.get_pos()
        self.menu_flash += 0.06

        self.draw_button(self.start_button, self.tr("开始游戏", "START"), mouse_pos)
        self.draw_button(self.quit_button, self.tr("退出", "QUIT"), mouse_pos, color_base=(95, 78, 88), color_hover=(135, 95, 100))
        self.draw_button(self.settings_button, self.tr("音频设置", "AUDIO SETTINGS"), mouse_pos, color_base=(78, 108, 145), color_hover=(98, 130, 170))

        self.draw_history_panel(462, 84, self.tr("历史记录 TOP", "TOP SCORES"))

        tip1 = self.render_small(self.tr("移动: WASD / 方向键    攻击: 自动发射", "MOVE: WASD/ARROWS   FIRE: AUTO"), (175, 200, 230))
        tip2 = self.render_small(self.tr("技能EMP: F   暂停: P   菜单: H", "EMP: F   PAUSE: P   MENU: H"), (175, 200, 230))
        self.screen.blit(tip1, (center_x - tip1.get_width() // 2, HEIGHT - 88))
        self.screen.blit(tip2, (center_x - tip2.get_width() // 2, HEIGHT - 58))

    def draw_settings(self):
        """绘制音频设置界面
        
        显示下列元素：
          1. 上方是 BGM 开关按钮（强化设置会钉住音效推清）
          2. 下库是 BGM 音量滑块
          3. 再下是 SFX 开关按钮
          4. SFX 音量滑块
          5. 最下显示返回按钮
        """
        self.draw_background()
        center_x = WIDTH // 2
        title = self.title_font.render(self.tr("音频设置", "AUDIO"), True, (240, 248, 255))
        self.screen.blit(title, (center_x - title.get_width() // 2, 110))

        mouse_pos = pygame.mouse.get_pos()
        bgm_label = self.tr("背景音乐", "BGM") + ": " + (self.tr("开", "ON") if self.bgm_enabled else self.tr("关", "OFF"))
        sfx_label = self.tr("音效", "SFX") + ": " + (self.tr("开", "ON") if self.sfx_enabled else self.tr("关", "OFF"))
        self.draw_button(self.bgm_toggle_button, bgm_label, mouse_pos, color_base=(68, 120, 120), color_hover=(84, 146, 146))
        self.draw_button(self.sfx_toggle_button, sfx_label, mouse_pos, color_base=(68, 120, 120), color_hover=(84, 146, 146))

        for rect, label, value in (
            (self.bgm_slider_rect, self.tr("背景音乐音量", "BGM VOLUME"), self.bgm_volume),
            (self.sfx_slider_rect, self.tr("音效音量", "SFX VOLUME"), self.sfx_volume),
        ):
            txt = self.small_font.render(f"{label}: {int(value * 100)}%", True, (220, 236, 255))
            self.screen.blit(txt, (rect.left, rect.top - 26))
            pygame.draw.rect(self.screen, (52, 68, 90), rect, border_radius=6)
            fill_w = int(rect.width * value)
            pygame.draw.rect(self.screen, (96, 174, 225), (rect.left, rect.top, fill_w, rect.height), border_radius=6)
            knob_x = rect.left + fill_w
            pygame.draw.circle(self.screen, (240, 248, 255), (knob_x, rect.centery), 9)

        self.draw_button(self.settings_back_button, self.tr("返回主菜单", "BACK TO MENU"), mouse_pos, color_base=(86, 86, 104), color_hover=(112, 112, 134))

    def draw_touch_ui(self):
        if not IS_WEB:
            return
        # Home button
        home_surf = pygame.Surface((self.home_button.width, self.home_button.height), pygame.SRCALPHA)
        pygame.draw.circle(home_surf, (92, 104, 124, 195), (29, 29), 29)
        pygame.draw.circle(home_surf, (218, 236, 255, 200), (29, 29), 29, width=2)
        h_text = self.render_small(self.tr("主页", "HOME"), (242, 248, 255))
        home_surf.blit(h_text, (29 - h_text.get_width() // 2, 29 - h_text.get_height() // 2))
        self.screen.blit(home_surf, self.home_button.topleft)

        # Pause/Resume button
        pause_surf = pygame.Surface((self.pause_button.width, self.pause_button.height), pygame.SRCALPHA)
        pygame.draw.circle(pause_surf, (95, 120, 165, 195), (29, 29), 29)
        pygame.draw.circle(pause_surf, (218, 236, 255, 200), (29, 29), 29, width=2)
        pause_label = self.tr("继续", "PLAY") if self.state == "paused" else self.tr("暂停", "PAUSE")
        p_text = self.render_small(pause_label, (242, 248, 255))
        pause_surf.blit(p_text, (29 - p_text.get_width() // 2, 29 - p_text.get_height() // 2))
        self.screen.blit(pause_surf, self.pause_button.topleft)

        if self.state != "playing":
            return

        # EMP button
        surf = pygame.Surface((self.skill_button.width, self.skill_button.height), pygame.SRCALPHA)
        pygame.draw.circle(
            surf,
            (88, 148, 220, 200) if self.player.skill_t <= 0 else (85, 95, 120, 180),
            (self.skill_button.width // 2, self.skill_button.height // 2),
            self.skill_button.width // 2,
        )
        pygame.draw.circle(
            surf,
            (218, 236, 255, 200),
            (self.skill_button.width // 2, self.skill_button.height // 2),
            self.skill_button.width // 2,
            width=2,
        )
        text = self.small_font.render("EMP", True, (242, 248, 255))
        surf.blit(text, (self.skill_button.width // 2 - text.get_width() // 2, self.skill_button.height // 2 - text.get_height() // 2))
        self.screen.blit(surf, self.skill_button.topleft)

    def draw_history_panel(self, y, h, title):
        panel = pygame.Rect(16, y, WIDTH - 32, h)
        self.history_panel_rect = panel
        surf = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        pygame.draw.rect(surf, (15, 25, 40, 175), surf.get_rect(), border_radius=10)
        pygame.draw.rect(surf, (190, 220, 250, 120), surf.get_rect(), width=1, border_radius=10)
        self.screen.blit(surf, panel.topleft)

        title_surf = self.render_small(title, (208, 230, 250))
        self.screen.blit(title_surf, (panel.left + 10, panel.top + 6))

        if not self.history:
            empty = self.render_small(self.tr("暂无记录", "No records"), (165, 190, 210))
            self.screen.blit(empty, (panel.left + 10, panel.top + 32))
            return

        total_pages = max(1, math.ceil(len(self.history) / self.history_page_size))
        self.history_page = max(0, min(self.history_page, total_pages - 1))
        start = self.history_page * self.history_page_size
        end = min(len(self.history), start + self.history_page_size)

        rows = end - start
        old_clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(panel.left + 8, panel.top + 26, panel.width - 16, panel.height - 30))
        for i in range(rows):
            rec = self.history[start + i]
            rank = start + i + 1
            text = self.tr(
                f"{rank}. 分{rec['score']}  击落{rec['kills']}  生存{rec['time']}s",
                f"{rank}. score {rec['score']}  kill {rec['kills']}  {rec['time']}s",
            )
            line = self.render_small(text, (220, 235, 255))
            self.screen.blit(line, (panel.left + 10, panel.top + 28 + i * 20))
        self.screen.set_clip(old_clip)

        page_txt = self.small_font.render(f"{self.history_page + 1}/{total_pages}", True, (205, 228, 250))
        self.screen.blit(page_txt, (panel.right - page_txt.get_width() - 12, panel.top + 6))

    def draw_button(self, rect, text, mouse_pos, color_base=(70, 128, 175), color_hover=(94, 166, 216)):
        hovered = rect.collidepoint(mouse_pos)
        c1 = color_hover if hovered else color_base
        shadow = pygame.Surface((rect.width + 4, rect.height + 4), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (10, 18, 32, 90), (0, 0, rect.width + 4, rect.height + 4), border_radius=18)
        self.screen.blit(shadow, (rect.left - 2, rect.top + 3))

        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*c1, 245), (0, 0, rect.width, rect.height), border_radius=16)
        pygame.draw.rect(surf, (230, 245, 255, 190), (0, 0, rect.width, rect.height), width=2, border_radius=16)
        self.screen.blit(surf, rect.topleft)

        label = self.h1_font.render(text, True, (245, 250, 255))
        self.screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2 - 1))

    def draw_hud(self):
        panel = pygame.Surface((WIDTH - 24, 84), pygame.SRCALPHA)
        pygame.draw.rect(panel, (12, 20, 32, 170), panel.get_rect(), border_radius=12)
        self.screen.blit(panel, (12, 12))

        hp_ratio = max(0.0, self.player.hp / self.player.max_hp)
        pygame.draw.rect(self.screen, (46, 58, 75), (28, 36, 220, 18), border_radius=8)
        pygame.draw.rect(self.screen, (80, 220, 155), (28, 36, int(220 * hp_ratio), 18), border_radius=8)
        hp_text = self.ui_font.render(f"HP {int(self.player.hp)}/{self.player.max_hp}", True, (230, 245, 250))
        self.screen.blit(hp_text, (34, 33))

        skill_ratio = 1.0 - self.player.skill_t / self.player.skill_cd if self.player.skill_cd > 0 else 1
        skill_ratio = max(0.0, min(1.0, skill_ratio))
        pygame.draw.rect(self.screen, (46, 58, 75), (28, 62, 220, 12), border_radius=6)
        pygame.draw.rect(self.screen, (100, 170, 250), (28, 62, int(220 * skill_ratio), 12), border_radius=6)
        sk_text = self.small_font.render("EMP", True, (190, 220, 250))
        self.screen.blit(sk_text, (254, 59))

        lane_text = self.small_font.render(self.tr(f"弹道 {self.player.bullet_lanes}", f"LANE {self.player.bullet_lanes}"), True, (190, 220, 250))
        self.screen.blit(lane_text, (305, 59))

        right = WIDTH - 26
        score_text = self.ui_font.render(self.tr(f"分数: {self.score}", f"SCORE: {self.score}"), True, (245, 235, 200))
        atk_text = self.ui_font.render(self.tr(f"攻击: {self.player.attack}", f"ATK: {self.player.attack}"), True, (245, 235, 200))
        lv_text = self.ui_font.render(self.tr(f"等级: {self.player.level}", f"LV: {self.player.level}"), True, (245, 235, 200))
        tm_text = self.ui_font.render(self.tr(f"生存: {int(self.survive_time)}s", f"TIME: {int(self.survive_time)}s"), True, (245, 235, 200))

        self.screen.blit(score_text, (right - score_text.get_width(), 24))
        self.screen.blit(atk_text, (right - atk_text.get_width(), 46))
        self.screen.blit(lv_text, (right - lv_text.get_width(), 68))
        self.screen.blit(tm_text, (right - tm_text.get_width(), 90))

        if self.combo > 1 and self.combo_t > 0:
            combo_text = self.h1_font.render(self.tr(f"连击 x{self.combo}", f"COMBO x{self.combo}"), True, (255, 195, 120))
            self.screen.blit(combo_text, (WIDTH // 2 - combo_text.get_width() // 2, 105))

        boss = self.get_alive_boss()
        if boss is not None:
            pygame.draw.rect(self.screen, (55, 45, 56), (28, 112, WIDTH - 56, 10), border_radius=5)
            ratio = max(0.0, boss.hp / boss.max_hp)
            pygame.draw.rect(self.screen, (235, 92, 122), (28, 112, int((WIDTH - 56) * ratio), 10), border_radius=5)
            boss_text = self.render_small(self.tr("首领", "BOSS"), (255, 220, 220))
            self.screen.blit(boss_text, (WIDTH // 2 - boss_text.get_width() // 2, 108))

    def handle_events(self):
        """处理所有输入事件
        
        支持的输入方式：
          - 键盘：WASD / 方向键（移动）、F（技能）、P（暂停）、H（菜单）、R（重开）
          - 鼠标：拖动控制玩家移动、点击按钮
          - 触摸（网页版）：FINGER 事件（手指拖动和点击）
          - 滚轮：修改历史记录页码
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.save_current_run_if_needed()
                self.stop_bgm()
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.state == "menu":
                    if event.key == pygame.K_RETURN:
                        self.play_button_sfx()
                        self.state = "playing"
                        self.reset_game()
                        self.ensure_bgm()
                    elif event.key == pygame.K_s:
                        self.play_button_sfx()
                        self.state = "settings"
                elif self.state == "playing":
                    if event.key == pygame.K_f:
                        self.cast_emp()
                    elif event.key == pygame.K_p:
                        self.play_button_sfx()
                        self.state = "paused"
                        self.set_bgm_paused(True)
                    elif event.key == pygame.K_h:
                        self.play_button_sfx()
                        self.save_current_run_if_needed()
                        self.state = "menu"
                        self.stop_bgm()
                        self.touch_active = False
                elif self.state == "paused":
                    if event.key == pygame.K_p:
                        self.play_button_sfx()
                        self.state = "playing"
                        self.set_bgm_paused(False)
                    elif event.key == pygame.K_h:
                        self.play_button_sfx()
                        self.save_current_run_if_needed()
                        self.state = "menu"
                        self.stop_bgm()
                        self.touch_active = False
                        self.set_bgm_paused(False)
                elif self.state == "settings":
                    if event.key in (pygame.K_ESCAPE, pygame.K_h):
                        self.play_button_sfx()
                        self.state = "menu"
                        self.stop_bgm()
                elif self.state == "game_over":
                    if event.key == pygame.K_r:
                        self.play_button_sfx()
                        self.state = "playing"
                        self.reset_game()
                        self.ensure_bgm()
                    elif event.key == pygame.K_ESCAPE:
                        self.play_button_sfx()
                        self.save_current_run_if_needed()
                        self.state = "menu"
                        self.stop_bgm()
                    elif event.key == pygame.K_h:
                        self.play_button_sfx()
                        self.save_current_run_if_needed()
                        self.state = "menu"
                        self.stop_bgm()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "menu":
                    if self.start_button.collidepoint(event.pos):
                        self.play_button_sfx()
                        self.state = "playing"
                        self.reset_game()
                        self.ensure_bgm()
                    elif self.quit_button.collidepoint(event.pos):
                        self.play_button_sfx()
                        self.running = False
                    elif self.settings_button.collidepoint(event.pos):
                        self.play_button_sfx()
                        self.state = "settings"
                    elif self.history_panel_rect.collidepoint(event.pos):
                        self.history_dragging = True
                        self.history_drag_start_y = event.pos[1]
                elif self.state == "settings":
                    if self.bgm_toggle_button.collidepoint(event.pos):
                        self.play_button_sfx()
                        self.bgm_enabled = not self.bgm_enabled
                        self.apply_audio_settings()
                    elif self.sfx_toggle_button.collidepoint(event.pos):
                        self.play_button_sfx()
                        self.sfx_enabled = not self.sfx_enabled
                    elif self.bgm_slider_rect.collidepoint(event.pos):
                        self.dragging_slider = "bgm"
                        self.update_slider_by_x("bgm", event.pos[0])
                    elif self.sfx_slider_rect.collidepoint(event.pos):
                        self.dragging_slider = "sfx"
                        self.update_slider_by_x("sfx", event.pos[0])
                    elif self.settings_back_button.collidepoint(event.pos):
                        self.play_button_sfx()
                        self.state = "menu"
                        self.stop_bgm()
                elif self.state in ("playing", "paused"):
                    if not self.try_touch_action(event.pos) and self.state == "playing":
                        self.touch_active = True
                        self.touch_pos = event.pos
                elif self.state == "game_over":
                    self.play_button_sfx()
                    self.state = "menu"
                    self.stop_bgm()
            elif event.type == pygame.MOUSEMOTION:
                if self.state == "playing" and self.touch_active:
                    self.touch_pos = event.pos
                elif self.state == "settings" and self.dragging_slider is not None:
                    self.update_slider_by_x(self.dragging_slider, event.pos[0])
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.state == "playing":
                    self.touch_active = False
                elif self.state == "settings":
                    self.dragging_slider = None
                elif self.state == "menu" and self.history_dragging:
                    if self.history_drag_start_y is not None:
                        dy = event.pos[1] - self.history_drag_start_y
                        max_page = max(0, math.ceil(len(self.history) / self.history_page_size) - 1)
                        if dy <= -24:
                            self.history_page = min(max_page, self.history_page + 1)
                            self.play_button_sfx()
                        elif dy >= 24:
                            self.history_page = max(0, self.history_page - 1)
                            self.play_button_sfx()
                    self.history_dragging = False
                    self.history_drag_start_y = None
            elif event.type == pygame.MOUSEWHEEL and self.state == "menu":
                max_page = max(0, math.ceil(len(self.history) / self.history_page_size) - 1)
                if event.y < 0:
                    self.history_page = min(max_page, self.history_page + 1)
                elif event.y > 0:
                    self.history_page = max(0, self.history_page - 1)
            elif event.type == pygame.FINGERDOWN:
                pos = (int(event.x * WIDTH), int(event.y * HEIGHT))
                if self.state in ("playing", "paused"):
                    if not self.try_touch_action(pos) and self.state == "playing":
                        self.touch_active = True
                        self.set_touch_from_finger(event.x, event.y)
                elif self.state == "menu":
                    # Menu keeps click-driven behavior; finger taps map to button checks.
                    if self.start_button.collidepoint(pos):
                        self.play_button_sfx()
                        self.state = "playing"
                        self.reset_game()
                        self.ensure_bgm()
                    elif self.quit_button.collidepoint(pos):
                        self.play_button_sfx()
                        self.running = False
                    elif self.settings_button.collidepoint(pos):
                        self.play_button_sfx()
                        self.state = "settings"
                    elif self.history_panel_rect.collidepoint(pos):
                        self.history_dragging = True
                        self.history_drag_start_y = pos[1]
                elif self.state == "settings":
                    if self.bgm_toggle_button.collidepoint(pos):
                        self.play_button_sfx()
                        self.bgm_enabled = not self.bgm_enabled
                        self.apply_audio_settings()
                    elif self.sfx_toggle_button.collidepoint(pos):
                        self.play_button_sfx()
                        self.sfx_enabled = not self.sfx_enabled
                    elif self.bgm_slider_rect.collidepoint(pos):
                        self.dragging_slider = "bgm"
                        self.update_slider_by_x("bgm", pos[0])
                    elif self.sfx_slider_rect.collidepoint(pos):
                        self.dragging_slider = "sfx"
                        self.update_slider_by_x("sfx", pos[0])
                    elif self.settings_back_button.collidepoint(pos):
                        self.play_button_sfx()
                        self.state = "menu"
                        self.stop_bgm()
            elif event.type == pygame.FINGERMOTION:
                if self.state == "playing" and self.touch_active:
                    self.set_touch_from_finger(event.x, event.y)
                elif self.state == "settings" and self.dragging_slider is not None:
                    self.update_slider_by_x(self.dragging_slider, int(event.x * WIDTH))
            elif event.type == pygame.FINGERUP:
                if self.state == "playing":
                    self.touch_active = False
                elif self.state == "settings":
                    self.dragging_slider = None
                elif self.state == "menu" and self.history_dragging:
                    if self.history_drag_start_y is not None:
                        dy = int(event.y * HEIGHT) - self.history_drag_start_y
                        max_page = max(0, math.ceil(len(self.history) / self.history_page_size) - 1)
                        if dy <= -24:
                            self.history_page = min(max_page, self.history_page + 1)
                            self.play_button_sfx()
                        elif dy >= 24:
                            self.history_page = max(0, self.history_page - 1)
                            self.play_button_sfx()
                    self.history_dragging = False
                    self.history_drag_start_y = None

    def cast_emp(self):
        """攻击 EMP 技能
        
        功能：
          1. 清除所有敌机子弹
          2. 对所有敌机造成 2.4 倍的攻击伤害
          3. 对玩家提供 1.1 秒无敌时间
          4. 触发全屏轰炸效果
          5. 清空连击计数
        
        技能冷却时间为 self.player.skill_cd，存儲在 self.player.skill_t 中
        """
        if self.player.skill_t > 0:
            return  # 技能在冷却中，无法使用
        self.player.skill_t = self.player.skill_cd
        self.player.invuln = max(self.player.invuln, 1.1)

        destroyed = 0
        for e in self.enemies:
            e.hp -= self.player.attack * 2.4
            if e.hp <= 0 and e.alive:
                e.alive = False
                destroyed += 1
                self.score += 280 if e.is_boss else 55
                self.kills += 1
                self.play_kill_sfx()
                self.add_explosion(e.x, e.y, 56 if e.is_boss else 22, (255, 170, 110))
                self.spawn_pickup(e.x, e.y)

        self.enemy_bullets.clear()
        self.add_explosion(self.player.x, self.player.y, 30, (115, 220, 255))
        self.combo = max(1, self.combo + destroyed)
        self.combo_t = 1.2

    def spawn_pickup(self, x, y):
        roll = random.random()
        if roll < 0.06:
            self.pickups.append(Pickup(x, y, "multishot"))
        elif roll < 0.12:
            self.pickups.append(Pickup(x, y, "heal"))

    def fire_player_bullets(self):
        """根据弹道数发射子弹
        
        子弹排列方法：
          - 所有子弹不同位置
          - 相邓㞣弹道间为 12 像素
          - 中心对称，把玩家处于最中间
        
        伤害流失：
          - 5 道弹道时，每条子弹执行 90% 伤害（为了平衡
          - 少于 5 道时全伤害
        """
        lanes = max(1, min(5, self.player.bullet_lanes))
        center_x = self.player.x
        base_y = self.player.y - 20
        lane_gap = 12
        # 弹道算法：用对称偏移生成多弹道，保证弹道围绕玩家中心均匀分布。
        # 例如 3 道时偏移为 [-1,0,1] * lane_gap；5 道时为 [-2,-1,0,1,2] * lane_gap。
        start = -(lanes - 1) / 2
        dmg_scale = 0.9 if lanes >= 5 else 1.0
        for i in range(lanes):
            x = center_x + (start + i) * lane_gap
            self.player_bullets.append(Bullet(x, base_y, -620, self.player.attack * dmg_scale, True))

    def update_playing(self, dt):
        """更新游戏进行中的所有逻辑
        
        包括：
          1. 玩家移动和发射子弹
          2. 敌机刷新和移动
          3. 子弹更新和碰撞检测
          4. 掉落物拾取
          5. 敌机击杀判定和分数加成
          6. 玩家升级判定
          7. boss 生成和伤害
          8. 游戏结束判定
        
        Args:
            dt: 帧时间间隔（秒）
        """
        self.survive_time += dt
        self.combo_t = max(0.0, self.combo_t - dt)
        if self.combo_t == 0:
            self.combo = 0

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        if self.touch_active:
            tx, ty = self.touch_pos
            self.player.x = tx
            self.player.y = ty
            self.player.x = max(28, min(WIDTH - 28, self.player.x))
            self.player.y = max(38, min(HEIGHT - 30, self.player.y))

        # 难度曲线算法：刷怪冷却随生存时间线性缩短，并设置下限避免无穷增速。
        self.spawn_cd = max(0.2, 0.78 - self.survive_time * 0.012)
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            level = 1 + int(self.survive_time / 16)
            self.enemies.append(self.create_regular_enemy(level))
            if self.survive_time > 35 and random.random() < 0.35:
                self.enemies.append(self.create_regular_enemy(level + 1))
            self.spawn_t = self.spawn_cd

        if self.survive_time >= self.next_boss_time and self.get_alive_boss() is None:
            level = 1 + int(self.survive_time / 18)
            boss = Enemy(level, kind="boss", is_boss=True)
            boss.x = WIDTH // 2
            boss.y = -90
            self.enemies.append(boss)
            self.play_boss_sfx()
            self.next_boss_time += random.uniform(52, 70)

        if self.player.fire_t <= 0:
            self.fire_player_bullets()
            self.player.fire_t = self.player.fire_cd

        for b in self.player_bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)
        self.player_bullets = [b for b in self.player_bullets if b.alive]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

        for e in self.enemies:
            e.update(dt)
            if e.shoot_t <= 0 and e.alive:
                e.shoot_t = e.shoot_cd
                self.spawn_enemy_shot(e)

        # 碰撞算法：对子弹和敌机做双层遍历，基于 pygame.Rect.colliderect 进行 AABB 判定。
        for b in self.player_bullets:
            if not b.alive:
                continue
            for e in self.enemies:
                if e.alive and b.rect.colliderect(e.rect):
                    hit_dmg = b.dmg * (0.55 if e.is_boss else 1.0)
                    e.hp -= hit_dmg
                    b.alive = False
                    if e.hp <= 0:
                        e.alive = False
                        self.kills += 1
                        self.play_kill_sfx()
                        self.combo = self.combo + 1 if self.combo_t > 0 else 1
                        self.combo_t = 1.35
                        gain = (260 if e.is_boss else 35) + min(40, self.combo * 2)
                        self.score += gain
                        self.add_explosion(e.x, e.y, 60 if e.is_boss else 20, (255, 170, 110))
                        self.spawn_pickup(e.x, e.y)
                    else:
                        self.add_explosion(b.x, b.y, 4, (130, 220, 255))
                    break

        p_rect = self.player.rect
        for b in self.enemy_bullets:
            if b.alive and b.rect.colliderect(p_rect):
                b.alive = False
                if self.player.invuln <= 0:
                    self.player.hp -= b.dmg
                    self.player.invuln = 2.0
                    self.play_hurt_sfx()
                    self.add_explosion(self.player.x, self.player.y, 10, (105, 220, 255))

        for e in self.enemies:
            if e.alive and e.rect.colliderect(p_rect):
                e.alive = False
                if self.player.invuln <= 0:
                    self.player.hp -= 20
                    self.player.invuln = 2.0
                    self.play_hurt_sfx()
                    self.add_explosion(self.player.x, self.player.y, 14, (255, 120, 120))
                self.add_explosion(e.x, e.y, 16, (255, 155, 110))

        for p in self.pickups:
            p.update(dt)
            if p.alive and p.rect.colliderect(p_rect):
                p.alive = False
                if p.kind == "multishot":
                    self.player.bullet_lanes = min(5, self.player.bullet_lanes + 1)
                    self.add_explosion(self.player.x, self.player.y, 14, (255, 210, 110))
                else:
                    self.player.hp = min(self.player.max_hp, self.player.hp + 22)
                    self.add_explosion(self.player.x, self.player.y, 14, (120, 245, 165))

        self.enemies = [e for e in self.enemies if e.alive]
        self.pickups = [p for p in self.pickups if p.alive]

        new_level = 1 + self.score // 420
        if new_level > self.player.level:
            self.player.level = new_level
            self.player.attack = 14 + (self.player.level - 1) * 2
            self.add_explosion(self.player.x, self.player.y, 18, (150, 245, 255))

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        if self.player.hp <= 0:
            if not self.game_recorded:
                self.append_history()
                self.game_recorded = True
            self.state = "game_over"
            self.game_over_timer = 0.0
            self.add_explosion(self.player.x, self.player.y, 48, (255, 115, 95))

    def draw_playing(self):
        """绘制游戏进行中的整个画哨
        
        绘制顺序（前提敌机已经发射子弹）：
          1. 背景与星空（需要在最上芝
          2. 掉落物（增强可见性）
          3. 玩家子弹
          4. 敌机子弹
          5. 爆炸效果粒子
          6. 玩家飞机（需要在子弹之上）
          7. HUD 信息（HP、技能、整个列表、打倒计数）
          8. 网页端控制按钮（HOME、PAUSE、EMP）
        """
        self.draw_background()

        for e in self.enemies:
            e.draw(self.screen)
        for p in self.pickups:
            p.draw(self.screen, self.time)
        for b in self.player_bullets:
            b.draw(self.screen)
        for b in self.enemy_bullets:
            b.draw(self.screen)

        self.player.draw(self.screen, self.time)

        for p in self.particles:
            p.draw(self.screen)

        self.draw_hud()
        self.draw_touch_ui()

    def draw_game_over(self):
        """绘制游戏结束界面
        
        控件顺序：
          1. 先绘制游戏画面
          2. 背景
          3. 显示 "GAME OVER" 标题
          4. 打印 4 行统计：最终分数、击杀数、生存时间
          5. 展示历史成绩模板
        """
        self.draw_playing()
        self.game_over_timer += 1 / FPS

        mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alpha = min(180, int(140 + self.game_over_timer * 120))
        mask.fill((12, 8, 10, alpha))
        self.screen.blit(mask, (0, 0))

        title = self.title_font.render(self.tr("游戏结束", "GAME OVER"), True, (255, 185, 155))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 170))

        lines = [
            self.tr(f"最终分数: {self.score}", f"FINAL SCORE: {self.score}"),
            self.tr(f"击落敌机: {self.kills}", f"KILLS: {self.kills}"),
            self.tr(f"生存时间: {int(self.survive_time)} 秒", f"SURVIVAL: {int(self.survive_time)}s"),
            self.tr("按 R 重开  |  ESC / H 回菜单", "R to retry  |  ESC / H to menu"),
        ]
        for i, txt in enumerate(lines):
            color = (235, 225, 210) if i < 3 else (190, 210, 235)
            surf = self.h1_font.render(txt, True, color)
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 260 + i * 40))

        self.draw_history_panel(452, 120, self.tr("历史记录 TOP", "TOP SCORES"))

    def draw_pause_overlay(self):
        """绘制暂停界面
        
        控件：
          1. 先绘制游戏画面
          2. 添加遮罩
          3. 居中显示 "PAUSED" 标题
          4. 指提玩家 P 继续、H 返菜单
          5. 网页端控制按钮仍跳转
        """
        self.draw_playing()
        mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        mask.fill((8, 10, 18, 165))
        self.screen.blit(mask, (0, 0))

        title = self.title_font.render(self.tr("已暂停", "PAUSED"), True, (230, 240, 255))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 220))
        tip = self.h1_font.render(self.tr("按 P 继续，按 H 返回菜单", "Press P to resume, H for menu"), True, (210, 224, 245))
        self.screen.blit(tip, (WIDTH // 2 - tip.get_width() // 2, 300))
        self.draw_touch_ui()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            self.update_stars(dt)
            self.handle_events()

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state == "playing":
                self.update_playing(dt)
                self.draw_playing()
            elif self.state == "paused":
                self.draw_pause_overlay()
            else:
                self.draw_game_over()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    async def run_web(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            self.update_stars(dt)
            self.handle_events()

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state == "playing":
                self.update_playing(dt)
                self.draw_playing()
            elif self.state == "paused":
                self.draw_pause_overlay()
            else:
                self.draw_game_over()

            pygame.display.flip()
            await asyncio.sleep(0)

        pygame.quit()


if __name__ == "__main__":
    if IS_WEB:
        asyncio.run(Game().run_web())
    else:
        Game().run()
