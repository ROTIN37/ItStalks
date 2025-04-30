import gc
from machine import Pin, SPI, WDT, freq
import time
import math
import random
import sys
import _thread

from Bit import display  # Or however you get the display instance

WORLD_BUFFER = display.buffer  # Same as WORLD_BUFFER


from Bit import *
begin()
print("Begun")

time.sleep(0)

n = 2
raySel = 4
FOV = math.pi / n 
current_fov_index = 1

SCREEN_WIDTH = 128
SCREEN_HEIGHT = 128
FOV = math.pi / n  # 90 degrees (wider FOV)
HALF_FOV = FOV / 2
NUM_RAYS = SCREEN_WIDTH
MAX_DEPTH = 6

FOVn = 100


c = 0

freq(240000000)  # Set CPU frequency to 240MHz

# Colors
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
enemy_stun_timer = 0  # seconds
last_hit_time = 0     # timestamp when enemy last hit player


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

# Player position and angle
player_x, player_y = 2, 2
player_angle = 90

enemy_x, enemy_y = 2, 2


lvl1_x, lvl1_y = 14, 18

mapSize = 11 # MUST BE ODD NUMBER


brightness_factor = 1.0  # Default brightness
brightness_decreasing = True  
brightness_min = 0.25  # Minimum brightness
brightness_max = 1.0
brightness_speed = 0.025  # Speed for brightness change


# Precompute angle lookup tables
angle_step = FOV / NUM_RAYS
angle_lookup = [player_angle - HALF_FOV + i * angle_step for i in range(NUM_RAYS)]
cos_lookup = [math.cos(angle) for angle in angle_lookup]
sin_lookup = [math.sin(angle) for angle in angle_lookup]
collectedR = False


CENTER_X = 64  # Center of the display (assuming 128x128 display)
CENTER_Y = 12
RHOMBUS_WIDTH = 5  # Horizontal size of the rhombus
RHOMBUS_HEIGHT = 10  # Vertical size of the rhombus (makes it more needle-like)



# Example multiplayer data, replace with actual JSON loading, rendering implemented but no time for networking 
# Sooo myby in the future, if I ever get to it, I will implement it
multiplayer_players = [

]





# Scene (0 = empty, 1 = wall, 2 = exit(NOT USED),10 = window(HELLA LAGGY))
scene = [ ]
print("Set world buffer")
# Orb positions (x, y) in world coordinates
orbs = [ ]

# ========= ST7735 RGB565 Buffered Driver for CircuitMess Bit =========
class ST7735:
    def __init__(self, spi, dc, rst, bl, width=128, height=128):
        self.spi = spi
        self.dc = dc
        self.rst = rst
        self.width = width
        self.height = height
        self.bl = bl
        self.frames = {}  # Store frames by key/name

        # Initialize the world buffer
        print("\nInitializing ST7735 display...")
        print("Clearing memory, for resource allocation...")
        gc.collect()  # Run garbage collection to free up unused memory
        print("Free memory:", gc.mem_free())
        global WORLD_BUFFER
        self.WORLD_BUFFER = WORLD_BUFFER # 2 bytes per pixel for RGB565
        
        # Font configuration
        self.FONT_WIDTH = 6
        self.FONT_HEIGHT = 8
        self.CHAR_SPACING = 1
        
        # Initialize pins
        self.dc.init(Pin.OUT, value=0)
        self.bl.init(Pin.OUT, value=0)  # Set LOW to turn ON for PNP transistor
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
        self.write_cmd(0x01)  # Software reset
        time.sleep_ms(150)

        self.write_cmd(0x11)  # Sleep out
        time.sleep_ms(150)

        self.write_cmd(0x3A)  # Color mode
        self.write_data(0x05)  # 16-bit RGB565
        time.sleep_ms(10)

        self.write_cmd(0x36)  # MADCTL
        self.write_data(0xC8)

        self.write_cmd(0x2A)  # Column address set
        self.write_data(bytearray([0x00, 0x00, 0x00, self.width - 1]))

        self.write_cmd(0x2B)  # Row address set
        self.write_data(bytearray([0x00, 0x00, 0x00, self.height - 1]))

        self.write_cmd(0x29)  # Display on
        time.sleep_ms(100)

        self.backlight(True)
        
        # Clear the buffer and display
        self.clear(0x0000)
        self.refresh()

    def backlight(self, on):
        self.bl.value(not on)  # LOW = ON for PNP

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
        """Calculate the buffer address for a given pixel"""
        return (x + y * self.width) * 2

    def pixel(self, x, y, color):
        """Draw a pixel to the buffer"""
        if 0 <= x < self.width and 0 <= y < self.height:
            addr = self.buffer_address(x, y)
            high, low = self.colorCalc(color)
            self.WORLD_BUFFER[addr] = high
            self.WORLD_BUFFER[addr + 1] = low

    def clear(self, color=0x0000):
        """Clear the buffer with a single color"""
        high, low = self.colorCalc(color)
        for i in range(0, len(self.WORLD_BUFFER), 2):
            self.WORLD_BUFFER[i] = high
            self.WORLD_BUFFER[i + 1] = low

    def refresh(self):
        """Push the entire buffer to the display"""
        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.dc.value(1)
        self.spi.write(self.WORLD_BUFFER)

    def refresh_area(self, x, y, w, h):
        """Refresh only a portion of the screen"""
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
            
        temp_buffer = bytearray(w * 2)
        self.set_window(x, y, x + w - 1, y + h - 1)
        self.dc.value(1)
        
        for row in range(h):
            start_addr = self.buffer_address(x, y + row)
            for col in range(w):
                temp_buffer[col*2] = self.WORLD_BUFFER[start_addr + col*2]
                temp_buffer[col*2 + 1] = self.WORLD_BUFFER[start_addr + col*2 + 1]
            self.spi.write(temp_buffer)

    def line(self, x0, y0, x1, y1, color):
        """Draw a line directly to the buffer using Bresenham's algorithm"""
        # Bounds checking
        x0 = max(0, min(self.width - 1, x0))
        y0 = max(0, min(self.height - 1, y0))
        x1 = max(0, min(self.width - 1, x1))
        y1 = max(0, min(self.height - 1, y1))
        
        # Convert color once instead of repeatedly
        high, low = self.colorCalc(color)
        
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        
        while True:
            # Direct buffer access
            addr = (x0 + y0 * self.width) * 2
            self.WORLD_BUFFER[addr] = high
            self.WORLD_BUFFER[addr + 1] = low
            
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                if x0 == x1:
                    break
                err += dy
                x0 += sx
            if e2 <= dx:
                if y0 == y1:
                    break
                err += dx
                y0 += sy


    def rect(self, x, y, w, h, color):
        """Draw a rectangular outline directly to the buffer"""
        # Bounds checking and adjustment
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
            
        # Convert color once
        high, low = self.colorCalc(color)
        
        # Top and bottom horizontal lines
        for i in range(w):
            # Top line
            addr_top = ((x + i) + y * self.width) * 2
            self.WORLD_BUFFER[addr_top] = high
            self.WORLD_BUFFER[addr_top + 1] = low
            
            # Bottom line
            addr_bottom = ((x + i) + (y + h - 1) * self.width) * 2
            self.WORLD_BUFFER[addr_bottom] = high
            self.WORLD_BUFFER[addr_bottom + 1] = low
        
        # Left and right vertical lines
        for i in range(h):
            # Left line
            addr_left = (x + (y + i) * self.width) * 2
            self.WORLD_BUFFER[addr_left] = high
            self.WORLD_BUFFER[addr_left + 1] = low
            
            # Right line
            addr_right = ((x + w - 1) + (y + i) * self.width) * 2
            self.WORLD_BUFFER[addr_right] = high
            self.WORLD_BUFFER[addr_right + 1] = low

    def rectF(self, x, y, w, h, color):
        """Draw a filled rectangle directly to the buffer - optimized"""
        # Bounds checking and adjustment
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
        
        # Optimize for larger blocks by creating a row pattern once
        row_pattern = bytearray(w * 2)
        for i in range(0, w * 2, 2):
            row_pattern[i] = high
            row_pattern[i + 1] = low
        
        # Apply the pattern to each row
        for y_pos in range(y, y + h):
            start_addr = (x + y_pos * self.width) * 2
            for i in range(len(row_pattern)):
                self.WORLD_BUFFER[start_addr + i] = row_pattern[i]

    def draw_rle_image_to_buffer(self, rle_data, palette, width, height, start_x=0, start_y=0):
        """Decode RLE image directly to the world buffer"""
        x = 0
        y = 0
        i = 0

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
                    px, py = start_x + x, start_y + y
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
    # draw_rle_image_store("button", BUTTON_DATA_RLE, BUTTON_PALLETE, BUTTON_WIDTH, BUTTON_HEIGHT)
    def draw_rle_image_store(self, name, rle_data, palette, width, height):
        """Decode and store RLE image into self.frames[name]"""
        total_pixels = width * height
        frame = bytearray(total_pixels * 2)
        print("Allocating frame memory of size:", total_pixels * 2, " bytes.")
        print("Free memory after allocation:", gc.mem_free())

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
        """Draw a stored frame to the world buffer"""
        if frame_name not in self.frames:
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
        """Convert a character to its index in the font array"""
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
        else: return -1  # Character not found

    def draw_char(self, font_bytes, x, y, char, color, bg_color=None):
        """Draw a single character from the font to the buffer"""
        char_index = self.get_char_index(char)
        if char_index < 0:
            return self.FONT_WIDTH  # Skip unknown characters but preserve spacing
            
        bytes_per_char = self.FONT_WIDTH  # Each character is 6 bytes in your format
        start_byte = char_index * bytes_per_char
        
        if start_byte + bytes_per_char > len(font_bytes):
            return self.FONT_WIDTH
            
        for dy in range(self.FONT_HEIGHT):
            for dx in range(self.FONT_WIDTH):
                byte_offset = start_byte + dx
                if byte_offset < len(font_bytes):
                    # Check if the bit at position dy is set
                    bit_is_set = (font_bytes[byte_offset] & (1 << dy)) != 0
                    
                    px, py = x + dx, y + dy
                    if 0 <= px < self.width and 0 <= py < self.height:
                        if bit_is_set:
                            self.pixel(px, py, color)
                        elif bg_color is not None:  # Draw background only if specified
                            self.pixel(px, py, bg_color)
        
        return self.FONT_WIDTH + self.CHAR_SPACING

    def draw_text(self, font_bytes, x, y, text, color, bg_color=None):
        """Draw text string to the buffer using the provided font"""
        cursor_x = x
        
        for char in str(text):  # Ensure text is a string
            if char == ' ':
                cursor_x += self.FONT_WIDTH
                continue
                
            char_width = self.draw_char(font_bytes, cursor_x, y, char, color, bg_color)
            cursor_x += char_width
            
            if cursor_x >= self.width:
                break
                
        return cursor_x - x  # Return the total width of the drawn text

    def fill(self, color):
        """Fill the entire buffer with one color - an alias for clear()"""
        self.clear(color)

    def draw_precompiled_rle(self, start_x, start_y, width, height, frame):
        """Draw directly from a stored frame (non-buffered)"""
        self.set_window(start_x, start_y, start_x + width - 1, start_y + height - 1)
        self.dc.value(1)
        self.spi.write(frame)

    def draw_frame_by_name(self, name, x, y, width, height):
        """Convenience: draw a stored frame by name"""
        if name in self.frames:
            self.draw_precompiled_rle(x, y, width, height, self.frames[name])




