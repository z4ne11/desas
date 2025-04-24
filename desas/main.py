import pygame
import sqlite3
import requests
import json
import time
from datetime import datetime
import os

pygame.init()

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 450
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 25
CELL_SIZE = 75
GRID_SIZE = 3
grid_pixel_size = GRID_SIZE * CELL_SIZE
GRID_LEFT = 278
GRID_TOP = 130

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PINK = (255, 192, 203)
LIGHT_PINK = (255, 218, 224)

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Latvju Desiņas")

def load_images():
    assets = {}
    try:
        assets['bg_menu'] = pygame.image.load(os.path.join('assets', '1.png'))
        assets['bg_character'] = pygame.image.load(os.path.join('assets', '2.png'))
        assets['bg_game'] = pygame.image.load(os.path.join('assets', '3.png'))
        assets['bg_end'] = pygame.image.load(os.path.join('assets', '4.png'))
        
        sausage_files = [
            'image-removebg-preview (9).png',
            'image-removebg-preview (10).png',
            'image-removebg-preview (12).png',
            'image-removebg-preview (13).png',
            'image-removebg-preview (14).png',
            'image-removebg-preview (15).png',
            'image-removebg-preview (16).png',
            'image-removebg-preview (17).png',
            'image-removebg-preview (18).png'
        ]
        for i, file in enumerate(sausage_files):
            try:
                img = pygame.image.load(os.path.join('assets', 'desasSpeletajam', file))
                assets[f'sausage{i}'] = img
            except pygame.error:
                print(f"Could not load sausage image: {file}")
                assets[f'sausage{i}'] = pygame.Surface((50, 100))
                assets[f'sausage{i}'].fill(PINK)
    except Exception as e:
        print(f"Error loading assets: {e}")
    return assets

