import pygame
import random
import time
import csv
import os
import math
import struct

pygame.init()
pygame.mixer.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
W, H = screen.get_size()
pygame.display.set_caption("AimLab Lite - 六目标射击训练")
clock = pygame.time.Clock()

def load_chinese_font(size=36):
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except:
                continue
    return pygame.font.Font(None, size)

title_font = load_chinese_font(64)
button_font = load_chinese_font(36)
info_font = load_chinese_font(28)

#  配色 
BG_TOP = (20, 22, 30)
BG_BOTTOM = (8, 8, 12)
TEXT_WHITE = (220, 220, 230)
TEXT_GRAY = (130, 130, 140)
CROSSHAIR_NORMAL = (0, 255, 200)
CROSSHAIR_HIT = (0, 255, 100)
CROSSHAIR_MISS = (255, 80, 80)
BAR_START = (200, 200, 220)
BAR_END = (255, 160, 80)
BTN_IDLE = (60, 60, 80)
BTN_HOVER = (80, 120, 200)
BTN_TEXT = (220, 220, 230)

# 击中音效 
def generate_pop_sound(volume=0.6):
    sample_rate = 44100
    duration = 0.06
    samples = int(sample_rate * duration)
    wave = []
    for i in range(samples):
        noise = random.uniform(-1, 1)
        envelope = math.exp(-i / (samples * 0.25))
        wave.append(int(noise * 32767 * volume * envelope))
    wave_bytes = struct.pack('h' * len(wave), *wave)
    return pygame.mixer.Sound(buffer=wave_bytes)

hit_sound = generate_pop_sound(0.6)
miss_sound = generate_pop_sound(0.3)

# 外部结束音乐加载 
script_dir = os.path.dirname(os.path.abspath(__file__))
low_path = os.path.join(script_dir, "assets", "low_score.ogg")
high_path = os.path.join(script_dir, "assets", "high_score.ogg")

def load_music(path, volume=0.5):
    """安全加载音乐，文件不存在时返回静音占位"""
    if os.path.exists(path):
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(volume)
            return sound
        except Exception as e:
            print(f"无法加载音乐 {path}: {e}")
    print(f"警告：未找到音乐文件 {path}，将使用静音。")
    return pygame.mixer.Sound(buffer=bytes(44100 * 2))  # 0秒静音

end_music_low = load_music(low_path, 0.5)
end_music_high = load_music(high_path, 0.5)
# ====================================

# 背景框架
def create_background(w, h):
    bg = pygame.Surface((w, h))
    for y in range(h):
        ratio = y / h
        r = BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio
        g = BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio
        b = BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio
        pygame.draw.line(bg, (r, g, b), (0, y), (w, y))
    grid_color = (30, 32, 40)
    for x in range(0, w, 100):
        pygame.draw.line(bg, grid_color, (x, 0), (x, h), 1)
    for y in range(0, h, 100):
        pygame.draw.line(bg, grid_color, (0, y), (w, y), 1)
    for _ in range(60):
        x = random.randint(0, w)
        y = random.randint(0, h)
        brightness = random.randint(80, 160)
        pygame.draw.circle(bg, (brightness, brightness, brightness), (x, y), 1)
    return bg

bg_surface = create_background(W, H)