# SPI and pin config (verified from schematic)
spi = SPI(1, baudrate=240000000, polarity=0, phase=0, sck=Pin(13), mosi=Pin(14))  # Adjust baudrate if needed
dc = Pin(15, Pin.OUT)
rst = Pin(16, Pin.OUT)
bl = Pin(12, Pin.OUT)  # Backlight pin

# Initialize display
displayC = ST7735(spi, dc, rst, bl)


# Gray Wall Background
IMAGE_WIDTH = 128
IMAGE_HEIGHT = 128
PALETTE = [21130,27469,19110,16936,33872,23302,14823,29581,0]
# RLE format: [count1, value1, count2, value2, ...]
IMAGE_DATA_RLE = bytearray([5,6,5,0,7,2,2,5,3,2,10,4,9,5,4,2,6,5,13,2,10,3,7,4,5,5,8,4,13,5,14,4,4,3,8,6,5,0,4,2,2,5,7,2,9,4,9,5,4,2,2,4,5,5,13,2,3,4,6,3,6,4,6,5,8,4,1,5,3,0,8,5,2,0,15,4,3,3,5,6,3,4,6,0,2,2,2,5,7,2,10,4,7,5,4,2,4,4,5,5,11,2,4,4,2,3,5,0,4,4,6,5,9,4,6,0,5,5,3,0,12,4,4,1,4,3,2,6,5,4,1,1,2,0,3,1,8,2,2,1,1,7,5,4,3,1,1,0,7,5,2,2,6,4,5,5,9,2,5,4,2,1,7,0,2,4,2,1,5,5,3,4,4,1,8,0,2,5,6,0,2,1,8,4,7,1,3,3,2,6,5,4,8,1,2,2,6,1,1,7,5,4,3,1,2,0,5,5,9,4,1,0,4,5,8,2,5,4,3,1,7,0,5,1,3,5,4,4,5,1,15,0,4,1,1,7,4,4,8,1,3,3,7,4,16,1,5,7,4,1,2,0,5,5,8,4,4,0,9,2,5,4,5,1,6,0,7,1,4,4,6,1,13,0,6,1,3,7,7,1,2,0,4,3,7,4,16,1,5,7,4,1,3,0,3,5,8,4,5,0,9,2,4,4,8,1,2,0,9,1,4,4,6,1,11,0,8,1,3,7,6,1,3,0,4,3,4,4,31,1,3,3,8,4,5,0,9,2,3,4,17,1,3,7,1,1,2,4,9,1,4,0,20,1,6,0,3,3,4,4,9,1,1,0,21,1,3,3,6,4,7,0,10,2,19,1,3,7,12,1,4,0,18,1,6,0,5,3,3,4,9,1,3,0,20,1,4,3,5,4,7,0,10,2,19,1,3,7,13,1,2,0,18,1,7,0,5,3,3,4,8,1,5,0,19,1,4,3,5,4,1,1,6,0,10,2,19,1,3,7,32,1,8,0,3,3,2,5,2,4,9,1,5,0,19,1,4,3,2,4,2,2,1,4,3,1,4,0,9,2,13,1,5,0,2,1,3,7,32,1,7,0,3,3,3,5,2,4,9,1,8,0,14,1,2,0,4,3,5,2,4,1,3,0,8,2,11,1,10,0,30,1,11,0,4,3,3,5,2,4,10,1,10,0,7,1,6,0,3,3,7,2,3,1,3,0,6,2,11,1,12,0,28,1,13,0,3,3,4,5,2,4,12,1,21,0,2,3,8,2,3,1,3,0,5,2,11,1,12,0,29,1,13,0,2,3,5,5,2,4,6,1,3,0,8,1,15,0,11,2,4,1,1,0,6,2,11,1,9,0,34,1,11,0,3,3,4,5,3,4,5,1,4,0,11,1,11,0,9,2,7,1,6,2,9,1,8,0,16,1,6,0,17,1,7,0,9,3,1,0,2,4,6,1,4,0,11,1,10,0,9,2,7,1,6,2,8,1,6,0,16,1,11,0,16,1,6,0,9,3,2,0,1,4,8,1,4,0,12,1,7,0,9,2,8,1,5,2,7,1,5,0,15,1,16,0,15,1,5,0,8,3,1,2,3,0,9,1,4,0,16,1,3,0,6,2,3,5,7,1,5,2,7,1,3,0,16,1,6,0,8,1,3,0,16,1,6,0,6,3,1,2,4,0,9,1,4,0,16,1,1,0,6,2,4,5,6,1,6,2,18,1,2,0,6,1,3,0,11,1,4,0,17,1,6,0,3,3,2,2,5,0,9,1,3,0,16,1,1,0,5,2,5,5,7,1,5,2,16,1,5,0,20,1,3,0,17,1,7,0,6,2,3,0,9,1,3,0,15,1,3,0,4,2,6,5,6,1,5,2,15,1,7,0,37,1,7,0,3,3,6,2,3,0,17,1,5,3,7,0,1,3,2,2,1,3,6,5,4,1,2,0,2,1,3,2,13,1,10,0,32,1,11,0,5,3,4,2,5,0,13,1,2,0,5,3,7,0,4,3,1,4,2,5,2,4,7,0,16,1,12,0,11,1,3,0,14,1,15,0,6,3,3,2,7,0,9,1,4,0,4,3,8,0,3,3,6,4,6,0,16,1,14,0,8,1,6,0,11,1,18,0,5,3,2,2,2,1,8,0,7,1,5,0,3,3,8,0,2,3,7,4,4,0,17,1,15,0,8,1,7,0,9,1,16,0,3,1,5,3,2,2,4,1,6,0,7,1,6,0,1,3,9,0,2,3,6,4,5,0,16,1,16,0,7,1,9,0,7,1,16,0,5,1,4,3,2,2,5,1,6,0,3,1,19,0,2,3,6,4,4,0,14,1,21,0,3,1,12,0,5,1,16,0,7,1,3,3,1,2,2,4,5,1,27,0,3,3,5,4,4,0,10,1,42,0,2,1,16,0,8,1,3,3,1,2,2,4,5,1,27,0,1,3,2,2,5,4,4,0,9,1,61,0,9,1,2,3,4,4,4,1,27,0,4,2,5,4,4,0,7,1,64,0,6,1,3,3,4,4,3,1,26,0,6,2,5,4,6,0,3,1,24,0,4,3,39,0,5,1,3,3,3,4,1,0,2,1,27,0,6,2,2,4,2,2,1,4,33,0,6,3,5,0,2,2,31,0,3,1,4,3,1,5,2,4,29,0,12,2,33,0,6,3,5,0,3,2,2,0,6,5,3,0,6,3,15,0,5,3,2,5,30,0,12,2,34,0,5,3,4,0,5,2,7,5,3,0,10,3,7,0,9,3,2,5,12,0,1,3,17,0,1,3,12,2,33,0,7,3,1,0,6,2,7,5,13,3,7,0,9,3,3,5,5,0,1,2,4,0,3,3,16,0,2,3,12,2,2,0,2,2,10,0,9,3,9,0,1,5,7,3,7,2,5,5,15,3,6,0,4,5,2,3,2,2,1,3,3,5,2,0,4,2,3,0,4,3,13,0,2,2,1,0,1,3,14,2,1,0,6,2,5,0,14,3,3,0,4,5,2,3,1,5,3,3,11,2,16,3,1,2,3,0,2,6,6,5,3,2,4,5,5,2,10,3,8,0,1,3,27,2,21,3,7,5,14,2,2,3,8,2,6,3,2,2,2,6,8,5,3,2,4,5,5,2,12,3,5,0,1,3,26,2,24,3,6,5,14,2,2,3,9,2,5,3,1,2,3,6,8,5,3,2,4,5,5,2,18,3,26,2,24,3,6,5,31,2,3,6,8,5,3,2,5,5,2,2,20,3,27,2,16,3,4,2,5,3,3,5,32,2,4,6,6,5,4,2,5,5,2,2,2,3,12,4,7,3,27,2,12,3,11,2,2,3,1,5,15,2,3,6,16,2,3,6,6,5,4,2,4,5,24,4,4,3,1,4,5,2,2,4,2,2,3,4,2,2,3,4,5,2,3,4,6,3,23,2,1,4,7,2,5,6,1,4,5,2,2,4,6,2,1,4,3,6,1,4,5,5,1,3,2,2,1,3,1,5,2,2,25,4,4,3,27,4,5,3,23,2,2,4,6,2,5,6,9,4,5,2,6,4,4,5,4,3,3,2,25,4,2,3,4,4,6,1,19,4,5,3,23,2,4,4,5,2,4,6,24,4,4,3,3,2,17,4,1,1,13,4,8,1,11,4,4,1,3,4,4,3,23,2,1,4,3,1,1,4,4,2,3,6,6,4,3,0,5,4,2,1,9,4,4,3,3,2,7,4,6,0,3,7,5,1,8,4,13,1,3,0,3,4,9,1,4,3,3,1,20,2,5,1,5,2,1,6,4,4,10,0,3,1,4,7,5,0,4,3,3,2,5,4,6,0,3,1,2,7,8,1,3,4,19,1,1,4,10,1,4,3,5,1,8,2,2,5,7,2,5,1,6,2,5,4,7,0,6,1,4,7,5,0,4,3,4,2,3,4,4,0,49,1,4,3,7,1,4,2,6,5,5,2,5,1,6,2,5,4,7,0,6,1,4,7,3,1,2,0,4,3,4,2,3,0,32,1,2,0,17,1,7,0,7,1,2,2,7,5,4,2,5,1,8,2,3,4,7,0,17,1,3,3,5,2,2,0,32,1,3,0,11,1,2,7,10,0,8,1,9,5,3,2,5,1,7,2,3,4,6,0,19,1,3,3,5,2,1,0,34,1,8,0,4,1,3,7,13,0,2,2,5,1,7,5,2,2,5,1,2,0,6,2,3,4,4,0,21,1,3,3,3,2,1,0,36,1,10,0,2,1,1,7,12,0,2,1,1,0,3,2,4,1,5,5,4,2,3,1,5,0,3,3,1,2,3,4,3,0,9,1,2,0,11,1,4,3,3,2,24,1,6,0,14,1,16,0,4,1,8,2,4,5,5,2,3,1,4,0,5,3,3,4,12,1,4,0,7,1,2,0,4,3,3,2,22,1,12,0,12,1,13,0,5,1,4,2,2,5,3,2,3,5,6,2,2,1,4,0,4,3,4,4,12,1,4,0,5,1,4,0,4,3,4,2,19,1,16,0,15,1,8,0,6,1,3,2,2,5,12,2,6,0,4,3,3,4,14,1,3,0,4,1,5,0,4,3,4,2,18,1,17,0,16,1,6,0,8,1,15,2,7,0,4,3,4,4,14,1,2,0,4,1,5,0,4,3,3,2,17,1,9,0,5,1,6,0,17,1,2,0,11,1,9,2,3,5,3,2,2,1,5,0,3,3,4,4,15,1,1,0,4,1,5,0,4,3,2,2,10,1,2,0,4,1,10,0,9,1,5,0,29,1,8,2,3,5,3,2,3,1,4,0,1,5,2,3,4,4,1,0,23,1,2,0,3,3,2,2,6,1,18,0,12,1,4,0,29,1,14,2,2,1,5,0,2,5,1,3,3,4,3,0,22,1,2,0,3,3,2,2,1,4,4,1,17,0,16,1,3,0,32,1,9,2,3,1,4,0,4,5,3,4,3,0,21,1,3,0,1,3,4,2,1,4,2,1,13,0,3,1,1,0,20,1,1,0,33,1,7,2,3,1,4,0,6,5,3,4,3,0,20,1,3,0,3,2,3,4,14,0,8,1,3,0,47,1,2,2,2,5,3,2,4,1,3,0,7,5,3,4,4,0,16,1,5,0,4,2,3,4,11,0,10,1,6,0,32,1,4,0,8,1,1,0,2,2,2,5,3,2,4,1,3,0,3,5,2,2,3,5,2,4,4,0,6,1,2,0,6,1,7,0,4,2,2,4,10,0,11,1,9,0,28,1,7,0,5,1,3,0,2,2,2,5,4,2,2,1,4,0,2,5,4,2,2,5,2,4,4,0,5,1,1,0,2,3,7,1,6,0,4,2,2,4,9,0,10,1,11,0,24,1,19,0,8,2,1,1,6,0,5,2,4,5,6,0,2,1,5,3,8,1,4,0,1,3,3,2,1,4,10,0,8,1,14,0,15,1,28,0,6,2,8,0,6,2,4,5,7,0,6,3,7,1,4,0,2,3,2,2,1,4,10,0,8,1,15,0,10,1,33,0,4,2,10,0,6,2,3,5,7,0,6,3,2,0,5,1,4,0,2,3,2,2,1,4,11,0,7,1,16,0,9,1,34,0,3,2,11,0,6,2,2,5,1,0,4,1,2,0,6,3,2,0,4,1,5,0,1,3,3,2,1,4,14,0,3,1,19,0,5,1,36,0,2,2,12,0,7,2,9,1,1,0,5,3,3,0,2,1,5,0,4,2,1,4,91,0,1,3,6,2,9,1,4,0,2,3,9,0,5,2,1,4,91,0,3,3,5,2,9,1,14,0,5,2,2,4,90,0,3,3,4,2,2,4,8,1,14,0,5,2,3,4,89,0,4,3,1,2,4,4,7,1,16,0,4,2,3,4,89,0,4,3,5,4,5,1,18,0,4,2,3,4,2,6,87,0,4,3,4,4,3,0,3,1,18,0,4,2,3,4,3,6,86,0,3,3,4,4,25,0,4,2,3,4,3,6,29,0,8,3,15,0,7,3,27,0,3,3,4,4,14,0,2,3,9,0,4,2,2,4,5,6,28,0,9,3,14,0,9,3,20,0,9,3,3,4,13,0,6,3,6,0,4,2,2,4,7,6,9,0,2,2,9,0,9,3,4,5,2,3,2,0,4,2,9,0,8,3,3,0,2,5,5,0,5,6,5,0,4,3,4,5,1,3,2,4,3,2,2,0,2,2,7,0,7,3,5,0,4,2,2,4,2,6,2,5,5,6,6,0,4,2,4,0,12,3,7,5,1,2,2,5,6,2,1,0,5,2,5,3,3,2,2,0,3,5,1,0,13,6,1,0,1,3,7,5,2,2,2,5,7,2,5,0,10,3,3,0,7,2,4,5,9,6,7,2,14,3,2,5,2,2,3,5,1,2,2,5,12,2,5,3,4,2,5,5,15,6,7,5,2,2,2,5,9,2,16,3,6,2,5,5,9,6,7,2,12,3,4,5,2,2,3,5,15,2,2,3,6,2,6,5,14,6,8,5,14,2,14,3,7,2,5,5,10,6,6,2,12,3,10,5,10,2,2,5,2,2,2,3,6,2,6,5,14,6,8,5,14,2,14,3,7,2,6,5,9,6,6,2,13,3,10,5,9,2,2,5,10,2,5,5,5,6,2,0,8,6,7,5,4,2,2,5,9,2,15,3,4,2,2,3,6,5,3,4,5,6,2,4,2,2,2,4,11,3,1,4,4,2,4,5,2,2,3,5,19,2,1,4,4,5,5,3,4,0,1,4,5,6,2,4,6,5,4,2,2,5,7,2,2,4,13,3,2,4,4,2,3,3,3,5,16,4,11,3,1,4,5,2,2,5,3,2,3,5,9,2,1,5,9,2,2,4,2,5,1,4,5,3,4,0,11,4,3,5,10,2,7,4,9,3,4,4,4,2,3,3,20,4,7,3,4,4,5,2,2,5,14,2,3,5,7,2,6,4,4,3,4,0,15,4,10,2,20,4,4,2,3,3,9,4,2,3,9,4,5,3,6,4,22,2,4,5,5,2,6,4,3,3,5,0,17,4,7,2,3,3,18,4,4,2,3,3,5,4,7,3,5,4,4,1,2,3,1,1,1,3,7,4,20,2,5,5,5,2,6,4,1,3,7,0,6,4,5,0,3,4,2,3,1,4,7,2,4,3,13,4,2,1,2,4,4,2,2,3,5,4,9,3,3,7,13,1,3,0,1,7,18,2,6,5,5,2,3,4,11,0,3,4,11,0,3,3,4,1,2,2,1,1,6,3,2,7,5,4,6,1,2,0,6,3,5,4,9,3,3,7,13,1,3,0,2,7,16,2,2,5,2,2,3,5,2,2,5,4,13,0,2,4,11,0,4,3,5,1,7,3,3,7,3,0,7,1,2,0,5,3,4,4,9,3,19,1,2,0,4,7,2,0,11,2,3,5,2,2,3,5,2,2,5,4,5,0,4,1,4,0,3,4,10,0,1,1,4,3,3,1,7,3,4,7,3,0,5,1,4,0,5,3,3,4,7,3,24,1,4,7,2,0,11,2,9,5,6,4,3,0,11,1,2,4,9,0,4,1,12,3,4,7,8,1,5,0,4,3,2,4,7,3,29,1,3,7,9,2,1,1,9,5,4,4,2,3,18,1,5,0,7,1,6,3,1,7,2,3,2,7,11,1,6,0,3,3,2,4,7,3,30,1,3,7,4,2,2,5,3,2,2,1,7,5,4,4,2,3,30,1,5,3,2,1,5,7,11,1,7,0,2,3,2,4,5,3,5,1,3,3,24,1,3,7,4,2,2,5,3,2,3,1,6,5,4,4,1,3,31,1,3,3,4,1,5,7,11,1,7,0,2,3,2,4,5,3,4,1,5,3,14,1,5,0,4,1,3,0,8,2,1,0,4,1,5,5,4,4,11,1,1,3,2,0,18,1,3,3,15,1,12,0,2,3,2,4,4,3,5,1,5,3,12,1,7,0,5,1,2,0,7,2,2,0,4,1,5,5,4,4,8,1,4,3,3,0,33,1,14,0,2,3,3,4,2,3,6,1,6,3,11,1,6,0,7,1,1,0,7,2,2,0,4,1,1,3,4,5,4,4,7,1,5,3,4,0,32,1,12,0,4,3,3,4,2,3,7,1,5,3,11,1,5,0,9,1,6,2,3,0,4,1,1,3,3,5,1,3,4,4,7,1,5,3,3,0,33,1,4,0,2,1,6,0,2,3,2,2,3,4,10,1,4,3,8,1,7,0,10,1,6,2,7,1,4,3,5,4,2,0,4,1,6,0,26,1,13,0,4,1,5,0,4,2,4,4,10,1,3,3,6,1,9,0,11,1,5,2,7,1,3,3,6,4,3,0,2,1,7,0,10,1,1,0,9,1,19,0,5,1,3,0,5,2,5,4,9,1,3,3,6,1,9,0,12,1,5,2,6,1,3,3,6,4,12,0,7,1,4,0,7,1,21,0,5,1,3,0,5,2,5,4,9,1,3,3,6,1,8,0,13,1,5,2,6,1,2,3,1,2,6,4,11,0,8,1,4,0,5,1,21,0,7,1,3,0,5,2,5,4,9,1,4,3,5,1,8,0,13,1,4,2,7,1,2,3,1,2,5,4,11,0,9,1,4,0,5,1,5,0,6,1,9,0,7,1,4,0,5,2,5,4,9,1,5,3,14,0,7,1,5,0,2,2,8,0,3,2,5,4,8,0,6,1,1,0,3,1,14,0,13,1,3,0,6,1,3,3,4,0,1,3,3,2,5,4,2,0,6,1,1,0,6,3,35,0,3,2,5,4,8,0,6,1,17,0,14,1,2,0,6,1,4,3,4,0,2,3,2,2,5,4,2,0,6,1,3,0,4,3,35,0,4,2,4,4,6,0,8,1,16,0,16,1,1,0,5,1,5,3,5,0,3,3,5,4,2,0,5,1,4,0,4,3,35,0,4,2,5,4,4,0,16,1,4,0,21,1,2,0,4,1,5,3,5,0,3,3,5,4,2,0,5,1,4,0,4,3,8,0,4,1,23,0,1,3,3,2,1,3,4,4,3,0,42,1,2,0,2,1,3,0,2,3,7,0,3,3,5,4,2,0,5,1,5,0,2,3,9,0,4,1,23,0,5,3,4,4,3,0,42,1,16,0,3,3,5,4,7,1,16,0,4,1,23,0,5,3,3,4,3,0,42,1,16,0,4,3,5,4,4,1,46,0,5,3,3,4,12,0,15,1,7,0,8,1,19,0,4,3,5,4,50,0,5,3,3,4,15,0,10,1,36,0,4,3,4,4,51,0,5,3,4,4,4,0,3,5,9,0,7,1,37,0,4,3,3,4,52,0,1,3,4,2,5,4,2,0,5,5,8,0,1,1,4,3,2,1,37,0,4,3,3,4,48,0,4,3,6,2,5,4,6,5,7,0,9,3,19,0,1,3,14,0,6,3,3,4,30,0,2,3,16,0,4,3,6,2,5,4,6,5,7,0,11,3,14,0,5,3,12,0,7,3,3,4,29,0,4,3,15,0,1,3,2,5,1,2,2,5,4,2,5,4,6,5,6,0,13,3,12,0,6,3,12,0,7,3,2,2,1,4,14,0,2,3,13,0,4,3,2,2,13,0,1,2,2,5,1,2,2,5,4,2,5,4,1,0,8,5,2,0,15,3,11,0,5,3,3,2,10,0,7,3,5,2,4,0,4,5,3,0,4,3,12,0,2,3,1,2,4,3,4,0,4,5,4,0,11,2,2,4,1,0,6,2,5,5,1,0,16,3,9,0,4,3,6,2,1,0,2,2,4,0,9,3,4,5,2,2,4,5,2,2,4,5,5,3,8,0,4,3,2,2,7,3,7,5,24,2,3,5,1,2,19,3,4,0,6,3,10,2,12,3,4,5,2,2,4,5,2,2,5,5,7,3,3,0,4,3,6,2,6,3,8,5,15,2,2,5,11,2,18,3,2,0,5,3,13,2,11,3,6,2,11,5,14,3,7,2,6,3,7,5,15,2,2,5,14,2,19,3,17,2,10,3,7,2,11,5,12,3,9,2,6,3,5,5,34,2,17,3,17,2,10,3])

