"""REST OF THE GAME"""
"""RUN THIS ONLY AFTER RUNNING THE PREVIOUS CODE"""
"""YOU ONLY NEED TO RUN THE PREVIOUS CODE ONCE"""


import gc
from machine import Pin, SPI, WDT, freq
import time
import math
import random
import sys
import _thread
from Bit import display
from Bit import *
begin()
n = 2
raySel = 4
FOV = math.pi / n 
current_fov_index = 1
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 128
FOV = math.pi / n
HALF_FOV = FOV / 2
NUM_RAYS = SCREEN_WIDTH
MAX_DEPTH = 6
FOVn = 100
c = 0
freq(240000000)
GRAY = 0xAD55
WHITE = 0xFFFF
WALLS = 0xC020
BLACK = 0x0000
RED = 0x1800
SKY = 0x6CDF
GREEN = 0x0401
ORB = 0x07FC
BLUE = 0x03DF
RED = 0xF041
PURPLE = 0xB81F
GROUND = 0x81C0
YELLOW = 0xEFE0
LAVANDER = 0x625B
ENEMY_COL = 0x0C00
move_speed = 0.25
rot_speed = 0.2
max_player_health = 3
player_health = 3
enemy_stun_timer = 0
last_hit_time = 0
enemy_speed = 0.025
enemy_path = []
enemy_target_tile = None
random_target_tile = None
recently_hurt = False
difficulty = 0
batteryCharges = 5
last_brightness_reset = 0
cooldown_progress = 1 
orbsToPlace = 5
player_x, player_y = 2, 2
player_angle = 90
enemy_x, enemy_y = 2, 2
lvl1_x, lvl1_y = 14, 18
mapSize = 11
brightness_factor = 1.0
brightness_decreasing = True  
brightness_min = 0.25
brightness_max = 1.0
brightness_speed = 0.025
angle_step = FOV / NUM_RAYS
angle_lookup = [player_angle - HALF_FOV + i * angle_step for i in range(NUM_RAYS)]
cos_lookup = [math.cos(angle) for angle in angle_lookup]
sin_lookup = [math.sin(angle) for angle in angle_lookup]
collectedR = False
gc.collect()
scene = [ ]
print("Set world buffer")
orbs = [ ]
IMAGE_WIDTH = 128
IMAGE_HEIGHT = 128
BUTTON_WIDTH = 80
BUTTON_HEIGHT = 15
GUMB_15_U_WIDTH = 15
GUMB_15_U_HEIGHT = 15
GUMB_15_WIDTH = 15
GUMB_15_HEIGHT = 15
BUTTON_100_WIDTH = 100
BUTTON_100_HEIGHT = 15
def get_asset(filename):
    with open(filename, 'rb') as f:
        width = int.from_bytes(f.read(2), 'little')
        height = int.from_bytes(f.read(2), 'little')
        palette_len = int.from_bytes(f.read(1), 'little')
        palette = [int.from_bytes(f.read(2), 'little') for _ in range(palette_len)]
        data = bytearray(f.read())
    return width, height, palette, data

class ST7735:
    def __init__(self, spi, dc, rst, bl, width=128, height=128):
        gc.collect()
        self.spi = spi
        self.dc = dc
        self.rst = rst
        self.width = width
        self.height = height
        self.bl = bl
        self.frames = {}
        print("\nInitializing ST7735 display...")
        print("Clearing memory, for resource allocation...")
        gc.collect()
        print("Free memory:", gc.mem_free())
        self.WORLD_BUFFER = display.buffer
        self.FONT_WIDTH = 6
        self.FONT_HEIGHT = 8
        self.CHAR_SPACING = 1
        self.dc.init(Pin.OUT, value=0)
        self.bl.init(Pin.OUT, value=0)
        self.rst.init(Pin.OUT, value=1)
        self.reset()
        self.init_display()
    def reset(self):
        self.rst.value(1)
        time.sleep_ms(100)
        self.rst.value(0)
        time.sleep_ms(100)
        self.rst.value(1)
        time.sleep_ms(150)
    def write_cmd(self, cmd):
        self.dc.value(0)
        self.spi.write(bytearray([cmd]))
    def write_data(self, data):
        self.dc.value(1)
        if isinstance(data, int):
            self.spi.write(bytearray([data]))
        else:
            self.spi.write(data)
    def init_display(self):
        self.write_cmd(0x01)
        time.sleep_ms(150)
        self.write_cmd(0x11)
        time.sleep_ms(150)
        self.write_cmd(0x3A)
        self.write_data(0x05)
        time.sleep_ms(10)
        self.write_cmd(0x36)
        self.write_data(0xC8)
        self.write_cmd(0x2A)
        self.write_data(bytearray([0x00, 0x00, 0x00, self.width - 1]))
        self.write_cmd(0x2B)
        self.write_data(bytearray([0x00, 0x00, 0x00, self.height - 1]))
        self.write_cmd(0x29)
        time.sleep_ms(100)
        self.backlight(True)
        self.clear(0x0000)
        self.refresh()
    def backlight(self, on):
        self.bl.value(not on)
    def set_window(self, x0, y0, x1, y1):
        self.write_cmd(0x2A)
        self.write_data(bytearray([0x00, x0, 0x00, x1]))
        self.write_cmd(0x2B)
        self.write_data(bytearray([0x00, y0, 0x00, y1]))
        self.write_cmd(0x2C)
    def colorCalc(self, color):
        high = (color >> 8) & 0xFF
        low = color & 0xFF
        return high, low
    def buffer_address(self, x, y):
        return (x + y * self.width) * 2
    def pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            addr = self.buffer_address(x, y)
            high, low = self.colorCalc(color)
            self.WORLD_BUFFER[addr] = high
            self.WORLD_BUFFER[addr + 1] = low
    def clear(self, color=0x0000):
        high, low = self.colorCalc(color)
        for i in range(0, len(self.WORLD_BUFFER), 2):
            self.WORLD_BUFFER[i] = high
            self.WORLD_BUFFER[i + 1] = low
    def refresh(self):
        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.dc.value(1)
        self.spi.write(self.WORLD_BUFFER)
    def rect(self, x, y, w, h, color):
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0
        if x + w > self.width:
            w = self.width - x
        if y + h > self.height:
            h = self.height - y
        if w <= 0 or h <= 0:
            return
        high, low = self.colorCalc(color)
        for i in range(w):
            addr_top = ((x + i) + y * self.width) * 2
            self.WORLD_BUFFER[addr_top] = high
            self.WORLD_BUFFER[addr_top + 1] = low
            addr_bottom = ((x + i) + (y + h - 1) * self.width) * 2
            self.WORLD_BUFFER[addr_bottom] = high
            self.WORLD_BUFFER[addr_bottom + 1] = low
        for i in range(h):
            addr_left = (x + (y + i) * self.width) * 2
            self.WORLD_BUFFER[addr_left] = high
            self.WORLD_BUFFER[addr_left + 1] = low
            addr_right = ((x + w - 1) + (y + i) * self.width) * 2
            self.WORLD_BUFFER[addr_right] = high
            self.WORLD_BUFFER[addr_right + 1] = low
    def rectF(self, x, y, w, h, color):
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0
        if x + w > self.width:
            w = self.width - x
        if y + h > self.height:
            h = self.height - y
        if w <= 0 or h <= 0:
            return
        high, low = self.colorCalc(color)
        row_pattern = bytearray(w * 2)
        for i in range(0, w * 2, 2):
            row_pattern[i] = high
            row_pattern[i + 1] = low
        for y_pos in range(y, y + h):
            start_addr = (x + y_pos * self.width) * 2
            for i in range(len(row_pattern)):
                self.WORLD_BUFFER[start_addr + i] = row_pattern[i]
    def draw_rle_image_to_buffer(self, filename, *_args, **_kwargs):
        width, height, palette, rle_data = get_asset(filename)
        x = y = i = 0
        while i < len(rle_data):
            count = int(rle_data[i])
            color_index = int(rle_data[i + 1])
            i += 2
            if color_index == 255:
                for _ in range(count):
                    y += 1
                    if y >= height:
                        y = 0
                        x += 1
                        if x >= width:
                            break
                continue
            color = palette[color_index]
            high, low = self.colorCalc(color)
            for _ in range(count):
                if x < width and y < height:
                    px, py = x, y
                    if 0 <= px < self.width and 0 <= py < self.height:
                        addr = self.buffer_address(px, py)
                        self.WORLD_BUFFER[addr] = high
                        self.WORLD_BUFFER[addr + 1] = low
                y += 1
                if y >= height:
                    y = 0
                    x += 1
                    if x >= width:
                        break

    def draw_rle_image_store(self, name, rle_data, palette, width, height):
        total_pixels = width * height
        frame = bytearray(total_pixels * 2)
        x = y = i = 0
        while i < len(rle_data):
            count = int(rle_data[i])
            color_index = int(rle_data[i + 1])
            i += 2
            if color_index == 255:
                x += count
                while x >= width:
                    x -= width
                    y += 1
                continue
            color = palette[color_index]
            high, low = self.colorCalc(color)
            for _ in range(count):
                if x < width and y < height:
                    p = (x + y * width) * 2
                    frame[p] = high
                    frame[p + 1] = low
                x += 1
                if x >= width:
                    x = 0
                    y += 1
                    if y >= height:
                        break
        self.frames[name] = frame
    def draw_frame_to_buffer(self, frame_name, x, y, width, height):
        if frame_name not in self.frames:
            try:
                w, h, palette, rle_data = get_asset(frame_name + ".dat")
                self.draw_rle_image_store(frame_name, rle_data, palette, w, h)
            except Exception as e:
                print("Failed to load frame from file:", frame_name, e)
                return
        frame = self.frames[frame_name]
        for dy in range(height):
            if y + dy >= self.height:
                break
            for dx in range(width):
                if x + dx >= self.width:
                    break
                src_addr = (dx + dy * width) * 2
                dst_addr = self.buffer_address(x + dx, y + dy)
                if src_addr < len(frame) - 1 and dst_addr < len(self.WORLD_BUFFER) - 1:
                    self.WORLD_BUFFER[dst_addr] = frame[src_addr]
                    self.WORLD_BUFFER[dst_addr + 1] = frame[src_addr + 1]

    def get_char_index(self, char):
        if 'A' <= char <= 'Z':
            return ord(char) - ord('A')
        elif 'a' <= char <= 'z':
            return 26 + (ord(char) - ord('a'))
        elif '0' <= char <= '9':
            return 52 + (ord(char) - ord('0'))
        elif char == '+': return 62
        elif char == '-': return 63
        elif char == '_': return 64
        elif char == '.': return 65
        elif char == ',': return 66
        elif char == '=': return 67
        elif char == '?': return 68
        elif char == '!': return 69
        elif char == '(': return 70
        elif char == ')': return 71
        else: return -1
    def draw_char(self, font_bytes, x, y, char, color, bg_color=None):
        char_index = self.get_char_index(char)
        if char_index < 0:
            return self.FONT_WIDTH
        bytes_per_char = self.FONT_WIDTH
        start_byte = char_index * bytes_per_char
        if start_byte + bytes_per_char > len(font_bytes):
            return self.FONT_WIDTH
        for dy in range(self.FONT_HEIGHT):
            for dx in range(self.FONT_WIDTH):
                byte_offset = start_byte + dx
                if byte_offset < len(font_bytes):
                    bit_is_set = (font_bytes[byte_offset] & (1 << dy)) != 0
                    px, py = x + dx, y + dy
                    if 0 <= px < self.width and 0 <= py < self.height:
                        if bit_is_set:
                            self.pixel(px, py, color)
                        elif bg_color is not None:
                            self.pixel(px, py, bg_color)
        return self.FONT_WIDTH + self.CHAR_SPACING
    def draw_text(self, font_bytes, x, y, text, color, bg_color=None):
        cursor_x = x
        for char in str(text):
            if char == ' ':
                cursor_x += self.FONT_WIDTH
                continue
            char_width = self.draw_char(font_bytes, cursor_x, y, char, color, bg_color)
            cursor_x += char_width
            if cursor_x >= self.width:
                break
        return cursor_x - x
    def fill(self, color):
        self.clear(color)
    def draw_precompiled_rle(self, start_x, start_y, width, height, frame):
        self.set_window(start_x, start_y, start_x + width - 1, start_y + height - 1)
        self.dc.value(1)
        self.spi.write(frame)
    def draw_frame_by_name(self, name, x, y, width, height):
        if name in self.frames:
            self.draw_precompiled_rle(x, y, width, height, self.frames[name])