def setup_database():
    conn = sqlite3.connect('game_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS games
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  player_character TEXT,
                  result TEXT,
                  duration REAL,
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

class Button:
    def __init__(self, x, y, width, height, text, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.font = pygame.font.Font(None, 32)

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class SpeechBubble:
    def __init__(self, text, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.Font(None, 40)
        
    def draw(self, surface):
        pygame.draw.polygon(surface, WHITE, [
            (self.rect.x, self.rect.y),
            (self.rect.x + self.rect.width, self.rect.y),
            (self.rect.x + self.rect.width, self.rect.y + self.rect.height),
            (self.rect.x + self.rect.width//2 + 20, self.rect.y + self.rect.height),
            (self.rect.x + self.rect.width//2, self.rect.y + self.rect.height + 20),
            (self.rect.x + self.rect.width//2 - 20, self.rect.y + self.rect.height),
            (self.rect.x, self.rect.y + self.rect.height),
        ])
        pygame.draw.polygon(surface, BLACK, [
            (self.rect.x, self.rect.y),
            (self.rect.x + self.rect.width, self.rect.y),
            (self.rect.x + self.rect.width, self.rect.y + self.rect.height),
            (self.rect.x + self.rect.width//2 + 20, self.rect.y + self.rect.height),
            (self.rect.x + self.rect.width//2, self.rect.y + self.rect.height + 20),
            (self.rect.x + self.rect.width//2 - 20, self.rect.y + self.rect.height),
            (self.rect.x, self.rect.y + self.rect.height),
        ], 2)
        
        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

class Game:
    def __init__(self):
        self.state = "START"
        self.board = [['' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.current_player = 'X'
        self.winner = None
        self.game_start_time = None
        self.stats = {'wins': 0, 'losses': 0, 'draws': 0}
        self.selected_character = 0
        self.assets = load_images()
        self.characters = [f'sausage{i}' for i in range(9)]
        self.fun_fact = ""

        self.start_button = Button(325,245,
                                 BUTTON_WIDTH, BUTTON_HEIGHT,
                                 "Sākt spēli", WHITE)
        
        self.confirm_button = Button(325,393,
                                   BUTTON_WIDTH, BUTTON_HEIGHT,
                                   "Apstiprināt", WHITE)
        
        self.left_button = Button(170, 200,
                                50, 50, "<", WHITE)
        
        self.right_button = Button(580,200,
                                 50, 50, ">", WHITE)
        
        self.restart_button = Button(110,145,
                                   BUTTON_WIDTH, BUTTON_HEIGHT,
                                   "Turpināt spēli", WHITE)
        
        self.menu_button = Button(112,199,
                                BUTTON_WIDTH, BUTTON_HEIGHT,
                                "Beigt", WHITE)
        
    def save_game_result(self, result):
        duration = time.time() - self.game_start_time
        conn = sqlite3.connect('game_history.db')
        c = conn.cursor()
        c.execute('''INSERT INTO games (player_character, result, duration, timestamp)
                    VALUES (?, ?, ?, ?)''',
                 (self.characters[self.selected_character],
                  result,
                  duration,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def get_fun_fact(self):
        try:
            response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en")
            data = response.json()
            return data.get('text', 'Failed to load fun fact')
        except:
            return "Failed to load fun fact"

    def get_game_history(self):
        conn = sqlite3.connect('game_history.db')
        c = conn.cursor()
        c.execute('''SELECT result, duration, timestamp 
                    FROM games ORDER BY timestamp DESC LIMIT 5''')
        history = c.fetchall()
        conn.close()
        return history

    def draw_background(self, bg_key):
        try:
            bg = self.assets[bg_key]
            bg_width = WINDOW_WIDTH
            bg_height = int(bg_width * bg.get_height() / bg.get_width())
            bg = pygame.transform.scale(bg, (bg_width, bg_height))
            screen.blit(bg, (0, (WINDOW_HEIGHT - bg_height) // 2))
        except Exception as e:
            print(f"Error displaying background: {e}")
            screen.fill(WHITE)

    def draw_start_screen(self):
        self.draw_background('bg_menu')
        self.start_button.draw(screen)
        pygame.display.flip()

    def draw_character_select(self):
        self.draw_background('bg_character')
        
        try:
            character = self.assets[self.characters[self.selected_character]]
            char_width = 150
            char_height = int(char_width * character.get_height() / character.get_width())
            character = pygame.transform.scale(character, (char_width, char_height))
            screen.blit(character, (WINDOW_WIDTH//2 - char_width//2,
                                  WINDOW_HEIGHT//2 - char_height//2))
        except Exception as e:
            print(f"Error displaying character: {e}")
        
        self.left_button.draw(screen)
        self.right_button.draw(screen)
        self.confirm_button.draw(screen)
        pygame.display.flip()

    def draw_game_board(self):
        self.draw_background('bg_game')

        grid_surface = pygame.Surface((grid_pixel_size, grid_pixel_size), pygame.SRCALPHA)
        grid_surface.fill((255, 255, 255, 0))
        
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if self.board[i][j]:
                    try:
                        if self.board[i][j] == 'X':
                            piece = self.assets[self.characters[self.selected_character]]
                        else:
                            computer_char = (self.selected_character + 4) % len(self.characters)
                            piece = self.assets[self.characters[computer_char]]
                        
                        piece_width = CELL_SIZE - 20
                        piece_height = int(piece_width * piece.get_height() / piece.get_width())
                        piece = pygame.transform.scale(piece, (piece_width, piece_height))
                        
                        x = j*CELL_SIZE + (CELL_SIZE - piece_width)//2
                        y = i*CELL_SIZE + (CELL_SIZE - piece_height)//2
                        grid_surface.blit(piece, (x, y))
                    except Exception as e:
                        print(f"Error displaying piece: {e}")
        
        screen.blit(grid_surface, (GRID_LEFT, GRID_TOP))
        pygame.display.flip()

    def draw_end_screen(self):
        self.draw_background('bg_end')
        window_surface = pygame.Surface((700, 400), pygame.SRCALPHA)
        screen.blit(window_surface, (50, 100))

        font = pygame.font.Font(None, 33)
        result_text = "Neizšķirts!" if self.winner is None else f"{':D' if self.winner == 'X' else 'D:'}"
        text_surface = font.render(result_text, True, BLACK)
        screen.blit(text_surface, (380,90))
        
        stats_font = pygame.font.Font(None, 28)
        lines = [
            f"Uzvaras: {self.stats['wins']}",
            f"Zaudējumi: {self.stats['losses']}",
            f"Neizšķirti: {self.stats['draws']}"
        ]

        x = 550
        y = 300
        line_spacing = 30

        for i, line in enumerate(lines):
            line_surface = stats_font.render(line, True, BLACK)
            screen.blit(line_surface, (x, y + i * line_spacing))

        history = self.get_game_history()
        y_offset = 58
        history_font = pygame.font.Font(None, 22)
        for result, duration, timestamp in history:
            history_text = f"{timestamp}: {result} ({duration:.1f}s)"
            history_surface = history_font.render(history_text, True, BLACK)
            screen.blit(history_surface, (510, y_offset))
            y_offset += 30
        
        def wrap_text(text, font, max_width):
            words = text.split(' ')
            lines = []
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if font.size(test_line)[0] < max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word + " "
            lines.append(current_line)
            return lines

        fact = self.fun_fact
        fact_font = pygame.font.Font(None, 20)
        wrapped_lines = wrap_text(fact, fact_font, 240)
        y = 327
        for line in wrapped_lines:
            line_surface = fact_font.render(line, True, BLACK)
            screen.blit(line_surface, (30, y))
            y += 26
        
        self.restart_button.draw(screen)
        self.menu_button.draw(screen)
        pygame.display.flip()

    def check_winner(self):
        for row in self.board:
            if row.count(row[0]) == len(row) and row[0] != '':
                return row[0]

        for col in range(GRID_SIZE):
            if self.board[0][col] != '' and all(self.board[row][col] == self.board[0][col] for row in range(GRID_SIZE)):
                return self.board[0][col]

        if self.board[0][0] != '' and all(self.board[i][i] == self.board[0][0] for i in range(GRID_SIZE)):
            return self.board[0][0]
        if self.board[0][2] != '' and all(self.board[i][2-i] == self.board[0][2] for i in range(GRID_SIZE)):
            return self.board[0][2]

        if all(all(cell != '' for cell in row) for row in self.board):
            return None
        
        return False

    def make_computer_move(self):
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if self.board[i][j] == '':
                    self.board[i][j] = 'O'
                    return

def main():
    setup_database()
    game = Game()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                
                if game.state == "START":
                    if game.start_button.is_clicked(pos):
                        game.state = "CHARACTER_SELECT"
                
                elif game.state == "CHARACTER_SELECT":
                    if game.left_button.is_clicked(pos):
                        game.selected_character = (game.selected_character - 1) % len(game.characters)
                    elif game.right_button.is_clicked(pos):
                        game.selected_character = (game.selected_character + 1) % len(game.characters)
                    elif game.confirm_button.is_clicked(pos):
                        game.state = "PLAYING"
                        game.game_start_time = time.time()
                
                elif game.state == "PLAYING":
                    board_x = (pos[0] - GRID_LEFT) // CELL_SIZE
                    board_y = (pos[1] - GRID_TOP) // CELL_SIZE

                    if 0 <= board_x < GRID_SIZE and 0 <= board_y < GRID_SIZE:
                        if game.board[board_y][board_x] == '':
                            game.board[board_y][board_x] = 'X'
                            winner = game.check_winner()
                            if winner:
                                game.winner = winner
                                if winner == 'X':
                                    game.stats['wins'] += 1
                                else:
                                    game.stats['losses'] += 1
                                game.save_game_result('win' if winner == 'X' else 'loss')
                                game.fun_fact = game.get_fun_fact()
                                game.state = "END"
                            elif winner is None:
                                game.stats['draws'] += 1
                                game.save_game_result('draw')
                                game.fun_fact = game.get_fun_fact()
                                game.state = "END"
                            else:
                                game.make_computer_move()
                                winner = game.check_winner()
                                if winner:
                                    game.winner = winner
                                    if winner == 'X':
                                        game.stats['wins'] += 1
                                    else:
                                        game.stats['losses'] += 1
                                    game.save_game_result('win' if winner == 'X' else 'loss')
                                    game.fun_fact = game.get_fun_fact()
                                    game.state = "END"
                                elif winner is None:
                                    game.stats['draws'] += 1
                                    game.save_game_result('draw')
                                    game.fun_fact = game.get_fun_fact()
                                    game.state = "END"
                
                elif game.state == "END":
                    if game.restart_button.is_clicked(pos):
                        game.board = [['' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
                        game.winner = None
                        game.game_start_time = time.time()
                        game.state = "PLAYING"
                    elif game.menu_button.is_clicked(pos):
                        game.board = [['' for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
                        game.winner = None
                        game.state = "START"
        
        if game.state == "START":
            game.draw_start_screen()
        elif game.state == "CHARACTER_SELECT":
            game.draw_character_select()
        elif game.state == "PLAYING":
            game.draw_game_board()
        elif game.state == "END":
            game.draw_end_screen()
            

    pygame.quit()

if __name__ == "__main__":
    main() 