BUTTON_WIDTH = 80
BUTTON_HEIGHT = 15
BUTTON_PALETTE = [21162,19017,12710,25356,10565,16872,0]
# RLE format: [count1, value1, count2, value2, ...]
BUTTON_DATA_RLE = bytearray([1,4,1,2,1,1,61,2,1,1,10,2,1,1,1,2,3,1,1,4,9,1,1,0,2,1,1,0,9,1,6,0,13,1,2,0,8,1,2,0,7,1,9,0,1,1,1,0,6,1,1,0,1,1,1,4,2,1,1,0,1,1,1,0,6,1,1,0,12,1,1,0,10,1,2,0,1,1,7,0,1,1,9,0,1,1,9,0,3,1,1,0,2,1,4,0,4,1,1,4,2,2,2,1,2,0,2,1,12,0,3,1,1,0,3,1,1,0,8,1,2,0,3,1,3,0,2,1,1,0,1,1,1,0,1,1,11,0,1,3,2,0,1,3,11,0,3,1,1,4,1,2,8,1,13,0,3,1,4,0,1,1,1,0,2,1,4,0,2,1,1,0,1,1,5,0,1,1,10,0,1,3,10,0,1,3,7,0,2,1,1,5,1,4,1,2,9,1,1,0,1,1,8,0,2,1,2,0,1,1,6,0,1,1,4,0,3,1,5,0,1,1,1,0,1,1,10,0,1,3,3,0,1,3,1,0,1,3,1,0,1,3,10,0,1,1,1,0,3,2,13,1,4,0,1,1,1,0,2,1,3,0,2,1,1,0,6,1,2,0,5,1,1,0,6,1,1,0,1,1,15,0,3,3,3,0,2,3,4,0,1,1,3,2,12,1,6,0,1,1,5,0,2,1,1,0,2,1,2,0,2,1,1,0,6,1,2,0,2,1,7,0,1,3,8,0,2,1,7,0,1,3,4,0,3,1,1,2,1,4,1,2,16,1,7,0,2,1,1,0,2,1,3,0,1,1,1,0,7,1,17,0,1,1,2,0,2,1,5,0,2,3,8,0,1,1,1,4,1,2,1,0,3,1,1,0,10,1,2,0,3,1,4,0,4,1,8,0,1,1,1,0,6,1,11,0,2,1,7,0,2,1,4,0,2,1,5,0,1,1,1,4,1,2,4,1,1,0,5,1,10,0,1,1,3,0,1,1,1,0,1,1,9,0,4,1,3,0,1,1,5,0,1,1,11,0,1,1,2,0,3,1,4,0,1,3,5,0,1,1,1,4,1,2,2,1,1,0,3,1,2,0,1,1,10,0,1,1,6,0,1,1,13,0,7,1,10,0,5,1,1,0,3,1,11,0,1,1,1,4,1,2,1,1,2,0,1,1,1,0,5,1,1,0,5,1,1,0,4,1,1,0,1,1,4,0,2,1,1,0,1,1,3,0,1,1,1,0,3,1,1,0,3,1,1,0,2,1,1,0,5,1,1,0,1,1,2,0,6,1,1,0,7,1,3,0,1,1,3,0,1,1,1,4,1,2,1,1,1,0,5,1,4,0,5,1,3,0,1,1,6,0,2,1,1,0,1,1,1,0,1,1,4,0,2,1,2,0,3,1,1,0,1,1,2,0,2,1,9,0,1,1,1,0,1,1,1,0,7,1,1,0,3,1,1,0,2,1,1,0,1,1,1,4,32,2,1,1,32,2,5,4,9,2])