# 球形hitbox
class Target:
    def __init__(self, existing_targets=None):
        self.radius = 40
        margin_x = int(W * 0.1) + self.radius
        margin_y_top = int(H * 0.1) + self.radius + 60
        margin_y_bottom = int(H * 0.9) - self.radius
        max_attempts = 100
        for _ in range(max_attempts):
            self.x = random.randint(margin_x, W - margin_x)
            self.y = random.randint(margin_y_top, margin_y_bottom)
            if existing_targets is None or not self._overlaps_any(existing_targets):
                break
        self.spawn_time = pygame.time.get_ticks()

    def _overlaps_any(self, targets):
        for t in targets:
            if self._overlaps(t):
                return True
        return False

    def _overlaps(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        min_dist = self.radius + other.radius + 15
        return dx*dx + dy*dy < min_dist*min_dist

    def get_display_y(self):
        return self.y + int(math.sin(pygame.time.get_ticks() / 300) * 5)

    def draw(self, screen):
        dy = self.get_display_y()
        r = self.radius
        glow_surf = pygame.Surface((r*3, r*3), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (100, 200, 255, 30), (r*1.5, r*1.5), int(r*1.2))
        screen.blit(glow_surf, (self.x - r*1.5, dy - r*1.5))
        for i in range(r, 2, -1):
            progress = i / r
            alpha = 180 + 70 * progress
            red = int(30 * progress)
            green = int(120 + 100 * progress)
            blue = int(180 + 70 * progress)
            color = (red, green, blue, int(alpha))
            layer = pygame.Surface((i*2, i*2), pygame.SRCALPHA)
            pygame.draw.circle(layer, color, (i, i), i)
            screen.blit(layer, (self.x - i, dy - i))
        pygame.draw.circle(screen, (255, 255, 255), (self.x - 3, dy - 4), 4)
        pygame.draw.circle(screen, (255, 255, 255), (self.x - 4, dy - 5), 2)

    def is_hit(self, mx, my):
        dy = self.get_display_y()
        return (mx - self.x)**2 + (my - dy)**2 <= (self.radius + 5)**2

# 动画系统 
hit_effects = []
score_texts = []          
shake_offset = [0, 0]
miss_timer = 0

def add_hit_effect(x, y, max_radius):
    hit_effects.append([x, y, 0, max_radius, 15])

def add_score_text(x, y, text, color):
    """添加分数飘字，持续40帧"""
    score_texts.append([x, y, text, 40, color])

def trigger_shake():
    shake_offset[0] = random.randint(-3, 3)
    shake_offset[1] = random.randint(-3, 3)

#  准星 
crosshair_color = CROSSHAIR_NORMAL

def draw_crosshair(screen, x, y):
    if crosshair_color == CROSSHAIR_HIT:
        col = (0, 255, 100)
    elif crosshair_color == CROSSHAIR_MISS:
        col = (255, 80, 80)
    else:
        col = CROSSHAIR_NORMAL

    length = 6
    gap = 2
    thick = 2
    pygame.draw.line(screen, col, (x - length, y), (x - gap, y), thick)
    pygame.draw.line(screen, col, (x + gap, y), (x + length, y), thick)
    pygame.draw.line(screen, col, (x, y - length), (x, y - gap), thick)
    pygame.draw.line(screen, col, (x, y + gap), (x, y + length), thick)

# 评级函数
def get_funny_rating(score):
    if score < 4000:
        return "你没开显示器吗？"
    elif score < 8000:
        return "建议玩消消乐"
    elif score < 12000:
        return "还算个人"
    elif score < 15000:
        return "有点东西"
    elif score < 20000:
        return "职业选手？"
    elif score < 25000:
        return "作弊的？"
    else:
        return "锁头已确认"

# 记录成绩
def save_record(mode, hits, shots, avg_interval, score):
    rating = get_funny_rating(score)
    file_exists = os.path.isfile("records.csv")
    with open("records.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["日期", "模式", "命中数", "总射击数", "命中率(%)",
                             "平均射击间隔(ms)", "每分钟命中", "总分", "评级"])
        hit_rate = (hits / shots * 100) if shots > 0 else 0
        hits_per_min = hits * 2
        writer.writerow([
            time.strftime("%Y-%m-%d"),
            mode,
            hits,
            shots,
            f"{hit_rate:.1f}",
            f"{avg_interval:.0f}" if avg_interval else "",
            f"{hits_per_min:.0f}",
            score,
            rating
        ])