spi = SPI(1, baudrate=240000000, polarity=0, phase=0, sck=Pin(13), mosi=Pin(14))
dc = Pin(15, Pin.OUT)
rst = Pin(16, Pin.OUT)
bl = Pin(12, Pin.OUT)
displayC = ST7735(spi, dc, rst, bl)

font_bytes = bytearray([
0x7E, 0x09, 0x09, 0x09, 0x7E, 0x00, 0x7F, 0x49, 0x49, 0x49, 0x49, 0x36, 
0x3E, 0x41, 0x41, 0x41, 0x41, 0x22, 0x7F, 0x41, 0x41, 0x41, 0x41, 0x3E, 
0x7F, 0x45, 0x45, 0x45, 0x41, 0x41, 0x7F, 0x05, 0x05, 0x05, 0x01, 0x01, 
0x3E, 0x41, 0x41, 0x41, 0x49, 0x39, 0x7F, 0x08, 0x08, 0x08, 0x08, 0x7F, 
0x41, 0x7F, 0x41, 0x00, 0x00, 0x00, 0x20, 0x40, 0x40, 0x3F, 0x00, 0x00, 
0x7F, 0x08, 0x08, 0x14, 0x62, 0x01, 0x7F, 0x40, 0x40, 0x40, 0x40, 0x40, 
0x7F, 0x02, 0x04, 0x02, 0x7F, 0x00, 0x7F, 0x02, 0x04, 0x08, 0x7F, 0x00, 
0x3E, 0x41, 0x41, 0x41, 0x41, 0x3E, 0x7F, 0x09, 0x09, 0x09, 0x09, 0x06, 
0x1E, 0x21, 0x21, 0x31, 0x21, 0x5E, 0x7F, 0x09, 0x19, 0x29, 0x49, 0x06, 
0x46, 0x49, 0x49, 0x49, 0x49, 0x11, 0x01, 0x01, 0x7F, 0x01, 0x01, 0x00, 
0x3F, 0x40, 0x40, 0x40, 0x40, 0x3F, 0x07, 0x18, 0x60, 0x18, 0x07, 0x00, 
0x7F, 0x20, 0x10, 0x20, 0x7F, 0x00, 0x63, 0x14, 0x08, 0x14, 0x63, 0x00, 
0x01, 0x02, 0x7C, 0x02, 0x01, 0x00, 0x61, 0x51, 0x49, 0x45, 0x43, 0x00, 
0x20, 0x54, 0x54, 0x54, 0x78, 0x00, 0x7F, 0x50, 0x48, 0x48, 0x30, 0x00, 
0x38, 0x44, 0x44, 0x44, 0x28, 0x00, 0x78, 0x44, 0x44, 0x44, 0x7F, 0x00, 
0x3C, 0x52, 0x52, 0x52, 0x4C, 0x00, 0x04, 0x7F, 0x05, 0x05, 0x00, 0x00, 
0x22, 0x45, 0x45, 0x45, 0x3F, 0x00, 0x7F, 0x10, 0x08, 0x70, 0x00, 0x00, 
0x7D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x40, 0x40, 0x3D, 0x00, 0x00, 
0x3F, 0x08, 0x14, 0x22, 0x00, 0x00, 0x3F, 0x40, 0x00, 0x00, 0x00, 0x00, 
0x78, 0x08, 0x70, 0x08, 0x70, 0x00, 0x78, 0x08, 0x08, 0x70, 0x00, 0x00, 
0x38, 0x44, 0x44, 0x44, 0x38, 0x00, 0x3F, 0x0A, 0x09, 0x09, 0x06, 0x00, 
0x0E, 0x11, 0x11, 0x12, 0x7F, 0x00, 0x3F, 0x02, 0x01, 0x01, 0x02, 0x00, 
0x48, 0x54, 0x54, 0x54, 0x24, 0x00, 0x04, 0x3E, 0x44, 0x00, 0x00, 0x00, 
0x3C, 0x40, 0x40, 0x40, 0x7C, 0x00, 0x18, 0x20, 0x40, 0x20, 0x18, 0x00, 
0x38, 0x40, 0x70, 0x40, 0x78, 0x00, 0x44, 0x28, 0x10, 0x28, 0x44, 0x00, 
0x4C, 0x50, 0x50, 0x3C, 0x00, 0x00, 0x64, 0x54, 0x54, 0x4C, 0x00, 0x00, 
0x3C, 0x62, 0x5A, 0x46, 0x3C, 0x00, 0x44, 0x7E, 0x40, 0x00, 0x00, 0x00, 
0x64, 0x52, 0x4A, 0x44, 0x00, 0x00, 0x22, 0x41, 0x49, 0x36, 0x00, 0x00, 
0x30, 0x28, 0x24, 0x7E, 0x20, 0x00, 0x4E, 0x52, 0x52, 0x52, 0x20, 0x00, 
0x38, 0x54, 0x52, 0x52, 0x20, 0x00, 0x06, 0x72, 0x0A, 0x06, 0x00, 0x00, 
0x36, 0x49, 0x49, 0x49, 0x36, 0x00, 0x0C, 0x52, 0x52, 0x3C, 0x00, 0x00, 
0x00, 0x10, 0x38, 0x10, 0x00, 0x00, 0x00, 0x10, 0x10, 0x10, 0x00, 0x00, 
0x40, 0x40, 0x40, 0x40, 0x40, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 
0x40, 0x30, 0x00, 0x00, 0x00, 0x00, 0x28, 0x28, 0x28, 0x28, 0x00, 0x00, 
0x02, 0x51, 0x09, 0x06, 0x00, 0x00, 0x5E, 0x00, 0x00, 0x00, 0x00, 0x00, 
0x3E, 0x41, 0x00, 0x00, 0x00, 0x00, 0x3E, 0x41, 0x00, 0x00, 0x00, 0x00, ])
def adjust_color_brightness(color, brightness):
    red = (color >> 11) & 0x1F
    green = (color >> 5) & 0x3F
    blue = color & 0x1F
    red = int(red * brightness)
    green = int(green * brightness)
    blue = int(blue * brightness)
    red = min(red, 0x1F)
    green = min(green, 0x3F)
    blue = min(blue, 0x1F)
    return (red << 11) | (green << 5) | blue