BUTTON_100_WIDTH = 100
BUTTON_100_HEIGHT = 15
BUTTON_100_PALETTE = [21162,19017,12710,25356,10565,16872,0]
# RLE format: [count1, value1, count2, value2, ...]
BUTTON_100_DATA_RLE = bytearray([1,4,1,2,2,1,76,2,1,1,13,2,1,1,1,2,4,1,1,4,12,1,1,0,2,1,1,0,12,1,7,0,16,1,3,0,10,1,2,0,9,1,12,0,1,1,1,0,7,1,2,0,1,1,1,4,3,1,1,0,1,1,1,0,8,1,1,0,15,1,1,0,13,1,3,0,1,1,8,0,2,1,11,0,1,1,11,0,4,1,2,0,2,1,5,0,5,1,1,4,1,2,1,1,1,2,2,1,3,0,2,1,6,0,1,1,4,0,1,1,3,0,4,1,1,0,4,1,1,0,10,1,3,0,3,1,4,0,3,1,1,0,1,1,2,0,1,1,14,0,1,3,2,0,1,3,14,0,4,1,1,4,1,2,5,1,1,0,4,1,17,0,4,1,5,0,1,1,1,0,2,1,6,0,2,1,1,0,1,1,7,0,1,1,13,0,1,3,12,0,2,3,8,0,3,1,1,5,1,4,1,2,12,1,1,0,1,1,1,0,1,1,8,0,1,1,1,0,1,1,2,0,2,1,4,0,1,1,2,0,1,1,5,0,4,1,6,0,1,1,2,0,1,1,13,0,1,3,4,0,1,3,1,0,1,3,2,0,1,3,3,0,1,3,8,0,2,1,1,0,3,2,17,1,5,0,1,1,1,0,3,1,3,0,3,1,1,0,8,1,2,0,7,1,1,0,7,1,2,0,1,1,18,0,4,3,4,0,3,3,4,0,2,1,3,2,16,1,7,0,1,1,1,0,1,1,5,0,2,1,1,0,1,1,1,0,1,1,2,0,3,1,1,0,7,1,3,0,2,1,9,0,1,3,10,0,3,1,2,0,1,1,6,0,1,3,5,0,4,1,1,2,1,4,1,2,10,1,1,0,9,1,9,0,3,1,1,0,2,1,4,0,1,1,2,0,8,1,22,0,1,1,3,0,2,1,2,0,1,1,3,0,3,3,10,0,1,1,1,4,1,2,1,1,1,0,4,1,1,0,3,1,1,0,8,1,3,0,4,1,4,0,5,1,10,0,2,1,1,0,2,1,1,0,4,1,14,0,1,1,1,0,1,1,9,0,2,1,5,0,2,1,7,0,1,1,1,4,1,2,5,1,2,0,6,1,2,0,1,1,10,0,1,1,4,0,1,1,1,0,1,1,12,0,4,1,4,0,1,1,5,0,1,1,1,0,1,1,14,0,1,1,3,0,3,1,5,0,1,3,7,0,1,1,1,4,1,2,3,1,1,0,4,1,2,0,2,1,12,0,1,1,8,0,1,1,16,0,9,1,1,0,1,1,11,0,6,1,1,0,4,1,14,0,1,1,1,4,1,2,2,1,2,0,2,1,1,0,6,1,1,0,1,1,1,0,5,1,1,0,3,1,1,0,1,1,1,0,1,1,5,0,3,1,1,0,1,1,4,0,1,1,1,0,4,1,2,0,3,1,1,0,3,1,1,0,1,1,1,0,4,1,2,0,1,1,3,0,7,1,1,0,9,1,4,0,1,1,4,0,1,1,1,4,1,2,2,1,1,0,6,1,1,0,1,1,3,0,1,1,1,0,5,1,3,0,1,1,8,0,3,1,1,0,1,1,1,0,2,1,4,0,3,1,3,0,3,1,1,0,2,1,2,0,3,1,11,0,1,1,1,0,2,1,1,0,2,1,1,0,6,1,1,0,2,1,1,0,1,1,1,0,2,1,2,0,1,1,1,4,40,2,1,1,25,2,1,4,15,2,6,4,11,2])




