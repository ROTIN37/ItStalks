import serial
import pygame
import numpy as np
import time
import sys

# ==== CONFIGURATION ====
WIDTH = 128 # Do not change
HEIGHT = 128 # Do not change
# IMPORTANT: Set the correct serial port for your system
# For Windows, it might be 'COM3', 'COM4', etc.
# For Linux, it might be '/dev/ttyUSB0', '/dev/ttyACM0', etc.
# For Mac, it might be '/dev/cu.usbmodemXXXX', etc.

# For windows you can find the port in Device Manager in Ports (COM & LPT)
# or use mode and look for COM ports

# For Linux you can find the port with ls /dev/tty*

# For Mac you can find the port with ls /dev/cu.*

SERIAL_PORT = ''  # IMPORTANT Replace with your correct port

BAUDRATE = 115200 # Leave as is unless you know what you're doing
# The ESP32 should be set to the same baud rate

SCALE = 8 # Determines the size of the image on the screen (8x = 1024x1024)
# Set the scale to 1 for 128x128 pixels, 2 for 256x256 pixels, etc.

FLUSH_INTERVAL = 2.5  # Flushes the serial buffer every 2.5 seconds to recover alignment
# This is because this code is shiet but it still mostly works

# ==== SETUP SERIAL ====
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=2, write_timeout=2)

# ==== CHECK SERIAL PORT ====
if SERIAL_PORT == '':
    print("❌ Port not selected. Please set the SERIAL_PORT variable to the correct port.")
    sys.exit(1)  # Exit the program with an error code


# ==== SETUP PYGAME FULLSCREEN ====
pygame.init()
info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
pygame.display.set_caption("ESP32 RGB565 Stream")

# ==== RGB565 TO RGB888 ====
def rgb565_to_rgb888(data):
    img = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for i in range(WIDTH * HEIGHT):
        high = data[2 * i]
        low = data[2 * i + 1]
        value = (high << 8) | low

        r = (value >> 11) & 0x1F
        g = (value >> 5) & 0x3F
        b = value & 0x1F

        img[i // WIDTH, i % WIDTH, 0] = (r * 255) // 31
        img[i // WIDTH, i % WIDTH, 1] = (g * 255) // 63
        img[i // WIDTH, i % WIDTH, 2] = (b * 255) // 31
    return img

# ==== INIT ====
running = True
last_flush_time = time.time()
last_good_frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

# ==== MAIN LOOP ====
while running:
    try:
        current_time = time.time()
        if current_time - last_flush_time > FLUSH_INTERVAL:
            ser.reset_input_buffer()
            print("🔄 Serial buffer flushed to recover alignment.")
            last_flush_time = current_time
            continue

        ser.write(b'READY')

        data = ser.read(WIDTH * HEIGHT * 2)

        if len(data) == WIDTH * HEIGHT * 2:
            last_good_frame = rgb565_to_rgb888(data)
        else:
            print(f"Incomplete or missing frame ({len(data)} bytes), showing last good frame.")

        surface = pygame.surfarray.make_surface(np.transpose(last_good_frame, (1, 0, 2)))
        surface = pygame.transform.scale(surface, (WIDTH * SCALE, HEIGHT * SCALE))

        screen.fill((0, 0, 0))  # Clear background
        screen.blit(surface, (0, 0))  # Top-left corner

        if len(data) != WIDTH * HEIGHT * 2:
            pygame.draw.rect(screen, (255, 128, 0), (0, 0, WIDTH * SCALE, HEIGHT * SCALE), 4)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False

        time.sleep(0.01)

    except serial.SerialException as e:
        print("Serial error:", e)
        time.sleep(0.5)

# ==== CLEANUP ====
pygame.quit()
ser.close()