def find_empty_cells(maze):
    empty_cells = []
    for y in range(len(maze)):
        for x in range(len(maze[0])):
            if maze[y][x] == 0:
                empty_cells.append((x, y))
    return empty_cells
def random_empty_cell(maze):
    empty_cells = [
        (x, y)
        for y in range(len(maze))
        for x in range(len(maze[0]))
        if maze[y][x] == 0
    ]
    return random.choice(empty_cells) if empty_cells else None
def place_orbs(num_orbs=5):
    global orbs
    empty_cells = find_empty_cells(scene)
    num_orbs = min(num_orbs, len(empty_cells))
    selected_positions = []
    for _ in range(num_orbs):
        if empty_cells:
            index = random.randint(0, len(empty_cells) - 1)
            pos = empty_cells.pop(index)
            centered_pos = (pos[0] + 0.5, pos[1] + 0.5)
            selected_positions.append(centered_pos)
    orbs = selected_positions
    print(f"Placed {len(orbs)} orbs at: {orbs}")
def print_maze(maze):
    for row in maze:
        print("".join("#" if cell == 1 else " " for cell in row))
def generate_map_with_rooms(rows, cols, max_room_size, num_rooms, start_x=1, start_y=1):
    map_grid = [[1 for _ in range(cols)] for _ in range(rows)]
    rooms = []
    for _ in range(num_rooms):
        room_width = random.randint(3, max_room_size)
        room_height = random.randint(3, max_room_size)
        room_x = random.randint(1, cols - room_width - 1)
        room_y = random.randint(1, rows - room_height - 1)
        overlap = False
        for other_room in rooms:
            other_x, other_y, other_width, other_height = other_room
            if (room_x < other_x + other_width and room_x + room_width > other_x and
                room_y < other_y + other_height and room_y + room_height > other_y):
                overlap = True
                break
        if not overlap:
            rooms.append((room_x, room_y, room_width, room_height))
            for y in range(room_y, room_y + room_height):
                for x in range(room_x, room_x + room_width):
                    map_grid[y][x] = 0
    if rooms:
        first_room_x, first_room_y, first_room_width, first_room_height = rooms[0]
        first_room_center_x = first_room_x + first_room_width // 2
        first_room_center_y = first_room_y + first_room_height // 2
        for x in range(min(start_x, first_room_center_x), max(start_x, first_room_center_x) + 1):
            map_grid[start_y][x] = 0
        for y in range(min(start_y, first_room_center_y), max(start_y, first_room_center_y) + 1):
            map_grid[y][first_room_center_x] = 0
    for i in range(1, len(rooms)):
        x1, y1, w1, h1 = rooms[i - 1]
        x2, y2, w2, h2 = rooms[i]
        center_x1, center_y1 = x1 + w1 // 2, y1 + h1 // 2
        center_x2, center_y2 = x2 + w2 // 2, y2 + h2 // 2
        for x in range(min(center_x1, center_x2), max(center_x1, center_x2) + 1):
            map_grid[center_y1][x] = 0
        for y in range(min(center_y1, center_y2), max(center_y1, center_y2) + 1):
            map_grid[y][center_x2] = 0
    print_maze(map_grid)
    return map_grid
def update_angle_lookup():
    global angle_lookup, cos_lookup, sin_lookup
    angle_step = FOV / (NUM_RAYS - 1)
    angle_lookup = [(player_angle - HALF_FOV + i * angle_step) for i in range(NUM_RAYS)]
    cos_lookup = [math.cos(angle) for angle in angle_lookup]
    sin_lookup = [math.sin(angle) for angle in angle_lookup]
update_angle_lookup()
def cast_ray(angle, ray_id):
    x, y = player_x, player_y
    dx, dy = math.cos(angle), math.sin(angle)
    delta_x = abs(1 / dx) if dx != 0 else 1e30
    delta_y = abs(1 / dy) if dy != 0 else 1e30
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    side_x = (x - int(x)) * delta_x if dx < 0 else (int(x) + 1 - x) * delta_x
    side_y = (y - int(y)) * delta_y if dy < 0 else (int(y) + 1 - y) * delta_y
    for _ in range(MAX_DEPTH):
        if side_x < side_y:
            side_x += delta_x
            x += step_x
            dist = side_x - delta_x
            side = 0
        else:
            side_y += delta_y
            y += step_y
            dist = side_y - delta_y
            side = 1
        if scene[int(y)][int(x)]:
            return dist, scene[int(y)][int(x)], None
    return MAX_DEPTH, 1, None