GUMB_15_U_WIDTH = 15
GUMB_15_U_HEIGHT = 15
GUMB_15_U_PALETTE = [2113,4258,19017,21162,25388,14791,29582,0]
# RLE format: [count1, value1, count2, value2, ...]
GUMB_15_U_DATA_RLE = bytearray([1,2,4,3,1,2,4,5,2,2,2,5,1,3,1,2,1,1,2,0,2,1,1,0,3,1,4,0,1,3,1,4,4,0,1,1,1,0,4,1,1,0,1,1,1,0,1,3,1,4,4,0,1,1,8,0,1,4,1,3,1,1,4,0,3,1,3,0,1,1,1,0,1,4,1,2,1,0,1,1,9,0,1,1,1,0,1,6,1,2,1,0,1,1,6,0,1,1,2,0,1,1,1,0,1,6,1,2,1,0,1,1,4,0,2,1,3,0,1,1,1,0,1,4,1,3,7,0,1,1,5,0,1,4,1,3,1,1,6,0,1,1,3,0,1,1,1,0,2,4,1,1,12,0,2,4,2,1,9,0,1,1,1,0,1,4,1,3,5,1,8,0,1,4,1,2,4,1,8,0,1,1,2,3,4,4,6,2,3,3,1,2])


GUMB_15_WIDTH = 15
GUMB_15_HEIGHT = 15
GUMB_15_PALETTE = [2113,21162,4226,19017,25388,14791,29582,0]
# RLE format: [count1, value1, count2, value2, ...]
GUMB_15_DATA_RLE = bytearray([1,3,4,1,1,3,4,5,2,3,2,5,1,1,1,3,1,2,2,0,2,2,1,0,3,2,4,0,1,1,1,4,4,0,1,2,1,0,4,2,1,1,1,3,1,0,1,1,1,4,4,0,1,2,4,0,3,1,1,0,1,4,1,1,1,2,4,0,3,2,1,0,1,1,1,3,1,2,1,0,1,4,1,3,1,0,1,2,6,0,1,1,1,3,1,1,1,2,1,0,1,6,1,3,1,0,1,2,5,0,1,1,1,3,1,1,1,0,1,2,1,0,1,6,1,3,1,0,2,1,3,0,1,2,1,1,1,3,2,0,1,2,1,0,1,4,1,1,1,0,1,1,1,3,1,1,2,0,1,1,1,3,1,1,4,0,1,4,1,1,1,2,1,0,1,1,1,3,1,0,1,1,1,3,1,1,3,0,1,2,1,0,2,4,1,2,1,0,1,1,1,3,1,1,1,3,1,1,6,0,2,4,2,2,1,0,1,1,1,3,2,1,4,0,1,2,1,0,1,4,1,1,4,2,2,1,7,0,1,4,1,3,4,2,8,0,1,2,2,1,4,4,6,3,3,1,1,3])


ITSTALKSBW_WIDTH = 64
ITSTALKSBW_HEIGHT = 64
ITSTALKSBW_PALETTE = [0,65535]
# RLE format: [count1, value1, count2, value2, ...]
ITSTALKSBW_DATA_RLE = bytearray([255,0,255,0,76,0,33,1,31,0,33,1,31,0,2,1,3,0,1,1,6,0,1,1,2,0,2,1,6,0,1,1,7,0,2,1,31,0,2,1,1,0,11,1,1,0,2,1,1,0,9,1,1,0,2,1,1,0,2,1,31,0,2,1,1,0,1,1,3,0,1,1,3,0,1,1,1,0,1,1,1,0,2,1,1,0,1,1,2,0,1,1,2,0,1,1,1,0,1,1,2,0,1,1,1,0,2,1,31,0,2,1,1,0,2,1,6,0,1,1,1,0,1,1,1,0,2,1,1,0,1,1,5,0,1,1,1,0,1,1,2,0,1,1,1,0,2,1,8,0,3,1,20,0,2,1,1,0,1,1,3,0,3,1,3,0,1,1,1,0,2,1,3,0,3,1,3,0,1,1,2,0,4,1,7,0,5,1,19,0,2,1,1,0,1,1,2,0,5,1,2,0,1,1,1,0,2,1,2,0,5,1,2,0,1,1,5,0,1,1,6,0,7,1,18,0,2,1,4,0,5,1,1,0,2,1,1,0,2,1,1,0,7,1,1,0,4,1,2,0,1,1,6,0,7,1,18,0,2,1,1,0,1,1,2,0,5,1,2,0,1,1,1,0,2,1,1,0,7,1,2,0,1,1,1,0,1,1,9,0,7,1,18,0,2,1,1,0,1,1,3,0,3,1,3,0,1,1,2,0,1,1,1,0,7,1,2,0,1,1,3,0,1,1,8,0,5,1,19,0,2,1,1,0,3,1,5,0,1,1,1,0,1,1,2,0,1,1,2,0,5,1,8,0,1,1,8,0,3,1,20,0,2,1,3,0,1,1,1,0,1,1,3,0,1,1,1,0,1,1,2,0,1,1,3,0,3,1,4,0,1,1,13,0,3,1,20,0,2,1,1,0,11,1,5,0,3,1,2,0,4,1,2,0,1,1,7,0,7,1,19,0,2,1,4,0,1,1,10,0,6,1,9,0,1,1,4,0,9,1,18,0,14,1,2,0,8,1,4,0,1,1,7,0,11,1,17,0,2,1,13,0,10,1,10,0,3,1,1,0,4,1,2,0,3,1,16,0,2,1,12,0,3,1,1,0,4,1,1,0,3,1,5,0,1,1,2,0,3,1,2,0,4,1,3,0,3,1,15,0,10,1,3,0,3,1,2,0,4,1,2,0,3,1,2,0,1,1,3,0,3,1,3,0,4,1,4,0,3,1,14,0,2,1,3,0,1,1,6,0,3,1,3,0,4,1,3,0,3,1,4,0,3,1,4,0,4,1,5,0,2,1,14,0,2,1,1,0,1,1,1,0,1,1,1,0,4,1,1,0,2,1,4,0,4,1,4,0,2,1,4,0,2,1,5,0,4,1,21,0,2,1,1,0,1,1,1,0,1,1,4,0,1,1,7,0,4,1,17,0,4,1,21,0,2,1,1,0,1,1,6,0,5,1,2,0,6,1,2,0,1,1,4,0,1,1,1,0,1,1,5,0,6,1,20,0,2,1,1,0,1,1,1,0,4,1,5,0,1,1,2,0,7,1,14,0,7,1,19,0,2,1,1,0,1,1,4,0,1,1,1,0,3,1,3,0,8,1,4,0,1,1,4,0,1,1,3,0,8,1,19,0,2,1,1,0,4,1,1,0,1,1,1,0,4,1,2,0,3,1,2,0,3,1,8,0,3,1,2,0,3,1,2,0,3,1,19,0,2,1,1,0,1,1,4,0,1,1,2,0,7,1,3,0,4,1,2,0,1,1,5,0,6,1,3,0,3,1,19,0,2,1,11,0,4,1,5,0,3,1,6,0,1,1,2,0,4,1,4,0,3,1,19,0,12,1,2,0,2,1,2,0,3,1,1,0,4,1,1,0,6,1,2,0,2,1,5,0,4,1,18,0,13,1,4,0,4,1,2,0,3,1,1,0,6,1,10,0,3,1,255,0,207,0,3,1,1,0,5,1,2,0,7,1,1,0,5,1,3,0,1,1,3,0,2,1,4,0,2,1,2,0,2,1,2,0,7,1,12,0,3,1,1,0,5,1,2,0,7,1,1,0,5,1,2,0,3,1,2,0,2,1,4,0,2,1,2,0,2,1,2,0,7,1,12,0,3,1,2,0,3,1,3,0,2,1,3,0,2,1,2,0,3,1,3,0,1,1,1,0,1,1,2,0,2,1,4,0,2,1,1,0,2,1,3,0,2,1,3,0,2,1,12,0,3,1,2,0,3,1,3,0,2,1,3,0,2,1,2,0,3,1,2,0,2,1,1,0,2,1,1,0,2,1,4,0,5,1,3,0,2,1,3,0,2,1,12,0,3,1,2,0,3,1,3,0,2,1,7,0,3,1,2,0,2,1,1,0,2,1,1,0,2,1,4,0,4,1,4,0,2,1,17,0,3,1,2,0,3,1,3,0,7,1,2,0,3,1,2,0,2,1,1,0,2,1,1,0,2,1,4,0,3,1,5,0,7,1,12,0,3,1,2,0,3,1,8,0,2,1,2,0,3,1,2,0,2,1,1,0,2,1,1,0,2,1,4,0,3,1,10,0,2,1,12,0,3,1,2,0,3,1,3,0,2,1,3,0,2,1,2,0,3,1,2,0,2,1,1,0,2,1,1,0,2,1,4,0,4,1,4,0,2,1,3,0,2,1,12,0,3,1,2,0,3,1,3,0,2,1,3,0,2,1,2,0,3,1,2,0,5,1,1,0,2,1,4,0,5,1,3,0,2,1,3,0,2,1,12,0,3,1,2,0,3,1,3,0,7,1,2,0,3,1,2,0,2,1,1,0,2,1,1,0,5,1,1,0,2,1,1,0,3,1,2,0,7,1,12,0,3,1,2,0,3,1,3,0,7,1,2,0,3,1,2,0,2,1,1,0,2,1,1,0,5,1,1,0,2,1,2,0,2,1,2,0,7,1,255,0,199,0])









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
0x3E, 0x41, 0x00, 0x00, 0x00, 0x00, 0x3E, 0x41, 0x00, 0x00, 0x00, 0x00, 

])


