import pygame
import random
import numpy as np
import platform
import sys

# === Initialization ===
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)
SCREEN_COLUMNS, SCREEN_ROWS = 10, 20
BLOCK = 30
SCORE_HEIGHT = 30
WIDTH = SCREEN_COLUMNS * BLOCK
HEIGHT = SCREEN_ROWS * BLOCK + SCORE_HEIGHT
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tetris - No Media")
clock = pygame.time.Clock()
FPS = 60

# === Colors & Shapes ===
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY  = (128, 128, 128)
COLORS = [
    (0,255,255), (255,255,0), (128,0,128),
    (0,255,0),   (255,0,0),   (0,0,255),
    (255,165,0)
]
SHAPES = [
    [(0,-1),(0,0),(0,1),(0,2)], # I
    [(0,0),(1,0),(0,1),(1,1)],  # O
    [(-1,0),(0,0),(1,0),(0,1)], # T
    [(-1,0),(0,0),(0,1),(1,1)], # S
    [(1,0),(0,0),(0,1),(-1,1)], # Z
    [(-1,0),(0,0),(1,0),(-1,1)],# J
    [(-1,0),(0,0),(1,0),(1,1)]  # L
]

# === Sound: simple square-wave melody ===
NOTES = {'A3':220,'B3':247,'C4':262,'D4':294,'E4':330}
MELODY = [('E4',.25),('B3',.25),('C4',.25),('D4',.25),
          ('C4',.25),('B3',.25),('A3',.5)] * 8

def make_square(f, d, amp=0.3, sr=44100):
    t = np.arange(int(d*sr)) / sr
    return amp * np.sign(np.sin(2*np.pi*f*t))

wave = np.concatenate([
    make_square(NOTES[n], dur) for n,dur in MELODY
])
wave_i = (wave * 32767).astype(np.int16)
stereo = np.column_stack((wave_i, wave_i))
sound = pygame.sndarray.make_sound(stereo)
sound.play(loops=-1)

# === Game State ===
grid = [[0]*SCREEN_COLUMNS for _ in range(SCREEN_ROWS)]
score, lines, level = 0, 0, 1
drop_interval = .5
timer = 0
font = pygame.font.SysFont('Arial', 24)
state = 'menu'
current = None

def new_piece():
    i = random.randrange(len(SHAPES))
    shape = [tuple(pt) for pt in SHAPES[i]]
    return {'shape': shape, 'color': COLORS[i], 'x':4, 'y': -min(y for _,y in shape)}

def collides(p):
    for dx,dy in p['shape']:
        x,y = p['x']+dx, p['y']+dy
        if x<0 or x>=SCREEN_COLUMNS or y>=SCREEN_ROWS or (y>=0 and grid[y][x]):
            return True
    return False

def move_ok(p, dx, dy):
    npiece = {**p, 'x':p['x']+dx, 'y':p['y']+dy}
    return not collides(npiece)

def rotate(p):
    new_shape = [ (y, -x) for x,y in p['shape'] ]
    npiece = {**p, 'shape': new_shape}
    if not collides(npiece):
        p['shape'] = new_shape

def lock_piece(p):
    global score, lines, level, drop_interval
    filled = []
    for dx,dy in p['shape']:
        x,y = p['x']+dx, p['y']+dy
        if y>=0: 
            grid[y][x] = p['color']
    # clear rows
    full = [r for r in range(SCREEN_ROWS) if all(grid[r])]
    if full:
        for r in sorted(full, reverse=True):
            del grid[r]
        for _ in full:
            grid.insert(0, [0]*SCREEN_COLUMNS)
        pts = [0,100,300,600,1000][min(len(full),4)]
        score += pts
        lines += len(full)
        if lines // 10 >= level:
            level += 1
            drop_interval *= 0.9

def draw():
    screen.fill(BLACK)
    # grid
    for y in range(SCREEN_ROWS):
        for x in range(SCREEN_COLUMNS):
            if grid[y][x]:
                pygame.draw.rect(
                    screen, grid[y][x],
                    (x*BLOCK, SCORE_HEIGHT + y*BLOCK, BLOCK, BLOCK)
                )
    # grid lines
    for i in range(SCREEN_ROWS+1):
        pygame.draw.line(screen, GRAY, (0, SCORE_HEIGHT + i*BLOCK), (WIDTH, SCORE_HEIGHT + i*BLOCK))
    for i in range(SCREEN_COLUMNS+1):
        pygame.draw.line(screen, GRAY, (i*BLOCK, SCORE_HEIGHT), (i*BLOCK, HEIGHT))

    # piece
    if current:
        for dx,dy in current['shape']:
            x,y = current['x']+dx, current['y']+dy
            if y>=0:
                pygame.draw.rect(
                    screen, current['color'],
                    (x*BLOCK, SCORE_HEIGHT + y*BLOCK, BLOCK, BLOCK)
                )
    # score
    txt = font.render(f"Score: {score}", True, WHITE)
    screen.blit(txt, (10,5))

    if state == 'menu':
        render_center("TETRIS", 100, 48)
        render_center("Press S to Start", 200)
    elif state == 'credits':
        render_center("CREDITS to TETRIS & PYGAME", 200)
        render_center("Press M for Menu", 250)

    pygame.display.flip()

def render_center(text, y, size=24):
    f = pygame.font.SysFont('Arial', size)
    surf = f.render(text, True, WHITE)
    rect = surf.get_rect(center=(WIDTH//2, y))
    screen.blit(surf, rect)

def reset():
    global grid, score, lines, level, drop_interval, timer, current
    grid = [[0]*SCREEN_COLUMNS for _ in range(SCREEN_ROWS)]
    score = lines = 0
    level = 1
    drop_interval = .5
    timer = 0
    current = new_piece()

# === Main Loop ===
reset()
running = True
while running:
    dt = clock.tick(FPS) / 1000.0
    timer += dt
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.KEYDOWN:
            if state == 'menu':
                if ev.key == pygame.K_s:
                    reset(); state = 'play'
                elif ev.key == pygame.K_c:
                    state = 'credits'
            elif state == 'credits':
                if ev.key == pygame.K_m:
                    state = 'menu'
            elif state == 'play':
                if ev.key == pygame.K_LEFT and move_ok(current, -1, 0):
                    current['x'] -= 1
                elif ev.key == pygame.K_RIGHT and move_ok(current, 1, 0):
                    current['x'] += 1
                elif ev.key == pygame.K_DOWN and move_ok(current, 0, 1):
                    current['y'] += 1
                elif ev.key == pygame.K_UP:
                    rotate(current)

    if state == 'play' and timer >= drop_interval:
        if move_ok(current, 0, 1):
            current['y'] += 1
        else:
            lock_piece(current)
            current = new_piece()
            if collides(current):
                state = 'menu'
        timer = 0

    draw()

pygame.quit()
sys.exit()