def handle_input():
    global player_x, player_y, player_angle, orbs, brightness_factor, brightness_decreasing, batteryCharges, collectedR, move_speed, rot_speed, recently_hurt
    buttons.scan()
    if buttons.state(Buttons.Up):
        new_x = player_x + math.cos(player_angle) * move_speed
        new_y = player_y + math.sin(player_angle) * move_speed
        if 0 <= new_x < len(scene[0]) and 0 <= new_y < len(scene):
            if not scene[int(new_y)][int(new_x)]:
                player_x, player_y = new_x, new_y
    if buttons.state(Buttons.Down):
        new_x = player_x - math.cos(player_angle) * move_speed
        new_y = player_y - math.sin(player_angle) * move_speed
        if 0 <= new_x < len(scene[0]) and 0 <= new_y < len(scene):
            if not scene[int(new_y)][int(new_x)]:
                player_x, player_y = new_x, new_y
    if buttons.state(Buttons.Left):
        player_angle -= rot_speed
        update_angle_lookup()
    if buttons.state(Buttons.Right):
        player_angle += rot_speed
        update_angle_lookup()
    for orb in orbs[:]:
        orb_x, orb_y = orb
        if orb_x - 0.3 <= player_x < orb_x + 0.3 and orb_y - 0.3 <= player_y < orb_y + 0.3:
            orbs.remove(orb)
            print(f"Orb collected at position ({orb_x}, {orb_y})!")
            Audio.SFX.orbPickup()
            batteryCharges = 5
            collectedR = True
def TerminateExecution():
    sys.exit()
    raise SystemExit
def draw_heart(display, x, y, color):
    display.line(x, y + 3, x + 2, y + 5, color)
    display.line(x + 2, y + 5, x + 6, y + 0, color)
    display.line(x + 6, y + 0, x + 8, y + 2, color)
    display.line(x + 8, y + 2, x + 4, y + 8, color)
    display.line(x + 4, y + 8, x, y + 3, color)
    display.line(x, y + 3, x + 3, y, color)