# Function to adjust 16-bit RGB565 color brightness
def adjust_color_brightness(color, brightness):
    # Extract RGB components from 16-bit RGB565 color
    red = (color >> 11) & 0x1F  # 5 bits for red
    green = (color >> 5) & 0x3F  # 6 bits for green
    blue = color & 0x1F  # 5 bits for blue

    # Adjust brightness
    red = int(red * brightness)
    green = int(green * brightness)
    blue = int(blue * brightness)

    # Clamp values to valid ranges
    red = min(red, 0x1F)
    green = min(green, 0x3F)
    blue = min(blue, 0x1F)

    # Recombine into 16-bit RGB565 color
    return (red << 11) | (green << 5) | blue







# FUNCTION FOR SETTING AN EXIT DOOR OBSOLETE NOT USED

def find_and_update(array, lvl1_x, lvl1_y):
    # Get the dimensions of the array
    rows = len(array)
    cols = len(array[0]) if rows > 0 else 0

    # List to store valid candidates (cells with 1 and exactly one adjacent 0)
    candidates = []

    # Iterate through the array to find valid cells
    for i in range(rows):
        for j in range(cols):
            if array[i][j] == 1:
                # Check adjacent cells (up, down, left, right)
                adjacent_zeros = []
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    x, y = i + dx, j + dy
                    if 0 <= x < rows and 0 <= y < cols and array[x][y] == 0:
                        adjacent_zeros.append((x, y))

                # If there is exactly one adjacent 0, add to candidates
                if len(adjacent_zeros) == 1:
                    candidates.append((i, j, adjacent_zeros[0]))

    # If no valid candidates are found, return the original array and coordinates
    if not candidates:
        print("No valid cell found.")
        return array, lvl1_x, lvl1_y

    # Randomly select a candidate
    selected = random.choice(candidates)
    i, j, (zero_x, zero_y) = selected

    # Update the array and coordinates
    array[i][j] = 2
    lvl1_x, lvl1_y = zero_x, zero_y

    print(f"Updated cell ({i}, {j}) to 2 and set lvl1_x, lvl1_y to ({zero_x}, {zero_y})")
    return array, lvl1_x, lvl1_y




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
        if empty_cells:  # Check for empty cell
            # Pick a random empty cell
            index = random.randint(0, len(empty_cells) - 1)
            pos = empty_cells.pop(index)
            centered_pos = (pos[0] + 0.5, pos[1] + 0.5)
            selected_positions.append(centered_pos)
    
    # Update the global orbs list
    orbs = selected_positions
    print(f"Placed {len(orbs)} orbs at: {orbs}")


    
def print_maze(maze):

    for row in maze:
        print("".join("#" if cell == 1 else " " for cell in row))

# Not used
def shuffle(arr):
    for i in range(len(arr) - 1, 0, -1):
        j = random.randint(0, i)
        arr[i], arr[j] = arr[j], arr[i]

