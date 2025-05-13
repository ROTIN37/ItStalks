# It Stalks  
<p align="center">  
  <img src="logo.png" alt="Logo" width="20%" style="image-rendering: pixelated;">  
</p>  

**A semi 3D maze crawler for the CircuitMess Bit.**  

## Overview  
*It Stalks* is a Python-based game designed for the CircuitMess Bit. It features a semi-3D maze-crawling experience and offers multiple ways to interact with the game, including streaming the gameplay to a computer or playing directly on the device.  

**Important Notes**:  
- Running `setup.py` writes required images to the device's flash memory. This process may sometimes interfere with other games stored on the device.  
- If `setup.py` causes the device to break, refer to the [Rebuilding the Device](#rebuilding-the-device) section to restore functionality.  

---

## Table of Contents  
- [Setup](#setup)  
- [Display.py](#displaypy)  
- [Game Variants](#game-variants)  
  - [gameDisplayBI.py](#gamedisplaybipy)  
  - [game.py](#gamepy)  
  - [main.py](#mainpy)  
- [How to Play](#how-to-play)  
- [Rebuilding the Device](#rebuilding-the-device)  
- [License](#license)  

---

## Setup  
1. Clone or download this repository to your local machine.  
2. Upload the `setup.py` file to the CircuitMess Bit using the [Code.CircuitMess.com](https://code.circuitmess.com) web-based IDE.  
3. **On the CircuitMess Bit**, run the `setup.py` script to set up the necessary environment and configurations.  
   **Note**: Running `setup.py` writes images to the flash memory of the CircuitMess Bit device, which may cause other games to stop functioning properly. If the device experiences issues after running `setup.py`, refer to the [Rebuilding the Device](#rebuilding-the-device) section.  

---

## Display.py  
This script is used for displaying the CircuitMess Bit's screen on your computer.  
- **Usage**: Run the file in the command line using:  
  ```bash  
  python path/to/Display.py  
  ```  

---

## Game Variants  

### gameDisplayBI.py  
This is the game file with streaming logic built-in.  
- **Usage**: Run this file after executing `setup.py`.  
- **Note**: Works when uploaded through the CircuitMess web-based IDE at [Code.CircuitMess.com](https://code.circuitmess.com).  

### game.py  
This is the regular game file without streaming logic.  
- **Usage**: Run this file after executing `setup.py`.  
- **Note**: Works when uploaded through the CircuitMess web-based IDE at [Code.CircuitMess.com](https://code.circuitmess.com).  

### main.py  
This is the complete game packaged in a single file.  
- **Note**:  
  - This file **ONLY** works if uploaded directly to the CircuitMess Bit (not through the web-based IDE).  
  - Use the CircuitMess web-based programming IDE at [Code.CircuitMess.com](https://code.circuitmess.com) to upload this file directly to the device for gameplay.  

---

## How to Play  
- Run the respective game file depending on your setup preferences (streaming or non-streaming).  
- Navigate through the maze using the controls provided by the CircuitMess Bit.  

---

## Rebuilding the Device  
If everything breaks or the game fails to run, you can rebuild your CircuitMess Bit:  
1. Use [esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32/) to erase the flash memory by running the `erase-flash` command.  
2. Visit [Code.CircuitMess.com](https://code.circuitmess.com).  
3. Reinstall MicroPython from the website.  

This will restore your device to a clean state, allowing you to upload and play the game again.  

---

## License  
This project is licensed under the [Apache License 2.0](LICENSE).  

---  

Let me know if there’s anything else you’d like to update!