#  开始界面 
def show_start_screen():
    button_width, button_height = 200, 60
    start_btn_rect = pygame.Rect(W//2 - button_width//2, H//2, button_width, button_height)
    pygame.mouse.set_visible(True)

    while True:
        screen.blit(bg_surface, (0, 0))
        title_surf = title_font.render("AimLab Lite", True, TEXT_WHITE)
        screen.blit(title_surf, (W//2 - title_surf.get_width()//2, H//3))
        sub_surf = info_font.render("六目标射击训练", True, TEXT_GRAY)
        screen.blit(sub_surf, (W//2 - sub_surf.get_width()//2, H//3 + 70))

        mx, my = pygame.mouse.get_pos()
        if start_btn_rect.collidepoint(mx, my):
            color = BTN_HOVER
            text_color = (255, 255, 255)
        else:
            color = BTN_IDLE
            text_color = BTN_TEXT
        pygame.draw.rect(screen, color, start_btn_rect, border_radius=12)
        btn_text = button_font.render("开始游戏", True, text_color)
        screen.blit(btn_text, (start_btn_rect.centerx - btn_text.get_width()//2,
                               start_btn_rect.centery - btn_text.get_height()//2))

        tip = info_font.render("按 ESC 退出", True, TEXT_GRAY)
        screen.blit(tip, (W//2 - tip.get_width()//2, H - 60))

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and start_btn_rect.collidepoint(mx, my):
                return True

#  游戏主循环 
def game_loop():
    global crosshair_color, shake_offset, miss_timer
    pygame.mouse.set_visible(False)

    crosshair_color = CROSSHAIR_NORMAL
    shake_offset = [0, 0]
    miss_timer = 0
    hit_effects.clear()
    score_texts.clear()

    shots = 0
    hits = 0
    combo = 0          
    score = 0

    start_ticks = pygame.time.get_ticks()
    targets = []
    for _ in range(6):
        new_target = Target(targets)
        new_target.spawn_time = start_ticks
        targets.append(new_target)

    game_duration = 30 * 1000

    running = True
    while running:
        elapsed = pygame.time.get_ticks() - start_ticks
        remaining = max(0, game_duration - elapsed)
        if remaining <= 0:
            break

        clock.tick(60)

        if shake_offset[0] != 0:
            shake_offset[0] = int(shake_offset[0] * 0.7)
        if shake_offset[1] != 0:
            shake_offset[1] = int(shake_offset[1] * 0.7)

        screen.blit(bg_surface, shake_offset)

        progress = remaining / game_duration
        bar_width = int(W * progress)
        r = int(BAR_START[0] * (1 - progress) + BAR_END[0] * progress)
        g = int(BAR_START[1] * (1 - progress) + BAR_END[1] * progress)
        b = int(BAR_START[2] * (1 - progress) + BAR_END[2] * progress)
        pygame.draw.rect(screen, (r, g, b), (0, 0, bar_width, 4))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                shots += 1
                mx, my = pygame.mouse.get_pos()
                hit_any = False
                for t in targets[:]:
                    if t.is_hit(mx, my):
                        hits += 1
                        combo += 1   

                       
                        if combo >= 20:
                            add_score = 300
                        elif combo >= 10:
                            add_score = 200
                        else:
                            add_score = 100
                        score += add_score

                        dy = t.get_display_y()
                        add_hit_effect(t.x, dy, t.radius * 2)
                        add_score_text(t.x, dy - 20, f"+{add_score}", (0, 255, 100))
                        trigger_shake()

                        crosshair_color = CROSSHAIR_HIT
                        hit_sound.play()

                        targets.remove(t)
                        hit_any = True
                        break

                if not hit_any:
                    combo = 0
                    score = max(0, score - 500)
                    add_score_text(mx, my, "-500", (255, 80, 80))
                    crosshair_color = CROSSHAIR_MISS
                    miss_timer = 8
                    miss_sound.play()

                while len(targets) < 6:
                    new_target = Target(targets)
                    targets.append(new_target)

        if miss_timer > 0:
            miss_timer -= 1
            if miss_timer == 0:
                crosshair_color = CROSSHAIR_NORMAL

        for t in targets:
            t.draw(screen)

        for effect in hit_effects[:]:
            x, y, cur_r, max_r, life = effect
            cur_r += 2
            life -= 1
            if life <= 0 or cur_r >= max_r:
                hit_effects.remove(effect)
                continue
            alpha = int(100 * life / 15)
            ring_surf = pygame.Surface((max_r*2, max_r*2), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (255,255,255,alpha), (max_r, max_r), int(cur_r), 1)
            screen.blit(ring_surf, (x - max_r, y - max_r))
            effect[2] = cur_r
            effect[4] = life

        #命中得分
        for st in score_texts[:]:
            x, y, text, life, color = st
            life -= 1
            if life <= 0:
                score_texts.remove(st)
                continue
            alpha = int(255 * life / 40)
            surf = info_font.render(text, True, color)
            surf.set_alpha(alpha)
            screen.blit(surf, (x - surf.get_width()//2, y - 20))
            st[3] = life

        mx, my = pygame.mouse.get_pos()
        draw_crosshair(screen, mx, my)

        pygame.display.flip()

    avg_interval = game_duration / hits if hits > 0 else None
    return hits, shots, avg_interval, score

#  结束画面 
def show_end_screen(hits, shots, avg_interval, score):
    pygame.mouse.set_visible(True)
    rating = get_funny_rating(score)

    # 根据分数播放对应结束音乐
    if score < 12000:
        end_music_low.play()
    else:
        end_music_high.play()

    if shots > 0:
        save_record("六目标射击", hits, shots, avg_interval, score)

    screen.blit(bg_surface, (0, 0))
    result_texts = [
        "训练结束！",
        f"命中：{hits}  射击：{shots}",
        f"命中率：{hits/shots*100:.1f}%" if shots > 0 else "命中率：0%",
        f"平均射击间隔：{avg_interval:.0f} ms" if avg_interval else "平均射击间隔：N/A",
        f"总分：{score}",
        f"评价：{rating}"
    ]
    y = H // 2 - 80
    for line in result_texts:
        text = button_font.render(line, True, TEXT_WHITE)
        screen.blit(text, (W//2 - text.get_width()//2, y))
        y += 35

    tip = info_font.render("按 ESC 或关闭窗口退出", True, TEXT_GRAY)
    screen.blit(tip, (W//2 - tip.get_width()//2, H - 60))
    pygame.display.flip()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                waiting = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                waiting = False
        clock.tick(30)

#  主程序
def main():
    while True:
        start = show_start_screen()
        if not start:
            break
        result = game_loop()
        show_end_screen(*result)
    pygame.quit()

if __name__ == "__main__":
    main()