def generate_maze(rows, cols):
    #Prims algorithm generation

    # Ensure rows and cols are odd
    if rows % 2 == 0:
        rows += 1
    if cols % 2 == 0:
        cols += 1

    # Initialize the maze grid
    maze = [[1 for _ in range(cols)] for _ in range(rows)]

    # Start with a random cell
    start_row, start_col = random.randint(1, rows - 2), random.randint(1, cols - 2)
    maze[start_row][start_col] = 0

    # List of frontier cells
    frontier = []
    for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        new_row, new_col = start_row + dr, start_col + dc
        if 0 < new_row < rows and 0 < new_col < cols:
            frontier.append((new_row, new_col, start_row, start_col))

    # Prim's Algorithm
    while frontier:
        # Randomly select a cell
        index = random.randint(0, len(frontier) - 1)
        new_row, new_col, parent_row, parent_col = frontier.pop(index)

        if maze[new_row][new_col] == 1:
            # Carve a path to the new cell
            maze[new_row][new_col] = 0
            # Carve a path through the wall between the new cell and its parent
            maze[(new_row + parent_row) // 2][(new_col + parent_col) // 2] = 0

            # Add new cells
            for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                next_row, next_col = new_row + dr, new_col + dc
                if 0 < next_row < rows and 0 < next_col < cols and maze[next_row][next_col] == 1:
                    frontier.append((next_row, next_col, new_row, new_col))
    print_maze(maze)
    return maze


def generate_map_with_rooms(rows, cols, max_room_size, num_rooms, start_x=1, start_y=1):

    # Initialize the map with walls
    map_grid = [[1 for _ in range(cols)] for _ in range(rows)]

    # List to store room coordinates (x, y, width, height)
    rooms = []

    for _ in range(num_rooms):
        # Random room size
        room_width = random.randint(3, max_room_size)
        room_height = random.randint(3, max_room_size)

        # Random room position
        room_x = random.randint(1, cols - room_width - 1)
        room_y = random.randint(1, rows - room_height - 1)

        # Check for room overlap
        overlap = False
        for other_room in rooms:
            other_x, other_y, other_width, other_height = other_room
            if (room_x < other_x + other_width and room_x + room_width > other_x and
                room_y < other_y + other_height and room_y + room_height > other_y):
                overlap = True
                break

        if not overlap:
            # Add the room to the list
            rooms.append((room_x, room_y, room_width, room_height))

            # Carve out the room in the map
            for y in range(room_y, room_y + room_height):
                for x in range(room_x, room_x + room_width):
                    map_grid[y][x] = 0

    # Ensure the starting position is connected to the first room
    if rooms:
        first_room_x, first_room_y, first_room_width, first_room_height = rooms[0]
        first_room_center_x = first_room_x + first_room_width // 2
        first_room_center_y = first_room_y + first_room_height // 2

        # Carve a horizontal corridor from the starting position to the first room
        for x in range(min(start_x, first_room_center_x), max(start_x, first_room_center_x) + 1):
            map_grid[start_y][x] = 0

        # Carve a vertical corridor from the starting position to the first room
        for y in range(min(start_y, first_room_center_y), max(start_y, first_room_center_y) + 1):
            map_grid[y][first_room_center_x] = 0

    # Connect the rooms with corridors
    for i in range(1, len(rooms)):
        # Get the center of the current room and the previous room
        x1, y1, w1, h1 = rooms[i - 1]
        x2, y2, w2, h2 = rooms[i]

        center_x1, center_y1 = x1 + w1 // 2, y1 + h1 // 2
        center_x2, center_y2 = x2 + w2 // 2, y2 + h2 // 2

        # Carve a horizontal corridor
        for x in range(min(center_x1, center_x2), max(center_x1, center_x2) + 1):
            map_grid[center_y1][x] = 0

        # Carve a vertical corridor
        for y in range(min(center_y1, center_y2), max(center_y1, center_y2) + 1):
            map_grid[y][center_x2] = 0
    print_maze(map_grid)
    return map_grid




# Update angle lookup tables
def update_angle_lookup():
    global angle_lookup, cos_lookup, sin_lookup
    angle_step = FOV / (NUM_RAYS - 1)  # Distribute rays evenly across FOV
    angle_lookup = [(player_angle - HALF_FOV + i * angle_step) for i in range(NUM_RAYS)]
    cos_lookup = [math.cos(angle) for angle in angle_lookup]
    sin_lookup = [math.sin(angle) for angle in angle_lookup]

# Initialize angle lookup tables
update_angle_lookup()


def cast_ray(angle, ray_id):
    x, y = player_x, player_y
    dx, dy = math.cos(angle), math.sin(angle)

    # Delta distances for DDA
    delta_x = abs(1 / dx) if dx != 0 else 1e30
    delta_y = abs(1 / dy) if dy != 0 else 1e30

    # Step direction and initial side distances
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    side_x = (x - int(x)) * delta_x if dx < 0 else (int(x) + 1 - x) * delta_x
    side_y = (y - int(y)) * delta_y if dy < 0 else (int(y) + 1 - y) * delta_y

    # DDA
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

        # If wall
        if scene[int(y)][int(x)]:
            return dist, scene[int(y)][int(x)], None

    return MAX_DEPTH, 1, None




def handle_input():
    global player_x, player_y, player_angle, orbs, brightness_factor, brightness_decreasing, batteryCharges, collectedR, move_speed, rot_speed, recently_hurt

    # Scan for button state changes
    buttons.scan()

    if buttons.state(Buttons.B) and buttons.state(Buttons.C):
        TerminateExecution()

    if buttons.state(Buttons.C):
        Reset()

    # Forward
    if buttons.state(Buttons.Up):
        new_x = player_x + math.cos(player_angle) * move_speed
        new_y = player_y + math.sin(player_angle) * move_speed

        # Check if the new position is within the maze boundaries
        if 0 <= new_x < len(scene[0]) and 0 <= new_y < len(scene):
            if not scene[int(new_y)][int(new_x)]:
                player_x, player_y = new_x, new_y

    # Backward
    if buttons.state(Buttons.Down):
        new_x = player_x - math.cos(player_angle) * move_speed
        new_y = player_y - math.sin(player_angle) * move_speed

        # Check if the new position is within the maze boundaries
        if 0 <= new_x < len(scene[0]) and 0 <= new_y < len(scene):
            if not scene[int(new_y)][int(new_x)]:
                player_x, player_y = new_x, new_y

    # Rotate left
    if buttons.state(Buttons.Left):
        player_angle -= rot_speed
        update_angle_lookup()  # Update angle lookup

    # Rotate right
    if buttons.state(Buttons.Right):
        player_angle += rot_speed
        update_angle_lookup()  # Update angle lookup

    # Check for orb collection
    for orb in orbs[:]:
        orb_x, orb_y = orb

        # Check if the player is near the orb
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
    display.fill(0)  # Clear the screen

    # Draw sky with gradient
    for y in range(SCREEN_HEIGHT // 2):  # Only draw the top half of the screen
        distance_factor = y / (SCREEN_HEIGHT // 2)
        brightness = max(0, 1 - distance_factor) * brightness_factor
        sky_color = adjust_color_brightness(SKY, brightness)
        display.line(0, y, SCREEN_WIDTH, y, sky_color)

    # Draw ground with gradient
    for y in range(SCREEN_HEIGHT // 2, SCREEN_HEIGHT):
        distance_factor = (y - SCREEN_HEIGHT // 2) / (SCREEN_HEIGHT // 2)
        brightness = max(0, distance_factor) * brightness_factor
        ground_color = adjust_color_brightness(GROUND, brightness)
        display.line(0, y, SCREEN_WIDTH, y, ground_color)

    # Create a depth buffer to store wall distances
    depth_buffer = [MAX_DEPTH] * SCREEN_WIDTH

    # Draw walls and orbs in a single pass
    for ray in range(NUM_RAYS):
        depth, wall_type, orb_data = cast_ray(angle_lookup[ray], ray)

        if wall_type > 0:  # Normal wall
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

    # Render orbs
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

    # Render multiplayer players
    # No time for implementing networking so this is commented out works though
    """
    for player in multiplayer_players:
        px, py = player["x"], player["y"]
        color = player["color"]
        rel_x = px - player_x
        rel_y = py - player_y
        dist = math.sqrt(rel_x**2 + rel_y**2) + epsilon
        angle_to_player = math.atan2(rel_y, rel_x) - player_angle
        while angle_to_player < -math.pi:
            angle_to_player += 2 * math.pi
        while angle_to_player > math.pi:
            angle_to_player -= 2 * math.pi
        if -HALF_FOV < angle_to_player < HALF_FOV:
            screen_x = int((angle_to_player + HALF_FOV) * (SCREEN_WIDTH / FOV))
            player_size = max(5, int(40 / dist))
            brightness = max(0, 1 - dist / MAX_DEPTH) * brightness_factor
            colorDark = adjust_color_brightness(color, brightness)
            if dist < depth_buffer[screen_x]:
                display.rect(
                    screen_x - player_size // 2,
                    (SCREEN_HEIGHT // 2) - player_size // 2,
                    player_size,
                    player_size * 2,
                    colorDark,
                    True
                )
    """

    # Render the enemy
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
        enemy_color = adjust_color_brightness(ENEMY_COL, brightness)  # Use RED for the enemy
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

    #   Draw player health in bottom-left corner
    for i in range(player_health):
        heart_x = 4 + i * 12  # spacing between icons
        heart_y = SCREEN_HEIGHT - 12  # near bottom
        draw_heart(display, heart_x, heart_y, RED)

    if recently_hurt:
        draw_crack()



    display.commit()


def mapRender(display):
    global scene, player_x, player_y, player_angle, orbs

    display.fill(0)  # Clear the screen

    # Map settings
    zoom = 5  # Zoom level (higher = more zoomed out)
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2
    distance_multiplier = 0.2  # Multiplier for dimming based on distance
    orb_illumination_radius = 1.0  # Radius around orbs to illuminate walls
    brightness_cutoff = 0.1  # Walls with brightness below this will be black
    max_render_distance = 10  # Skip rendering walls farther than this distance

    # Precompute sine and cosine for rotation
    cos_angle = math.cos(-player_angle)
    sin_angle = math.sin(-player_angle)

    # Render walls
    for y in range(len(scene)):
        for x in range(len(scene[0])):
            if scene[y][x] != 0:  # Any non not wall
                # Calculate wall center relative to the player
                wall_center_x = x + 0.5 - player_x
                wall_center_y = y + 0.5 - player_y
                distance = math.sqrt(wall_center_x**2 + wall_center_y**2)

                # Skip walls that are too far away
                if distance > max_render_distance:
                    continue

                # Calculate brightness based on distance
                brightness = max(0, 1 - distance * distance_multiplier)

                # Check if the wall is near any orb
                for orb_x, orb_y in orbs:
                    orb_distance = math.sqrt((orb_x - (x + 0.5))**2 + (orb_y - (y + 0.5))**2)
                    if orb_distance <= orb_illumination_radius:
                        brightness = min(1, brightness + 0.2)  # Slightly increase brightness
                        break

                # Apply brightness cutoff
                if brightness < brightness_cutoff:
                    continue  # Skip rendering this wall

                # Adjust wall color
                wall_color = adjust_color_brightness(WHITE, brightness)

                # Calculate wall corners relative to the player
                corners = [
                    (x - player_x, y - player_y),
                    (x + 1 - player_x, y - player_y),
                    (x + 1 - player_x, y + 1 - player_y),
                    (x - player_x, y + 1 - player_y),
                ]

                # Rotate and project corners
                projected_corners = []
                for cx, cy in corners:
                    rotated_x = cx * cos_angle - cy * sin_angle
                    rotated_y = cx * sin_angle + cy * cos_angle
                    screen_x = int(center_x + rotated_x * zoom)
                    screen_y = int(center_y + rotated_y * zoom)
                    projected_corners.append((screen_x, screen_y))

                # Check neighboring cells and draw only the lines bordering empty cells
                if y > 0 and scene[y - 1][x] == 0:  # Top
                    display.line(projected_corners[0][0], projected_corners[0][1], projected_corners[1][0], projected_corners[1][1], wall_color)
                if x < len(scene[0]) - 1 and scene[y][x + 1] == 0:  # Right
                    display.line(projected_corners[1][0], projected_corners[1][1], projected_corners[2][0], projected_corners[2][1], wall_color)
                if y < len(scene) - 1 and scene[y + 1][x] == 0:  # Bottom
                    display.line(projected_corners[2][0], projected_corners[2][1], projected_corners[3][0], projected_corners[3][1], wall_color)
                if x > 0 and scene[y][x - 1] == 0:  # Left
                    display.line(projected_corners[3][0], projected_corners[3][1], projected_corners[0][0], projected_corners[0][1], wall_color)

    # Render orbs
    for orb_x, orb_y in orbs:
        # Calculate orb position relative to the player
        rel_x = orb_x - player_x
        rel_y = orb_y - player_y

        # Rotate and project orb position
        rotated_x = rel_x * cos_angle - rel_y * sin_angle
        rotated_y = rel_x * sin_angle + rel_y * cos_angle
        screen_x = int(center_x + rotated_x * zoom)
        screen_y = int(center_y + rotated_y * zoom)

        # Draw the orb as a single pixel
        display.pixel(screen_x, screen_y, ORB)

    display.line(61, 61, 64, 64, 0xFFFF)
    display.line(61, 67, 64, 64, 0xFFFF)
    display.line(61, 61, 62, 64, 0xFFFF)
    display.line(61, 67, 62, 64, 0xFFFF)

    orbCounter()

    
    # Render enemy
    rel_x = enemy_x - player_x
    rel_y = enemy_y - player_y

    # Rotate and project enemy position
    rotated_x = rel_x * cos_angle - rel_y * sin_angle
    rotated_y = rel_x * sin_angle + rel_y * cos_angle
    screen_x = int(center_x + rotated_x * zoom)
    screen_y = int(center_y + rotated_y * zoom)

    # Draw the enemy as a red pixel
    display.pixel(screen_x, screen_y, RED)

    display.commit()


def BFS(grid, start, end):
    if not grid or not grid[0]:
        return []
    
    rows, cols = len(grid), len(grid[0])
    start_row, start_col = int(start[0]), int(start[1])
    end_row, end_col = int(end[0]), int(end[1])
    
    # Check if start or end is invalid (wall or out of bounds)
    if (start_row < 0 or start_row >= rows or start_col < 0 or start_col >= cols or
        end_row < 0 or end_row >= rows or end_col < 0 or end_col >= cols or
        grid[start_row][start_col] != 0 or grid[end_row][end_col] != 0):
        return []
    
    # Directions: left, right, up, down
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    
    # Queue for BFS
    queue = [(start_row, start_col)]
    # Parent matrix to reconstruct the path
    parent = [[None for _ in range(cols)] for _ in range(rows)]
    # Mark the start position as visited
    visited = [[False for _ in range(cols)] for _ in range(rows)]
    visited[start_row][start_col] = True
    
    while queue:
        current_row, current_col = queue.pop(0)
        
        # Check if reached the end
        if (current_row, current_col) == (end_row, end_col):
            # Reconstruct path
            path = []
            row, col = end_row, end_col
            while (row, col) != (start_row, start_col):
                path.append((row, col))
                row, col = parent[row][col]
            path.append((start_row, start_col))  # Add the start position
            return path[::-1]  # Reverse to get start-to-end path
        
        # Explore neighbors
        for dr, dc in dirs:
            next_row, next_col = current_row + dr, current_col + dc
            if (0 <= next_row < rows and 0 <= next_col < cols and
                not visited[next_row][next_col] and grid[next_row][next_col] == 0):
                visited[next_row][next_col] = True
                parent[next_row][next_col] = (current_row, current_col)
                queue.append((next_row, next_col))
    
    return []  # No path found

def enemyAI():
    global enemy_x, enemy_y, player_x, player_y
    global enemy_path, enemy_target_tile, random_target_tile
    global enemy_stun_timer, last_hit_time, player_health, recently_hurt, crack_start_time

    current_time = time.ticks_ms()  # Get current time in ms

    # Check stun
    if enemy_stun_timer > 0:
        # Check if stun duration passed (5000 ms = 5 sec)
        if time.ticks_diff(current_time, last_hit_time) >= 5000:
            enemy_stun_timer = 0
        else:
            return  # Skip movement while stunned

    current_tile = (int(enemy_y), int(enemy_x))
    player_tile = (int(player_y), int(player_x))

    # Manhattan distance
    distance = abs(player_tile[0] - current_tile[0]) + abs(player_tile[1] - current_tile[1])

    # Enemy hit player (within 0.5 units)
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

    # Pathfinding logic continues if not stunned
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

    print("Player:", player_x, player_y, "Health:", player_health)
    print("Enemy:", enemy_x, enemy_y, "Stunned:", enemy_stun_timer > 0)




def difficultyControl():
    global brightness_factor, brightness_decreasing, difficulty, brightness_speed, brightness_min, brightness_max
    global batteryCharges, last_brightness_reset, cooldown_progress

    current_time = time.ticks_ms()  # Get the current time in milliseconds
    cooldown_time = 3000  # Cooldown duration in milliseconds

    if difficulty == 0:
        # Always bright
        brightness_factor = brightness_max
        brightness_decreasing = False

    elif difficulty == 1:
        # Constantly decrease brightness
        brightness_decreasing = True
        if buttons.state(Buttons.A) and time.ticks_diff(current_time, last_brightness_reset) >= cooldown_time and batteryCharges > 0:
            brightness_factor = brightness_max  # Reset to max when A is pressed
            batteryCharges -= 1
            last_brightness_reset = current_time  # Update the last reset time


    # OBSOLETE NO TIME FOR THIS
    else:
        # Intermediate difficulties
        brightness_decreasing = True
        if buttons.state(Buttons.A) and time.ticks_diff(current_time, last_brightness_reset) >= cooldown_time:
            brightness_factor = brightness_max  # Reset to max when A is pressed
            last_brightness_reset = current_time  # Update the last reset time

        # Adjust brightness speed based on difficulty
        brightness_speed = 0.02 * difficulty  # Example: speed increases with difficulty

    # Gradually decrease brightness if decreasing is enabled
    if brightness_decreasing:
        brightness_factor -= brightness_speed
        if brightness_factor <= brightness_min:
            brightness_factor = brightness_min

    # Calculate cooldown progress (0 to 1, where 1 means cooldown is complete)
    time_since_reset = time.ticks_diff(current_time, last_brightness_reset)
    cooldown_progress = min(1, time_since_reset / cooldown_time)
    
        
def batteryDraw():
    global batteryCharges, cooldown_progress

    # Draw the battery outline
    display.rect(5, 5, 22, 9, WHITE, False)
    # display.rect(93+2, 6, 2, 7, WHITE, True)
    display.rect(27, 6, 2, 7, WHITE, True)

    # Draw the battery charges
    for i in range(batteryCharges):
        x = 6 + i * 4  # Calculate x position for each square
        display.rect(x + 1, 7, 2, 5, WHITE, True)  # Draw square with width 2 and 1 px padding

    # Draw the cooldown bar if cooldown is not complete
    if cooldown_progress < 1:
        cooldown_width = int((1 - cooldown_progress) * 50)  # Max width is 50
        cooldown_x = (SCREEN_WIDTH - cooldown_width) // 2  # Center the bar horizontally
        cooldown_y = 100  # Y position of the bar

        # Draw the cooldown bar
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


# RESET using mate map generation

def ResetM():
    
    # Resets the game with a new maze and ensures the player starting position is valid.
    # Also places new orbs in the maze.
    
    global scene, player_x, player_y, player_angle, lvl1_x, lvl1_y, orbsToPlace
    
    # Generate new maze
    new_maze = generate_maze(mapSize, mapSize)
    
    # Ensure the starting area is clear
    start_x, start_y = 1, 1  # Starting position
    
    # Clear a small area around the starting position
    for dy in range(0, 2):
        for dx in range(0, 2):
            if 0 <= start_y + dy < len(new_maze) and 0 <= start_x + dx < len(new_maze[0]):
                new_maze[start_y + dy][start_x + dx] = 0
    
    # Update the scene
    scene = new_maze
    
    # Place player at the cleared starting position
    player_x = float(start_x + 0.5)
    player_y = float(start_y + 0.5)
    player_angle = 45
    
    # Update angle lookup tables
    update_angle_lookup()
    
    # Place new orbs in the maze
    place_orbs(orbsToPlace)



    
    print("RESET TRIGGERED - New maze generated with clear starting area")

# RESET using room map generation

def Reset():
    global scene, player_x, player_y, player_angle, lvl1_x, lvl1_y, enemy_x, enemy_y

    # Generate a map with rooms
    rows, cols = mapSize, mapSize
    max_room_size = 3
    num_rooms = int(mapSize * (3/5)) # int(mapSize * (3/5))
    scene = generate_map_with_rooms(rows, cols, max_room_size, num_rooms)

    # Ensure the starting area is clear
    start_x, start_y = 1, 1  # Starting position
    for dy in range(0, 2):
        for dx in range(0, 2):
            if 0 <= start_y + dy < len(scene) and 0 <= start_x + dx < len(scene[0]):
                scene[start_y + dy][start_x + dx] = 0

    # Place player at the cleared starting position
    player_x = float(start_x + 0.5)
    player_y = float(start_y + 0.5)
    player_angle = 45

    # Update angle lookup tables
    update_angle_lookup()

    # Place new orbs in the maze
    place_orbs(orbsToPlace)  

    enemy_x, enemy_y = random_empty_cell(scene)  # Find a random empty cell for the enemy
    enemy_x += 0.5  # Center the enemy in the cell

    print("RESET TRIGGERED - New map with rooms generated")




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
    displayC.draw_rle_image_to_buffer(IMAGE_DATA_RLE, PALETTE, IMAGE_WIDTH, IMAGE_HEIGHT, 0, 0)
    # The previous function is a bit slow so no need for a delay here
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

    print("Precompiling images...")

    # PRECOMPILE IMAGES

    try:
        displayC.draw_rle_image_store("itstalksbw", ITSTALKSBW_DATA_RLE, ITSTALKSBW_PALETTE, ITSTALKSBW_WIDTH, ITSTALKSBW_HEIGHT)
        displayC.draw_frame_to_buffer("itstalksbw", 32, 32, ITSTALKSBW_WIDTH, ITSTALKSBW_HEIGHT)
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

    print("Done precompiling images.")

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


LoadingScreen()



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
        displayC.draw_rle_image_to_buffer(IMAGE_DATA_RLE, PALETTE, IMAGE_WIDTH, IMAGE_HEIGHT, 0, 0)
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
        y_pos = 30 + (3 - i) * 10  # Moves down each iteration
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

    # Handle toggles BEFORE drawing
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
    displayC.draw_text(font_bytes, 0, 70, "github.com/ROTIN37/NewBit", WHITE, None)

    if buttons.state(Buttons.B):
        time.sleep(0.2)  # Debounce to prevent immediate exit
        current_menu = 0  # Go back to the Main menu
        selectedButton = 0
        Audio.SFX.interact()
        return

    display.commit()


def ray_menu():
    global MAX_DEPTH, raySel, current_menu, selectedButton

    maybe_draw_background()

    possibleRays = [2,3,4,5,6,7,8]  # Must match raySel index range
    MAX_DEPTH = possibleRays[raySel]

    buttons.scan()

    display.text("< B", 5, 5, WHITE)


    displayC.rectF(20, 20, 88, 88, 0x39C7) # Dark gray rectangle
    displayC.rect(20, 20, 88, 88, 0x94B2) # Gray rectangle

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
        current_menu = 6  # Go back to the Graphics menu
        selectedButton = 0
        Audio.SFX.interact()
        return

    # Center "Ray Count" label
    text = "Max distance"
    text_width = (len(text) * 6) + ((len(text) - 1) * 2)
    x_text = (SCREEN_WIDTH - text_width) // 2
    display.text(text, x_text, 32, WHITE)

    # Center ray count value
    ray_value = f"< {possibleRays[raySel]} >"
    ray_value_width = (len(ray_value) * 6) + ((len(ray_value) - 1) * 2)
    x_ray_value = (SCREEN_WIDTH - ray_value_width) // 2
    display.text(ray_value, x_ray_value, 64, WHITE)

    display.commit()



def fov_menu():
    global current_menu, selectedButton, current_fov_index, n, FOV, HALF_FOV

    # These n values correspond to: 180°, 90°, 60°, 45°, 36°
    FOV_OPTIONS = [1, 2, 3, 4, 5]  # π/1 = 180°, π/2 = 90°, etc.
    FOV_DEGREES = [180, 90, 60, 45, 36]

    
    maybe_draw_background()
    # Get current FOV value
    n = FOV_OPTIONS[current_fov_index]
    FOV = math.pi / n
    HALF_FOV = FOV / 2
    FOVn = FOV_DEGREES[current_fov_index]

    displayC.rectF(32, 24, 64, 64, 0x39C7) # Dark gray rectangle
    displayC.rect(32, 24, 64, 64, 0x94B2) # Gray rectangle

    display.text("< B", 5, 5, WHITE)
    # Center "FOV" label
    text = "FOV"
    text_width = (len(text) * 6) + ((len(text) - 1) * 2)
    x_text = (SCREEN_WIDTH - text_width) // 2

    displayC.draw_text(font_bytes, x_text, 32, text, WHITE, None)

    # Center FOV value
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

    if buttons.state(Buttons.C):
        break

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
    enemy_speed = 0.05
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




# Globals
crack_start_time = 0
current_crack = None

def generate_radial_crack(center=None, num_branches=8, segments_per_branch=3, spread=25):
    """Generate a radial crack from a center point with jagged branches."""
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
            # Add jitter to simulate crack roughness
            dx = math.cos(angle_rad) * random.randint(spread - 10, spread + 10)
            dy = math.sin(angle_rad) * random.randint(spread - 10, spread + 10)
            x += dx
            y += dy

            # Clamp to screen bounds
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

    # Draw all crack branches
    for branch in current_crack:
        for i in range(len(branch) - 1):
            x1, y1 = branch[i]
            x2, y2 = branch[i + 1]
            display.line(x1, y1, x2, y2, RED)



gc.collect()
print(gc.mem_free())












# setDif()
currentLevel = 0
difficulty = 1

Reset()

# Global variable to track whether the map is open
map_open = False





exceptionCounter = 0

# Store original/base speeds
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

        # Cap FPS to MAX_FPS
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
        print("Exception occurred.")
        if exceptionCounter > 5:
            display.fill(0x0000)
            display.commit()
            time.sleep(1)
            print(f"Program failed, debug info: \n {e}")
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
