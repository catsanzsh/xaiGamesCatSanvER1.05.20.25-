import pygame
import random
import numpy as np
import asyncio
import platform

# Initialize Pygame
pygame.init()
pygame.mixer.init(frequency=44100)

# Screen setup
BLOCK_SIZE = 30
COLS = 10
ROWS = 20
SCORE_HEIGHT = 30
SCREEN_WIDTH = COLS * BLOCK_SIZE
SCREEN_HEIGHT = ROWS * BLOCK_SIZE + SCORE_HEIGHT
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Tetris - No Media")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
COLORS = [
    (0, 255, 255),   # I - Cyan
    (255, 255, 0),   # O - Yellow
    (128, 0, 128),   # T - Purple
    (0, 255, 0),     # S - Green
    (255, 0, 0),     # Z - Red
    (0, 0, 255),     # J - Blue
    (255, 165, 0)    # L - Orange
]

# Tetromino shapes
SHAPES = [
    [(0, -1), (0, 0), (0, 1), (0, 2)],  # I
    [(0, 0), (1, 0), (0, 1), (1, 1)],   # O
    [(-1, 0), (0, 0), (1, 0), (0, 1)],  # T
    [(-1, 0), (0, 0), (0, 1), (1, 1)],  # S
    [(1, 0), (0, 0), (0, 1), (-1, 1)],  # Z
    [(-1, 0), (0, 0), (1, 0), (-1, 1)], # J
    [(-1, 0), (0, 0), (1, 0), (1, 1)]   # L
]

# Game state variables
grid = [[0] * COLS for _ in range(ROWS)]
score = 0
total_lines_cleared = 0
level = 1
initial_interval = 0.5
drop_interval = initial_interval
drop_timer = 0
game_state = 'menu'
piece = None
font = pygame.font.SysFont('Arial', 24)
clock = pygame.time.Clock()
FPS = 60

# Music setup
NOTE_FREQS = {
    'A3': 220,
    'B3': 247,
    'C4': 262,
    'D4': 294,
    'E4': 330,
}
MELODY = [
    ('E4', 0.25), ('B3', 0.25), ('C4', 0.25), ('D4', 0.25),
    ('C4', 0.25), ('B3', 0.25), ('A3', 0.5)
] * 8  # Repeat for length

def generate_square_wave(frequency, duration, amplitude=0.5, sample_rate=44100):
    t = np.arange(0, duration, 1.0 / sample_rate)
    wave = amplitude * np.sign(np.sin(2 * np.pi * frequency * t))
    return wave

song_wave = np.concatenate([generate_square_wave(NOTE_FREQS[note], duration) for note, duration in MELODY])
song_wave_int = (song_wave * 32767).astype(np.int16)
# Convert to 2D array for stereo compatibility in Pyodide
song_wave_stereo = np.column_stack((song_wave_int, song_wave_int))
song_sound = pygame.sndarray.make_sound(song_wave_stereo)
song_sound.play(loops=-1)

# Game functions
def generate_new_piece():
    index = random.randint(0, 6)
    shape = SHAPES[index]
    color = COLORS[index]
    min_y = min(y for _, y in shape)
    return {'shape': shape, 'color': color, 'x': 4, 'y': -min_y}

def collides(piece):
    for px, py in piece['shape']:
        x = piece['x'] + px
        y = piece['y'] + py
        if x < 0 or x >= COLS or y >= ROWS or (y >= 0 and grid[y][x] != 0):
            return True
    return False

def can_move(piece, dx, dy):
    temp_piece = piece.copy()
    temp_piece['x'] += dx
    temp_piece['y'] += dy
    return not collides(temp_piece)

def rotate_piece(piece):
    rotated_shape = [(y, -x) for x, y in piece['shape']]
    temp_piece = piece.copy()
    temp_piece['shape'] = rotated_shape
    if not collides(temp_piece):
        piece['shape'] = rotated_shape