def render(display):
    global brightness_factor, collectedR
    display.fill(0)
    for y in range(SCREEN_HEIGHT // 2):
        distance_factor = y / (SCREEN_HEIGHT // 2)
        brightness = max(0, 1 - distance_factor) * brightness_factor
        sky_color = adjust_color_brightness(SKY, brightness)
        display.line(0, y, SCREEN_WIDTH, y, sky_color)
    for y in range(SCREEN_HEIGHT // 2, SCREEN_HEIGHT):
        distance_factor = (y - SCREEN_HEIGHT // 2) / (SCREEN_HEIGHT // 2)
        brightness = max(0, distance_factor) * brightness_factor
        ground_color = adjust_color_brightness(GROUND, brightness)
        display.line(0, y, SCREEN_WIDTH, y, ground_color)
    depth_buffer = [MAX_DEPTH] * SCREEN_WIDTH
    for ray in range(NUM_RAYS):
        depth, wall_type, orb_data = cast_ray(angle_lookup[ray], ray)

        if wall_type > 0:
            wall_height = int(SCREEN_HEIGHT / (depth + 0.0001))
            if wall_type == 1:
                base_red = 0xD1A9
                brightness = max(0, 1 - depth / MAX_DEPTH) * brightness_factor
                red = int((base_red >> 11) * brightness)
                wall_color = (red << 11)
            elif wall_type == 2:
                wall_color = GREEN
            elif wall_type == 3:
                wall_color = GRAY

            display.rect(
                ray,
                (SCREEN_HEIGHT - wall_height) // 2,
                1,
                wall_height,
                wall_color,
                True
            )
            depth_buffer[ray] = depth
    epsilon = 0.0001
    for orb_x, orb_y in orbs:
        rel_x = orb_x - player_x
        rel_y = orb_y - player_y
        dist = math.sqrt(rel_x**2 + rel_y**2) + epsilon
        angle_to_orb = math.atan2(rel_y, rel_x) - player_angle
        while angle_to_orb < -math.pi:
            angle_to_orb += 2 * math.pi
        while angle_to_orb > math.pi:
            angle_to_orb -= 2 * math.pi
        if -HALF_FOV < angle_to_orb < HALF_FOV:
            screen_x = int((angle_to_orb + HALF_FOV) * (SCREEN_WIDTH / FOV))
            orb_size = max(5, int(20 / dist))
            screen_y = SCREEN_HEIGHT // 2
            if dist < depth_buffer[screen_x]:
                display.rect(
                    screen_x - orb_size // 2,
                    screen_y - orb_size // 2,
                    orb_size,
                    orb_size,
                    ORB,
                    True
                )
    rel_x = enemy_x - player_x
    rel_y = enemy_y - player_y
    dist = math.sqrt(rel_x**2 + rel_y**2) + epsilon
    angle_to_enemy = math.atan2(rel_y, rel_x) - player_angle
    while angle_to_enemy < -math.pi:
        angle_to_enemy += 2 * math.pi
    while angle_to_enemy > math.pi:
        angle_to_enemy -= 2 * math.pi
    if -HALF_FOV < angle_to_enemy < HALF_FOV:
        screen_x = int((angle_to_enemy + HALF_FOV) * (SCREEN_WIDTH / FOV))
        enemy_size = max(5, int(40 / dist))
        brightness = max(0, 1 - dist / MAX_DEPTH) * brightness_factor
        enemy_color = adjust_color_brightness(ENEMY_COL, brightness)
        if dist < depth_buffer[screen_x]:
            display.rect(
                screen_x - enemy_size // 2,
                (SCREEN_HEIGHT // 2) - enemy_size // 2,
                enemy_size,
                enemy_size * 2,
                enemy_color,
                True
            )
    batteryDraw()
    if collectedR:
        collectedAnim()
    orbCounter()
    for i in range(player_health):
        heart_x = 4 + i * 12
        heart_y = SCREEN_HEIGHT - 12
        draw_heart(display, heart_x, heart_y, RED)
    if recently_hurt:
        draw_crack()
    display.commit()
def mapRender(display):
    global scene, player_x, player_y, player_angle, orbs
    display.fill(0)
    zoom = 5
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2
    distance_multiplier = 0.2
    orb_illumination_radius = 1.0
    brightness_cutoff = 0.1
    max_render_distance = 10
    cos_angle = math.cos(-player_angle)
    sin_angle = math.sin(-player_angle)
    for y in range(len(scene)):
        for x in range(len(scene[0])):
            if scene[y][x] != 0:
                wall_center_x = x + 0.5 - player_x
                wall_center_y = y + 0.5 - player_y
                distance = math.sqrt(wall_center_x**2 + wall_center_y**2)
                if distance > max_render_distance:
                    continue
                brightness = max(0, 1 - distance * distance_multiplier)
                for orb_x, orb_y in orbs:
                    orb_distance = math.sqrt((orb_x - (x + 0.5))**2 + (orb_y - (y + 0.5))**2)
                    if orb_distance <= orb_illumination_radius:
                        brightness = min(1, brightness + 0.2)
                        break
                if brightness < brightness_cutoff:
                    continue
                wall_color = adjust_color_brightness(WHITE, brightness)
                corners = [
                    (x - player_x, y - player_y),
                    (x + 1 - player_x, y - player_y),
                    (x + 1 - player_x, y + 1 - player_y),
                    (x - player_x, y + 1 - player_y),
                ]
                projected_corners = []
                for cx, cy in corners:
                    rotated_x = cx * cos_angle - cy * sin_angle
                    rotated_y = cx * sin_angle + cy * cos_angle
                    screen_x = int(center_x + rotated_x * zoom)
                    screen_y = int(center_y + rotated_y * zoom)
                    projected_corners.append((screen_x, screen_y))
                if y > 0 and scene[y - 1][x] == 0:
                    display.line(projected_corners[0][0], projected_corners[0][1], projected_corners[1][0], projected_corners[1][1], wall_color)
                if x < len(scene[0]) - 1 and scene[y][x + 1] == 0:
                    display.line(projected_corners[1][0], projected_corners[1][1], projected_corners[2][0], projected_corners[2][1], wall_color)
                if y < len(scene) - 1 and scene[y + 1][x] == 0:
                    display.line(projected_corners[2][0], projected_corners[2][1], projected_corners[3][0], projected_corners[3][1], wall_color)
                if x > 0 and scene[y][x - 1] == 0:
                    display.line(projected_corners[3][0], projected_corners[3][1], projected_corners[0][0], projected_corners[0][1], wall_color)

    for orb_x, orb_y in orbs:
        rel_x = orb_x - player_x
        rel_y = orb_y - player_y
        rotated_x = rel_x * cos_angle - rel_y * sin_angle
        rotated_y = rel_x * sin_angle + rel_y * cos_angle
        screen_x = int(center_x + rotated_x * zoom)
        screen_y = int(center_y + rotated_y * zoom)
        display.pixel(screen_x, screen_y, ORB)
    display.line(61, 61, 64, 64, 0xFFFF)
    display.line(61, 67, 64, 64, 0xFFFF)
    display.line(61, 61, 62, 64, 0xFFFF)
    display.line(61, 67, 62, 64, 0xFFFF)
    orbCounter()
    rel_x = enemy_x - player_x
    rel_y = enemy_y - player_y
    rotated_x = rel_x * cos_angle - rel_y * sin_angle
    rotated_y = rel_x * sin_angle + rel_y * cos_angle
    screen_x = int(center_x + rotated_x * zoom)
    screen_y = int(center_y + rotated_y * zoom)
    display.pixel(screen_x, screen_y, RED)
    display.commit()
def BFS(grid, start, end):
    if not grid or not grid[0]:
        return []
    rows, cols = len(grid), len(grid[0])
    start_row, start_col = int(start[0]), int(start[1])
    end_row, end_col = int(end[0]), int(end[1])
    if (start_row < 0 or start_row >= rows or start_col < 0 or start_col >= cols or
        end_row < 0 or end_row >= rows or end_col < 0 or end_col >= cols or
        grid[start_row][start_col] != 0 or grid[end_row][end_col] != 0):
        return []
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    queue = [(start_row, start_col)]
    parent = [[None for _ in range(cols)] for _ in range(rows)]
    visited = [[False for _ in range(cols)] for _ in range(rows)]
    visited[start_row][start_col] = True
    while queue:
        current_row, current_col = queue.pop(0)
        if (current_row, current_col) == (end_row, end_col):
            path = []
            row, col = end_row, end_col
            while (row, col) != (start_row, start_col):
                path.append((row, col))
                row, col = parent[row][col]
            path.append((start_row, start_col))
            return path[::-1]
        for dr, dc in dirs:
            next_row, next_col = current_row + dr, current_col + dc
            if (0 <= next_row < rows and 0 <= next_col < cols and
                not visited[next_row][next_col] and grid[next_row][next_col] == 0):
                visited[next_row][next_col] = True
                parent[next_row][next_col] = (current_row, current_col)
                queue.append((next_row, next_col))
    
    return []
def enemyAI():
    global enemy_x, enemy_y, player_x, player_y
    global enemy_path, enemy_target_tile, random_target_tile
    global enemy_stun_timer, last_hit_time, player_health, recently_hurt, crack_start_time
    current_time = time.ticks_ms()
    if enemy_stun_timer > 0:
        if time.ticks_diff(current_time, last_hit_time) >= 5000:
            enemy_stun_timer = 0
        else:
            return
    current_tile = (int(enemy_y), int(enemy_x))
    player_tile = (int(player_y), int(player_x))
    distance = abs(player_tile[0] - current_tile[0]) + abs(player_tile[1] - current_tile[1])
    if abs(enemy_x - player_x) < 0.5 and abs(enemy_y - player_y) < 0.5:
        if player_health > 0:
            player_health -= 1
            recently_hurt = True
            enemy_stun_timer = 1
            crack_start_time = time.ticks_ms()
            Audio.SFX.hurt()
            print("Player hit! Health:", player_health)
            last_hit_time = current_time
        return
    if distance <= 5:
        if not enemy_path or enemy_path[-1] != player_tile:
            enemy_path = BFS(scene, current_tile, player_tile)
            if len(enemy_path) > 1:
                enemy_target_tile = enemy_path[1]
            else:
                enemy_target_tile = None
    else:
        if not random_target_tile:
            rand_row = random.randint(0, len(scene) - 1)
            rand_col = random.randint(0, len(scene[0]) - 1)
            if scene[rand_row][rand_col] == 0:
                random_target_tile = (rand_row, rand_col)
                enemy_path = BFS(scene, current_tile, random_target_tile)
                if len(enemy_path) > 1:
                    enemy_target_tile = enemy_path[1]
                else:
                    enemy_target_tile = None
    if enemy_target_tile:
        target_row, target_col = enemy_target_tile
        target_x = target_col + 0.5
        target_y = target_row + 0.5
        dx = target_x - enemy_x
        dy = target_y - enemy_y
        dist = abs(dx) + abs(dy)
        if dist < enemy_speed:
            enemy_x = target_x
            enemy_y = target_y
            current_tile = (int(enemy_y), int(enemy_x))
            if distance <= 5:
                enemy_path = BFS(scene, current_tile, player_tile)
            elif random_target_tile:
                enemy_path = BFS(scene, current_tile, random_target_tile)
            if len(enemy_path) > 1:
                enemy_target_tile = enemy_path[1]
            else:
                enemy_target_tile = None
        else:
            enemy_x += enemy_speed * (1 if dx > 0 else -1 if dx < 0 else 0)
            enemy_y += enemy_speed * (1 if dy > 0 else -1 if dy < 0 else 0)
def difficultyControl():
    global brightness_factor, brightness_decreasing, difficulty, brightness_speed, brightness_min, brightness_max
    global batteryCharges, last_brightness_reset, cooldown_progress
    current_time = time.ticks_ms()
    cooldown_time = 3000
    if difficulty == 0:
        brightness_factor = brightness_max
        brightness_decreasing = False
    elif difficulty == 1:
        brightness_decreasing = True
        if buttons.state(Buttons.A) and time.ticks_diff(current_time, last_brightness_reset) >= cooldown_time and batteryCharges > 0:
            brightness_factor = brightness_max
            batteryCharges -= 1
            last_brightness_reset = current_time 
    else:
        brightness_decreasing = True
        if buttons.state(Buttons.A) and time.ticks_diff(current_time, last_brightness_reset) >= cooldown_time:
            brightness_factor = brightness_max
            last_brightness_reset = current_time
        brightness_speed = 0.02 * difficulty
    if brightness_decreasing:
        brightness_factor -= brightness_speed
        if brightness_factor <= brightness_min:
            brightness_factor = brightness_min
    time_since_reset = time.ticks_diff(current_time, last_brightness_reset)
    cooldown_progress = min(1, time_since_reset / cooldown_time)
def batteryDraw():
    global batteryCharges, cooldown_progress
    display.rect(5, 5, 22, 9, WHITE, False)
    display.rect(27, 6, 2, 7, WHITE, True)
    for i in range(batteryCharges):
        x = 6 + i * 4
        display.rect(x + 1, 7, 2, 5, WHITE, True)
    if cooldown_progress < 1:
        cooldown_width = int((1 - cooldown_progress) * 50)
        cooldown_x = (SCREEN_WIDTH - cooldown_width) // 2
        cooldown_y = 100
        display.rect(cooldown_x, cooldown_y, cooldown_width, 2, WHITE, True)
def collectedAnim():
    global collectedR
    d = 5
    for i in range(d):
        display.rect(0+i,0+i,128-i*2,128-i*2,WHITE)
        d -= 1
    if d == 0:
        collectedR = False
        d = 5
def Reset():
    global scene, player_x, player_y, player_angle, lvl1_x, lvl1_y, enemy_x, enemy_y
    rows, cols = mapSize, mapSize
    max_room_size = 3
    num_rooms = int(mapSize * (3/5))
    scene = generate_map_with_rooms(rows, cols, max_room_size, num_rooms)
    start_x, start_y = 1, 1
    for dy in range(0, 2):
        for dx in range(0, 2):
            if 0 <= start_y + dy < len(scene) and 0 <= start_x + dx < len(scene[0]):
                scene[start_y + dy][start_x + dx] = 0
    player_x = float(start_x + 0.5)
    player_y = float(start_y + 0.5)
    player_angle = 45
    update_angle_lookup()
    place_orbs(orbsToPlace)  
    enemy_x, enemy_y = random_empty_cell(scene)
    enemy_x += 0.5
def setDif():
    global difficulty
    while True:
        display.fill(0)
        display.text(("Difficulty: "+str(difficulty)), 10, 10, WHITE)
        buttons.scan()
        if buttons.state(Buttons.Up):
            difficulty +=1
        if buttons.state(Buttons.Down):
            difficulty -=1
        if buttons.state(Buttons.A):
            return
        display.commit()
        time.sleep(0.2)
def orbCounter():
    global orbs, orbsToPlace, currentLevel
    orbsCollected = orbsToPlace-len(orbs)
    display.text(str(str(orbsCollected)+"/"+str(orbsToPlace)), 80, 2, WHITE)
    if orbsCollected == orbsToPlace:
        NextLevel()
def NextLevel():
    global currentLevel, mapSize, orbsToPlace, player_health, max_player_health, enemy_speed
    display.fill(0)
    display.commit()
    displayC.draw_rle_image_to_buffer("bkg.dat")
    displayC.draw_text(font_bytes, 45, 10, f"Lvl {currentLevel}", WHITE, None)
    displayC.draw_text(font_bytes, 31, 20, "COMPLETE", WHITE, None)
    displayC.draw_text(font_bytes, 30, 70, "Press A",WHITE, None)
    displayC.draw_text(font_bytes, 30, 80, "to continue", WHITE, None)    
    displayC.refresh()
    Audio.SFX.new_level()
    time.sleep(1)
    mapSize += 2
    orbsToPlace += 1
    player_health += 1
    enemy_speed += 0.005
    if player_health > max_player_health:
        player_health = max_player_health
    while True:
        buttons.scan()
        if buttons.state(Buttons.A):
            currentLevel += 1
            Reset()
            break
def LoadingScreen():
    display.fill(0)
    display.commit()
    time.sleep(1)
    try:
        print("D")
    except:
        print("Error: Failed to draw itstalksbw image.")
    displayC.rect(15, 104, 98, 12, WHITE)
    displayC.refresh()
    try:
        displayC.draw_rle_image_store("button", BUTTON_DATA_RLE, BUTTON_PALETTE, BUTTON_WIDTH, BUTTON_HEIGHT)
    except:
        print("Error: Failed to load button image.")
    time.sleep(0.5)
    displayC.rectF(17, 106, 22, 8, WHITE)
    displayC.refresh()
    try:
        displayC.draw_rle_image_store("button_100", BUTTON_100_DATA_RLE, BUTTON_100_PALETTE, BUTTON_100_WIDTH, BUTTON_100_HEIGHT)
    except:
        print("Error: Failed to load button_100 image.")
    time.sleep(0.5)
    displayC.rectF(17, 106, 44, 8, WHITE)
    displayC.refresh()
    try:
        displayC.draw_rle_image_store("gumb_15", GUMB_15_DATA_RLE, GUMB_15_PALETTE, GUMB_15_WIDTH, GUMB_15_HEIGHT)
    except:
        print("Error: Failed to load gumb_15 image.")
    time.sleep(0.5)
    displayC.rectF(17, 106, 66, 8, WHITE)
    displayC.refresh()
    try:
        displayC.draw_rle_image_store("gumb_15_u", GUMB_15_U_DATA_RLE, GUMB_15_U_PALETTE, GUMB_15_U_WIDTH, GUMB_15_U_HEIGHT)
    except:
        print("Error: Failed to load gumb_15_u image.")
    time.sleep(0.5)
    displayC.rectF(17, 106, 94, 8, WHITE)
    displayC.refresh()
    time.sleep(0.5)
    for i in range(64):
        display.line(0, i, 128, i, WHITE)
        display.line(0, 127-i, 128, 127-i, WHITE)
        display.commit()
    display.fill(0)
    displayC.refresh()
    display.commit()
sfx_active = False
class Audio:
    class SFX:
        @staticmethod
        def orbPickup():
            def play_orb():
                ms = 100
                p = random.randint(0, 2)
                if p == 0:
                    piezo.tone(1760, ms)
                elif p == 1:
                    piezo.tone(185, ms)
                    piezo.tone(220, ms)
                elif p == 2:
                    piezo.tone(831, ms)
                    piezo.tone(784, ms)
            if sfxToggle:
                _thread.start_new_thread(play_orb, ())
        @staticmethod
        def interact():
            def play_interact():
                ms = 50
                piezo.tone(20, ms)
            if sfxToggle:
                _thread.start_new_thread(play_interact, ())
        @staticmethod
        def error(severity):
            global sfx_active
            if sfx_active or not sfxToggle:
                return
            sfx_active = True
            if severity == 0:
                piezo.tone(220, 100)
                piezo.tone(110, 100)
            elif severity == 1:
                piezo.tone(62, 500)
                piezo.tone(58, 500)
                piezo.tone(55, 500)
            sfx_active = False
        @staticmethod
        def new_level():
            def play_new_level():
                ms = 200
                piezo.tone(523, ms)
                piezo.tone(587, ms)
                piezo.tone(659, ms)
                piezo.tone(698, ms)
            if sfxToggle:
                _thread.start_new_thread(play_new_level(), ())   
        @staticmethod
        def hurt():
            def play_hurt():
                ms = 100
                piezo.tone(55, ms)
                piezo.tone(220, ms)
                piezo.tone(110, ms)
            if sfxToggle:
                _thread.start_new_thread(play_hurt(), ())
sfxToggle = True
musicToggle = True

def zfill(s, width):
    return ('0' * (width - len(s))) + s
menu_hierarchy = {
    0: {"name": "Main Menu", "submenus": [1, 3, 13]},
    1: {"name": "Solo Menu", "submenus": [12, 11]},
    2: {"name": "Multiplayer Menu", "submenus": [4, 5]},
    3: {"name": "Settings Menu", "submenus": [6, 7]},
    4: {"name": "Host Menu", "submenus": [10]},
    5: {"name": "Connect Menu", "submenus": [10]},
    6: {"name": "Graphics Menu", "submenus": [8, 9]},
    7: {"name": "Sound Menu", "submenus": []},
    8: {"name": "Ray Count Menu", "submenus": []},
    9: {"name": "FOV Menu", "submenus": []},
    10: {"name": "Lobby Menu", "submenus": []},
    11: {"name": "Difficulty Menu", "submenus": []},
    12: {"name": "Starting Menu", "submenus": []},
    13: {"name": "Credits Menu", "submenus": []},
}
last_menu = None
current_menu = 0
selectedButton = 0
def maybe_draw_background():
    global last_menu, current_menu
    if current_menu != last_menu:
        displayC.draw_rle_image_to_buffer("bkg.dat")
        last_menu = current_menu
def buttonScroll(lista):
    global selectedButton, current_menu
    if current_menu != 0:
        buttons.scan()
        if buttons.state(Buttons.A):
            if selectedButton == len(lista) - 1:
                current_menu = 0
                selectedButton = 0
            else:
                submenus = menu_hierarchy[current_menu]["submenus"]
                if selectedButton < len(submenus):
                    current_menu = submenus[selectedButton]
                    selectedButton = 0
            Audio.SFX.interact()
        if buttons.state(Buttons.Up):
            selectedButton -= 1
            Audio.SFX.interact()
        if buttons.state(Buttons.Down):
            selectedButton += 1
            Audio.SFX.interact()
        if selectedButton < 0:
            selectedButton = len(lista) - 1
        if selectedButton >= len(lista):
            selectedButton = 0
        time.sleep(0.1)
    else:
        buttons.scan()
        if buttons.state(Buttons.A):
            submenus = menu_hierarchy[current_menu]["submenus"]
            if selectedButton < len(submenus):
                current_menu = submenus[selectedButton]
                selectedButton = 0
            Audio.SFX.interact()
        if buttons.state(Buttons.Up):
            selectedButton -= 1
            Audio.SFX.interact()
        if buttons.state(Buttons.Down):
            selectedButton += 1
            Audio.SFX.interact()
        if selectedButton < 0:
            selectedButton = len(lista) - 1
        if selectedButton >= len(lista):
            selectedButton = 0       
        time.sleep(0.1)
def buttonSpace(buttonList):
    global selectedButton
    totalButtonHeight = len(buttonList) * BUTTON_HEIGHT
    spacing = (SCREEN_HEIGHT - totalButtonHeight) // (len(buttonList) + 1)
    for index in range(len(buttonList)):
        yButton = (spacing + BUTTON_100_HEIGHT) * index + spacing
        xButton = (SCREEN_WIDTH - BUTTON_100_WIDTH) // 2
        yText = yButton + (BUTTON_100_HEIGHT // 4) + 1
        xText = xButton + 2
        displayC.draw_frame_to_buffer("button_100", xButton, yButton, BUTTON_100_WIDTH, BUTTON_100_HEIGHT)
        if index == selectedButton:
            displayC.rect(xButton, yButton, BUTTON_100_WIDTH, BUTTON_100_HEIGHT, WHITE)
        displayC.draw_text(font_bytes, xText, yText, buttonList[index], WHITE, None)
def buttonSpaceToggles(buttonList, tg1, tg2):
    global selectedButton
    totalButtonHeight = len(buttonList) * BUTTON_HEIGHT
    spacing = (SCREEN_HEIGHT - totalButtonHeight) // (len(buttonList) + 1)
    for index in range(len(buttonList)):
        yButton = (spacing + BUTTON_HEIGHT) * index + spacing
        xButton = (SCREEN_WIDTH - BUTTON_WIDTH) // 2
        yText = yButton + (BUTTON_HEIGHT // 4) + 1
        xText = xButton + 2
        displayC.draw_frame_to_buffer("button", xButton, yButton, BUTTON_WIDTH, BUTTON_HEIGHT)
        if index == selectedButton:
            displayC.rect(xButton, yButton, BUTTON_WIDTH, BUTTON_HEIGHT, WHITE)
        displayC.draw_text(font_bytes, xText, yText, buttonList[index], WHITE, None)
        if index == 0:
            if tg1:
                displayC.draw_frame_to_buffer("gumb_15", xButton + BUTTON_WIDTH + 5, yButton, GUMB_15_WIDTH, GUMB_15_HEIGHT)
            else:
                displayC.draw_frame_to_buffer("gumb_15_u", xButton + BUTTON_WIDTH + 5, yButton, GUMB_15_U_WIDTH, GUMB_15_U_HEIGHT)
        if index == 1:
            if tg2:
                displayC.draw_frame_to_buffer("gumb_15", xButton + BUTTON_WIDTH + 5, yButton, GUMB_15_WIDTH, GUMB_15_HEIGHT)
            else:
                displayC.draw_frame_to_buffer("gumb_15_u", xButton + BUTTON_WIDTH + 5, yButton, GUMB_15_U_WIDTH, GUMB_15_U_HEIGHT)
def main_menu():
    global selectedButton
    maybe_draw_background()
    buttonSpace(["Solo", "Settings", "Credits"])
    buttonScroll(["Solo", "Settings", "Credits"])
def solo_menu():
    global selectedButton
    maybe_draw_background()
    displayC.draw_text(font_bytes, (SCREEN_WIDTH // 2) - 14, 10, "SOLO", WHITE, None)
    buttonSpace(["Start", "Back"])
    buttonScroll(["Start", "Back"])
def starting_menu():
    global running
    maybe_draw_background()
    displayC.draw_text(font_bytes, 10, 10, "STARTING", WHITE, None)
    displayC.draw_text(font_bytes, 10, 20, "IN", WHITE, None)
    for i in range(3, 0, -1):
        y_pos = 30 + (3 - i) * 10
        displayC.draw_text(font_bytes, 10, y_pos, str(i), WHITE, None)
        displayC.refresh()
        time.sleep(1)
    displayC.draw_text(font_bytes, 10, y_pos + 10, "GO!", WHITE, None)
    displayC.refresh()
    time.sleep(1)
    running = True
def settings_menu():
    global selectedButton
    maybe_draw_background()
    buttonSpace(["Graphics", "Sound", "Back"])
    buttonScroll(["Graphics", "Sound", "Back"])
def sound_menu():
    global selectedButton, sfxToggle, musicToggle, needs_redraw
    maybe_draw_background()
    if selectedButton == 0 and buttons.state(Buttons.A):
        sfxToggle = not sfxToggle
        needs_redraw = True
        time.sleep(0.2)
    if selectedButton == 1 and buttons.state(Buttons.A):
        musicToggle = not musicToggle
        needs_redraw = True
        time.sleep(0.2)
    buttonSpaceToggles(["Sfx", "", "Back"], sfxToggle, musicToggle)
    buttonScroll(["Sfx", "", "Back"])
def graphics_menu():
    global selectedButton
    maybe_draw_background()
    buttonSpace(["Max distance", "FOV", "Back"])
    buttonScroll(["Max distance", "FOV", "Back"])
def credits_menu():
    global selectedButton, current_menu
    buttons.scan()
    maybe_draw_background()
    display.text("< B", 5, 5, WHITE)
    displayC.draw_text(font_bytes, 10, 20, "CODE", WHITE, None)
    displayC.draw_text(font_bytes, 10, 50, "You can find the code", WHITE, None)
    displayC.draw_text(font_bytes, 10, 60, "for the game at", WHITE, None)
    displayC.draw_text(font_bytes, 10, 70, "github.com", WHITE, None)
    displayC.draw_text(font_bytes, 10, 80, "/ROTIN37", WHITE, None)
    displayC.draw_text(font_bytes, 10, 90, "/NewBit", WHITE, None)
    if buttons.state(Buttons.B):
        time.sleep(0.2)
        current_menu = 0
        selectedButton = 0
        Audio.SFX.interact()
        return
    display.commit()
def ray_menu():
    global MAX_DEPTH, raySel, current_menu, selectedButton
    maybe_draw_background()
    possibleRays = [2,3,4,5,6,7,8]
    MAX_DEPTH = possibleRays[raySel]
    buttons.scan()
    display.text("< B", 5, 5, WHITE)
    displayC.rectF(20, 20, 88, 88, 0x39C7)
    displayC.rect(20, 20, 88, 88, 0x94B2)
    if buttons.state(Buttons.Left):
        raySel -= 1
        if raySel < 0:
            raySel = len(possibleRays) - 1
        Audio.SFX.interact()
        time.sleep(0.2)
    if buttons.state(Buttons.Right):
        raySel += 1
        if raySel >= len(possibleRays):
            raySel = 0
        Audio.SFX.interact()
        time.sleep(0.2)
    if buttons.state(Buttons.B):
        current_menu = 6
        selectedButton = 0
        Audio.SFX.interact()
        return
    text = "Max distance"
    text_width = (len(text) * 6) + ((len(text) - 1) * 2)
    x_text = (SCREEN_WIDTH - text_width) // 2
    display.text(text, x_text, 32, WHITE)
    ray_value = f"< {possibleRays[raySel]} >"
    ray_value_width = (len(ray_value) * 6) + ((len(ray_value) - 1) * 2)
    x_ray_value = (SCREEN_WIDTH - ray_value_width) // 2
    display.text(ray_value, x_ray_value, 64, WHITE)
    display.commit()
def fov_menu():
    global current_menu, selectedButton, current_fov_index, n, FOV, HALF_FOV
    FOV_OPTIONS = [1, 2, 3, 4, 5]
    FOV_DEGREES = [180, 90, 60, 45, 36]
    maybe_draw_background()
    n = FOV_OPTIONS[current_fov_index]
    FOV = math.pi / n
    HALF_FOV = FOV / 2
    FOVn = FOV_DEGREES[current_fov_index]
    displayC.rectF(32, 24, 64, 64, 0x39C7)
    displayC.rect(32, 24, 64, 64, 0x94B2)
    display.text("< B", 5, 5, WHITE)
    text = "FOV"
    text_width = (len(text) * 6) + ((len(text) - 1) * 2)
    x_text = (SCREEN_WIDTH - text_width) // 2
    displayC.draw_text(font_bytes, x_text, 32, text, WHITE, None)
    fov_value = f"< {FOVn} >"
    fov_value_width = (len(fov_value) * 6) + ((len(fov_value) - 1) * 2)
    x_fov_value = (SCREEN_WIDTH - fov_value_width) // 2
    display.text(fov_value, x_fov_value, 64, WHITE)
    buttons.scan()
    if buttons.state(Buttons.Left):
        current_fov_index += 1
        if current_fov_index >= len(FOV_OPTIONS):
            current_fov_index = 0
        Audio.SFX.interact()
        time.sleep(0.2)
    if buttons.state(Buttons.Right):
        current_fov_index -= 1
        if current_fov_index < 0:
            current_fov_index = len(FOV_OPTIONS) - 1
        Audio.SFX.interact()
        time.sleep(0.2)
    if buttons.state(Buttons.B):
        current_menu = 6  # Back to Graphics menu
        selectedButton = 0
        Audio.SFX.interact()
        return
    display.commit()
menus = {
    0: main_menu,
    1: solo_menu,
    3: settings_menu,
    6: graphics_menu,
    7: sound_menu,
    8: ray_menu,
    9: fov_menu,
    12: starting_menu,
    13: credits_menu,
}
def menu_controll():
    global selectedButton, current_menu
    buttons.scan()
    if buttons.state(Buttons.Up):
        selectedButton -= 1
    if buttons.state(Buttons.Down):
        selectedButton += 1
    if selectedButton < 0:
        selectedButton = len(["Solo", "Multiplayer", "Settings"]) - 1
    if selectedButton >= len(["Solo", "Multiplayer", "Settings"]):
        selectedButton = 0
    if buttons.state(Buttons.A):
        if current_menu == 0:
            submenus = menu_hierarchy[current_menu]["submenus"]
            if selectedButton < len(submenus):
                current_menu = submenus[selectedButton]
                selectedButton = 0
    time.sleep(0.2)
needs_redraw = True
running = False
while running == False:
    buttons.scan()
    old_selected = selectedButton
    old_menu = current_menu
    menus[current_menu]()
    if old_selected != selectedButton or old_menu != current_menu:
        needs_redraw = True
    if needs_redraw:
        menus[current_menu]()
        displayC.refresh()
        needs_redraw = False
    time.sleep(0.01)
def ResetGame():
    global currentLevel, mapSize, orbsToPlace, player_health, max_player_health, batteryCharges, enemy_speed
    currentLevel = 0
    mapSize = 11
    orbsToPlace = 5
    player_health = 3
    max_player_health = 3
    batteryCharges = 5
    enemy_speed = 0.025
    Reset()
    displayC.refresh()
def Game_Over():
    displayC.draw_text(font_bytes, 10, 50, "GAME OVER", WHITE, None)
    displayC.draw_text(font_bytes, 10, 60, "Press A to reset", WHITE, None)
    displayC.draw_text(font_bytes, 10, 70, "Press B to exit", WHITE, None)
    display.commit()
    while True:
        buttons.scan()
        if buttons.state(Buttons.A):
            ResetGame()
            break
        if buttons.state(Buttons.B):
            TerminateExecution()
            break
crack_start_time = 0
current_crack = None
def generate_radial_crack(center=None, num_branches=8, segments_per_branch=3, spread=25):
    if center is None:
        center = (random.randint(30, SCREEN_WIDTH - 30), random.randint(30, SCREEN_HEIGHT - 30))
    branches = []
    angle_step = 360 // num_branches
    cx, cy = center
    for i in range(num_branches):
        angle_deg = i * angle_step + random.randint(-10, 10)
        angle_rad = math.radians(angle_deg)
        points = [(cx, cy)]
        x, y = cx, cy
        for _ in range(segments_per_branch):
            dx = math.cos(angle_rad) * random.randint(spread - 10, spread + 10)
            dy = math.sin(angle_rad) * random.randint(spread - 10, spread + 10)
            x += dx
            y += dy
            x = max(0, min(SCREEN_WIDTH, int(x)))
            y = max(0, min(SCREEN_HEIGHT, int(y)))
            points.append((x, y))
        branches.append(points)
    return branches
def draw_crack():
    global crack_start_time, current_crack, recently_hurt
    now = time.ticks_ms()
    if current_crack is None or time.ticks_diff(now, crack_start_time) > 2000:
        current_crack = generate_radial_crack()
        crack_start_time = now
        recently_hurt = False
    for branch in current_crack:
        for i in range(len(branch) - 1):
            x1, y1 = branch[i]
            x2, y2 = branch[i + 1]
            display.line(x1, y1, x2, y2, RED)

gc.collect()
print(gc.mem_free())
currentLevel = 0
difficulty = 1
Reset()
map_open = False
exceptionCounter = 0
base_move_speed = move_speed
base_rot_speed = rot_speed
frame_count = 0
start_time = time.ticks_ms()
MAX_FPS = 30
FRAME_DURATION_MS = int(1000 / MAX_FPS)
pbE = False
while running:
    frame_start = time.ticks_ms()
    try:
        buttons.scan()
        if buttons.state(Buttons.B):
            map_open = not map_open
            time.sleep_ms(200)
        handle_input()
        enemyAI()
        if map_open:
            move_speed = base_move_speed / 4
            rot_speed = base_rot_speed / 4
            mapRender(display)
        else:
            move_speed = base_move_speed
            rot_speed = base_rot_speed
            render(display)
            difficultyControl()
        frame_end = time.ticks_ms()
        frame_time = time.ticks_diff(frame_end, frame_start)
        if frame_time < FRAME_DURATION_MS:
            time.sleep_ms(FRAME_DURATION_MS - frame_time)
        frame_count += 1
        current_time = time.ticks_ms()
        elapsed_time = time.ticks_diff(current_time, start_time) / 1000
        if elapsed_time >= 1.0:
            fps = frame_count / elapsed_time
            print("FPS: {:.1f}".format(fps))
            frame_count = 0
            start_time = current_time
        if player_health==0:
            Game_Over()
            Reset()

    except Exception as e:
        exceptionCounter += 1
        Audio.SFX.error(0)
        if exceptionCounter > 5:
            display.fill(0x0000)
            display.commit()
            time.sleep(1)
            if pbE != True:
                Audio.SFX.error(1)
                pbE = True
            display.fill(0xF800)
            display.text("Critical Error", 0, 0, WHITE)
            display.text("Program failed...", 0, 10, WHITE)
            display.text("Error:", 0, 20, WHITE)
            display.text(str(e), 0, 30, WHITE)
            display.text("Press B to reset", 0, 50, WHITE)
            display.text("Press A to stop", 0, 60, WHITE)
            display.commit()
            while True:
                buttons.scan()
                if buttons.state(Buttons.B):
                    wdt = WDT(timeout=200)
                    time.sleep(0.3)
                if buttons.state(Buttons.A):
                    TerminateExecution()
                    break
