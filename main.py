import math
import json
import os
import random
import sys
from dataclasses import dataclass

import pygame

IS_WEB = sys.platform == "emscripten"
if IS_WEB:
    import asyncio


WIDTH, HEIGHT = 410, 640
FPS = 60
RECORD_FILE = "records.json"
MAX_RECORDS = 8


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple
    size: float

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 140 * dt
        self.life -= dt

    def draw(self, screen):
        t = max(0.0, self.life / self.max_life)
        radius = max(1, int(self.size * t))
        alpha = int(220 * t)
        surf = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (radius + 1, radius + 1), radius)
        screen.blit(surf, (self.x - radius, self.y - radius))


class Bullet:
    def __init__(self, x, y, vy, dmg, friendly=True):
        self.x = x
        self.y = y
        self.vy = vy
        self.dmg = dmg
        self.friendly = friendly
        self.alive = True
        self.radius = 4 if friendly else 6

    @property
    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

    def update(self, dt):
        self.y += self.vy * dt
        if self.y < -30 or self.y > HEIGHT + 30:
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
    def __init__(self, level=1):
        self.w = random.randint(36, 54)
        self.h = random.randint(28, 40)
        self.x = random.randint(30, WIDTH - 30)
        self.y = random.randint(-200, -40)
        self.speed = random.uniform(135, 210) + level * 4.4
        self.max_hp = random.randint(24, 44) + level * 3
        self.hp = self.max_hp
        self.shoot_cd = random.uniform(1.0, 1.9)
        self.shoot_t = random.uniform(0.2, 1.5)
        self.alive = True

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), self.w, self.h)

    def update(self, dt):
        self.y += self.speed * dt
        self.shoot_t -= dt
        if self.y > HEIGHT + 60:
            self.alive = False

    def draw(self, screen):
        body = self.rect
        pygame.draw.polygon(
            screen,
            (220, 75, 80),
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
        font = pygame.font.SysFont("consolas", 14, bold=True)
        txt = font.render(label, True, (30, 35, 45))
        screen.blit(txt, (int(self.x - txt.get_width() / 2), int(self.y - txt.get_height() / 2)))


class Player:
    def __init__(self):
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
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("飞机大战 - 无尽模式")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("microsoftyaheiui", 48, bold=True)
        self.h1_font = pygame.font.SysFont("microsoftyaheiui", 24, bold=True)
        self.ui_font = pygame.font.SysFont("microsoftyaheiui", 22)
        self.small_font = pygame.font.SysFont("consolas", 18)

        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(35, 180)] for _ in range(90)]
        self.big_stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(12, 28)] for _ in range(24)]

        self.running = True
        self.state = "menu"
        self.time = 0.0
        self.menu_flash = 0.0

        self.start_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 20, 200, 52)
        self.quit_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 86, 200, 46)
        self.skill_button = pygame.Rect(WIDTH - 78, HEIGHT - 78, 58, 58)
        self.touch_active = False
        self.touch_pos = (WIDTH // 2, HEIGHT - 90)

        self.history = self.load_history()

        self.reset_game()

    def reset_game(self):
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
        entry = {
            "score": int(self.score),
            "kills": int(self.kills),
            "time": int(self.survive_time),
        }
        self.history.append(entry)
        self.history.sort(key=lambda item: item.get("score", 0), reverse=True)
        self.history = self.history[:MAX_RECORDS]
        self.save_history()

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

    def draw_background(self):
        grad = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            r = int(8 + 14 * y / HEIGHT)
            g = int(22 + 16 * y / HEIGHT)
            b = int(42 + 24 * y / HEIGHT)
            pygame.draw.line(grad, (r, g, b), (0, y), (WIDTH, y))
        self.screen.blit(grad, (0, 0))

        for x, y, speed in self.stars:
            pygame.draw.circle(self.screen, (220, 235, 255), (int(x), int(y)), 1)
        for x, y, speed in self.big_stars:
            pygame.draw.circle(self.screen, (190, 215, 255), (int(x), int(y)), 2)

        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (55, 125, 180, 60), (-160, -120, 520, 320))
        pygame.draw.ellipse(glow, (255, 150, 90, 35), (WIDTH - 340, HEIGHT - 200, 360, 250))
        self.screen.blit(glow, (0, 0))

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
        self.draw_background()

        center_x = WIDTH // 2
        wobble = int(math.sin(self.time * 2.3) * 6)
        title = self.title_font.render("SKY STRIKE", True, (240, 248, 255))
        shadow = self.title_font.render("SKY STRIKE", True, (70, 110, 160))
        self.screen.blit(shadow, (center_x - title.get_width() // 2 + 3, 120 + wobble + 3))
        self.screen.blit(title, (center_x - title.get_width() // 2, 120 + wobble))

        subtitle = self.ui_font.render("无尽模式 · 刷新最高分", True, (190, 215, 245))
        self.screen.blit(subtitle, (center_x - subtitle.get_width() // 2, 205 + wobble))

        mouse_pos = pygame.mouse.get_pos()
        self.menu_flash += 0.06

        self.draw_button(self.start_button, "开始游戏", mouse_pos)
        self.draw_button(self.quit_button, "退出", mouse_pos, color_base=(95, 78, 88), color_hover=(135, 95, 100))

        self.draw_history_panel(470, 72, "历史记录 TOP")

        tip1 = self.small_font.render("移动: WASD / 方向键    攻击: 自动发射", True, (175, 200, 230))
        tip2 = self.small_font.render("技能EMP: F / 右下角按钮", True, (175, 200, 230))
        self.screen.blit(tip1, (center_x - tip1.get_width() // 2, HEIGHT - 88))
        self.screen.blit(tip2, (center_x - tip2.get_width() // 2, HEIGHT - 58))

    def draw_touch_ui(self):
        if not IS_WEB:
            return
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
        surf = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        pygame.draw.rect(surf, (15, 25, 40, 175), surf.get_rect(), border_radius=10)
        pygame.draw.rect(surf, (190, 220, 250, 120), surf.get_rect(), width=1, border_radius=10)
        self.screen.blit(surf, panel.topleft)

        title_surf = self.small_font.render(title, True, (208, 230, 250))
        self.screen.blit(title_surf, (panel.left + 10, panel.top + 6))

        if not self.history:
            empty = self.small_font.render("暂无记录", True, (165, 190, 210))
            self.screen.blit(empty, (panel.left + 10, panel.top + 32))
            return

        rows = min(3, len(self.history))
        for i in range(rows):
            rec = self.history[i]
            text = f"{i + 1}. 分{rec['score']}  击落{rec['kills']}  生存{rec['time']}s"
            line = self.small_font.render(text, True, (220, 235, 255))
            self.screen.blit(line, (panel.left + 10, panel.top + 28 + i * 20))

    def draw_button(self, rect, text, mouse_pos, color_base=(70, 128, 175), color_hover=(94, 166, 216)):
        hovered = rect.collidepoint(mouse_pos)
        t = 0.5 + 0.5 * math.sin(self.menu_flash)
        c1 = color_hover if hovered else color_base
        c2 = tuple(max(0, min(255, int(v * (0.85 + 0.15 * t)))) for v in c1)

        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for y in range(rect.height):
            ratio = y / max(1, rect.height - 1)
            col = (
                int(c1[0] * (1 - ratio) + c2[0] * ratio),
                int(c1[1] * (1 - ratio) + c2[1] * ratio),
                int(c1[2] * (1 - ratio) + c2[2] * ratio),
                240,
            )
            pygame.draw.line(surf, col, (0, y), (rect.width, y))

        pygame.draw.rect(surf, (230, 245, 255, 180), (0, 0, rect.width, rect.height), width=2, border_radius=12)
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

        lane_text = self.small_font.render(f"弹道 {self.player.bullet_lanes}", True, (190, 220, 250))
        self.screen.blit(lane_text, (305, 59))

        right = WIDTH - 26
        score_text = self.ui_font.render(f"分数: {self.score}", True, (245, 235, 200))
        atk_text = self.ui_font.render(f"攻击: {self.player.attack}", True, (245, 235, 200))
        lv_text = self.ui_font.render(f"等级: {self.player.level}", True, (245, 235, 200))
        tm_text = self.ui_font.render(f"生存: {int(self.survive_time)}s", True, (245, 235, 200))

        self.screen.blit(score_text, (right - score_text.get_width(), 24))
        self.screen.blit(atk_text, (right - atk_text.get_width(), 46))
        self.screen.blit(lv_text, (right - lv_text.get_width(), 68))
        self.screen.blit(tm_text, (right - tm_text.get_width(), 90))

        if self.combo > 1 and self.combo_t > 0:
            combo_text = self.h1_font.render(f"COMBO x{self.combo}", True, (255, 195, 120))
            self.screen.blit(combo_text, (WIDTH // 2 - combo_text.get_width() // 2, 105))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.state == "menu":
                    if event.key == pygame.K_RETURN:
                        self.state = "playing"
                        self.reset_game()
                elif self.state == "playing":
                    if event.key == pygame.K_f:
                        self.cast_emp()
                elif self.state == "game_over":
                    if event.key == pygame.K_r:
                        self.state = "playing"
                        self.reset_game()
                    elif event.key == pygame.K_ESCAPE:
                        self.state = "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "menu":
                    if self.start_button.collidepoint(event.pos):
                        self.state = "playing"
                        self.reset_game()
                    elif self.quit_button.collidepoint(event.pos):
                        self.running = False
                elif self.state == "playing":
                    if self.skill_button.collidepoint(event.pos):
                        self.cast_emp()
                    else:
                        self.touch_active = True
                        self.touch_pos = event.pos
                elif self.state == "game_over":
                    self.state = "menu"
            elif event.type == pygame.MOUSEMOTION and self.state == "playing":
                if self.touch_active:
                    self.touch_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.state == "playing":
                    self.touch_active = False

    def cast_emp(self):
        if self.player.skill_t > 0:
            return
        self.player.skill_t = self.player.skill_cd
        self.player.invuln = max(self.player.invuln, 1.1)

        destroyed = 0
        for e in self.enemies:
            e.hp -= self.player.attack * 2.4
            if e.hp <= 0 and e.alive:
                e.alive = False
                destroyed += 1
                self.score += 55
                self.kills += 1
                self.add_explosion(e.x, e.y, 22, (255, 170, 110))
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
        lanes = max(1, min(5, self.player.bullet_lanes))
        center_x = self.player.x
        base_y = self.player.y - 20
        lane_gap = 12
        start = -(lanes - 1) / 2
        dmg_scale = 0.9 if lanes >= 5 else 1.0
        for i in range(lanes):
            x = center_x + (start + i) * lane_gap
            self.player_bullets.append(Bullet(x, base_y, -620, self.player.attack * dmg_scale, True))
        if self.player.level >= 4:
            self.player_bullets.append(Bullet(center_x, self.player.y - 26, -700, self.player.attack * 0.8, True))

    def update_playing(self, dt):
        self.survive_time += dt
        self.combo_t = max(0.0, self.combo_t - dt)
        if self.combo_t == 0:
            self.combo = 0

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        if self.touch_active:
            tx, ty = self.touch_pos
            dx = tx - self.player.x
            dy = ty - self.player.y
            dist = math.hypot(dx, dy)
            if dist > 1:
                step = min(dist, self.player.speed * dt)
                self.player.x += dx / dist * step
                self.player.y += dy / dist * step
                self.player.x = max(28, min(WIDTH - 28, self.player.x))
                self.player.y = max(38, min(HEIGHT - 30, self.player.y))

        self.spawn_cd = max(0.2, 0.78 - self.survive_time * 0.012)
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            level = 1 + int(self.survive_time / 16)
            self.enemies.append(Enemy(level))
            if self.survive_time > 35 and random.random() < 0.35:
                self.enemies.append(Enemy(level + 1))
            self.spawn_t = self.spawn_cd

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
                self.enemy_bullets.append(Bullet(e.x, e.y + 16, 205 + self.survive_time * 1.5, 11, False))

        for b in self.player_bullets:
            if not b.alive:
                continue
            for e in self.enemies:
                if e.alive and b.rect.colliderect(e.rect):
                    e.hp -= b.dmg
                    b.alive = False
                    if e.hp <= 0:
                        e.alive = False
                        self.kills += 1
                        self.combo = self.combo + 1 if self.combo_t > 0 else 1
                        self.combo_t = 1.35
                        gain = 35 + min(40, self.combo * 2)
                        self.score += gain
                        self.add_explosion(e.x, e.y, 20, (255, 170, 110))
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
                    self.add_explosion(self.player.x, self.player.y, 10, (105, 220, 255))

        for e in self.enemies:
            if e.alive and e.rect.colliderect(p_rect):
                e.alive = False
                if self.player.invuln <= 0:
                    self.player.hp -= 20
                    self.player.invuln = 2.0
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
        self.draw_playing()
        self.game_over_timer += 1 / FPS

        mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        alpha = min(180, int(140 + self.game_over_timer * 120))
        mask.fill((12, 8, 10, alpha))
        self.screen.blit(mask, (0, 0))

        title = self.title_font.render("GAME OVER", True, (255, 185, 155))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 170))

        lines = [
            f"最终分数: {self.score}",
            f"击落敌机: {self.kills}",
            f"生存时间: {int(self.survive_time)} 秒",
            "按 R 立即重开，按 ESC 返回主菜单",
        ]
        for i, txt in enumerate(lines):
            color = (235, 225, 210) if i < 3 else (190, 210, 235)
            surf = self.h1_font.render(txt, True, color)
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 280 + i * 44))

        self.draw_history_panel(468, 104, "历史记录 TOP")

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            self.update_stars(dt)
            self.handle_events()

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "playing":
                self.update_playing(dt)
                self.draw_playing()
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
            elif self.state == "playing":
                self.update_playing(dt)
                self.draw_playing()
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