def land_piece(piece):
    global score, total_lines_cleared, level, drop_interval
    for px, py in piece['shape']:
        x = piece['x'] + px
        y = piece['y'] + py
        if y >= 0:
            grid[y][x] = piece['color']
    complete_rows = [y for y in range(ROWS) if all(grid[y])]
    num_lines = len(complete_rows)
    if num_lines > 0:
        for y in sorted(complete_rows, reverse=True):
            del grid[y]
        for _ in range(num_lines):
            grid.insert(0, [0] * COLS)
        score += [0, 100, 300, 600, 1000][min(num_lines, 4)]
        total_lines_cleared += num_lines
        if total_lines_cleared // 10 >= level:
            level += 1
            drop_interval = initial_interval * (0.9 ** (level - 1))

def draw_grid():
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x] != 0:
                pygame.draw.rect(screen, grid[y][x],
                                 (x * BLOCK_SIZE, SCORE_HEIGHT + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))
    for y in range(ROWS + 1):
        pygame.draw.line(screen, GRAY, (0, SCORE_HEIGHT + y * BLOCK_SIZE),
                         (SCREEN_WIDTH, SCORE_HEIGHT + y * BLOCK_SIZE))
    for x in range(COLS + 1):
        pygame.draw.line(screen, GRAY, (x * BLOCK_SIZE, SCORE_HEIGHT),
                         (x * BLOCK_SIZE, SCREEN_HEIGHT))

def draw_piece(piece):
    for px, py in piece['shape']:
        x = piece['x'] + px
        y = piece['y'] + py
        if y >= 0:
            pygame.draw.rect(screen, piece['color'],
                             (x * BLOCK_SIZE, SCORE_HEIGHT + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE))

def draw_score():
    text = font.render(f'Score: {score}', True, WHITE)
    screen.blit(text, (10, 5))

def draw_centered_text(text, y, font_size=24):
    font = pygame.font.SysFont('Arial', font_size)
    text_surface = font.render(text, True, WHITE)
    text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, y))
    screen.blit(text_surface, text_rect)

def init_game():
    global score, total_lines_cleared, level, drop_interval, drop_timer, grid, piece
    score = 0
    total_lines_cleared = 0
    level = 1
    drop_interval = initial_interval
    drop_timer = 0
    grid = [[0] * COLS for _ in range(ROWS)]
    piece = generate_new_piece()

# Setup function for initialization
def setup():
    pass  # Already initialized above

# Update loop
def update_loop():
    global drop_timer, piece, game_state
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            return
        elif event.type == pygame.KEYDOWN:
            if game_state == 'menu':
                if event.key == pygame.K_s:
                    init_game()
                    game_state = 'playing'
                elif event.key == pygame.K_c:
                    game_state = 'credits'
            elif game_state == 'credits':
                if event.key == pygame.K_m:
                    game_state = 'menu'
            elif game_state == 'playing':
                if event.key == pygame.K_LEFT and can_move(piece, -1, 0):
                    piece['x'] -= 1
                elif event.key == pygame.K_RIGHT and can_move(piece, 1, 0):
                    piece['x'] += 1
                elif event.key == pygame.K_DOWN and can_move(piece, 0, 1):
                    piece['y'] += 1
                elif event.key == pygame.K_UP:
                    rotate_piece(piece)

    if game_state == 'playing':
        dt = clock.tick(FPS) / 1000
        drop_timer += dt
        if drop_timer >= drop_interval:
            if can_move(piece, 0, 1):
                piece['y'] += 1
            else:
                land_piece(piece)
                piece = generate_new_piece()
                if collides(piece):
                    game_state = 'menu'
            drop_timer = 0

    screen.fill(BLACK)
    if game_state == 'menu':
        draw_centered_text("Tetris", 100, font_size=48)
        draw_centered_text("Press S to Start", 200)
        draw_centered_text("Press C for Credits", 250)
    elif game_state == 'credits':
        draw_centered_text("CREDITS TO TETRIS COMPANY @CATAI [C] 199X-20XX", 200)
        draw_centered_text("Press M to return to Menu", 250)
    elif game_state == 'playing':
        draw_grid()
        draw_piece(piece)
        draw_score()
    pygame.display.flip()

# Main async loop for Pyodide compatibility
async def main():
    setup()
    while True:
        update_loop()
        await asyncio.sleep(1.0 / FPS)

# Run the game
if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
