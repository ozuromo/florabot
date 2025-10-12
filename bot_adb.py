import logging
from com.dtmilano.android.viewclient import ViewClient
import time
import os
import numpy as np
import subprocess
import tkinter as tk
from tkinter import messagebox
import threading

# Function to configure logging based on user input
def setup_logging():
    enable_logging = input('Do you want to enable logging? (y/n): ').strip().lower()
    if enable_logging == 'y':
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("Logging is enabled at DEBUG level.")
    else:
        logging.basicConfig(level=logging.CRITICAL)  # Disable all logs below CRITICAL level
        print("Logging is disabled.")

class Bot:
    def __init__(self, station_cap, station_uses, station_num, station_start, rows):
        logging.info("Initializing bot with station_cap=%s, station_uses=%s, station_num=%s, station_start=%s, rows=%s", 
                     station_cap, station_uses, station_num, station_start, rows)

        self.station_cap = station_cap
        self.station_uses = station_uses
        self.rows = rows
        self.cols = 9
        self.offset = 10
        self.empty_colors = [np.array([223, 190, 164]), np.array([234, 208, 178])]
        self.threshold = 0.90
        self.item_tiles = [(i, j) for i in range(self.rows) for j in range(self.cols)]
        self.station_tiles = self.create_station_tiles(station_start, station_num)
        self.uses = self.station_cap // self.station_uses
        self.running = False

        self.device, self.serialno = ViewClient.connectToDeviceOrExit(verbose=True)
        logging.info("Bot initialized and connected to device.")

    def create_station_tiles(self, station_start, station_num):
        logging.info("Creating station tiles from station_start=%s to station_num=%s", station_start, station_num)
        station_tiles_blueprint = [(6-i, j) for i in range(2) for j in range(7)] +\
            [(6-i, j) for i in range(2, 4) for j in range(9)]
        return station_tiles_blueprint[station_start:station_start+station_num]

    def ccoeff_normed(self, template, target):
        logging.debug("Performing normalized cross-correlation.")
        template_norm = (template - np.mean(template)) / np.std(template)
        target_norm = (target - np.mean(target)) / np.std(target)
        cross_corr = np.correlate(target_norm.flatten(), template_norm.flatten())
        norm_factor = np.sqrt(np.sum(template_norm**2) * np.sum(target_norm**2))
        normalized_cc = cross_corr / norm_factor
        return normalized_cc

    def screenshot(self):
        logging.info("Taking a screenshot.")
        im = self.device.takeSnapshot(reconnect=True) # PIL img
        return np.array(im)[:, :, :3]

    def index_to_pixel(self, tile):
        i, j = tile
        x_offset = 444
        y_offset = 205
        tile_height = 115.333
        tile_width = 115.25
        x = int(x_offset + tile_width*j + tile_width/2)
        y = int(y_offset + tile_height*i + tile_height/2)
        logging.debug("Tile %s converted to pixel coordinates (%s, %s)", tile, x, y)
        return x, y
    
    def is_empty(self, tile, img):
        x, y = self.index_to_pixel(tile)
        tile_color = img[y, x]
        return any((tile_color == color).all() for color in self.empty_colors)

    def find_match(self, target_tile, tiles, img):
        if not tiles:
            logging.info("No tiles to match.")
            return False
        
        x, y = self.index_to_pixel(target_tile)
        target = img[y - self.offset:y + self.offset, x - self.offset:x + self.offset]

        for match_tile in tiles:
            if self.is_empty(match_tile, img):
                continue

            x, y = self.index_to_pixel(match_tile)
            match = img[y - self.offset:y + self.offset, x - self.offset:x + self.offset]

            coef = self.ccoeff_normed(match, target)
            logging.debug("Correlation coefficient for tiles %s and %s: %s", target_tile, match_tile, coef)
            if coef > self.threshold:
                logging.info("Found a match for tile %s", target_tile)
                return match_tile
            
        logging.info("No match found for tile %s", target_tile)
        return False

    def drag(self, match, tile):
        x, y = self.index_to_pixel(match)
        z, w = self.index_to_pixel(tile)
        logging.info("Dragging from %s to %s", (x, y), (z, w))
        self.device.drag((x, y), (z, w), duration=100)

    def use_station(self, tile):
        x, y = self.index_to_pixel(tile)
        logging.info("Using station at tile %s", tile)
        self.device.touch(x, y)
        return True

    def run(self):
        logging.info("Start run")
        matched = False
        tiles = self.item_tiles.copy()
        img = self.screenshot()

        while tiles:
            tile = tiles.pop(0)

            if self.is_empty(tile, img):
                continue

            match = self.find_match(tile, tiles, img)

            if match:
                matched = True
                self.drag(match, tile)
                tiles.remove(match)

        if not matched:
            logging.info("No matches found, using station if available.")
            if not self.station_tiles:
                logging.warning("No stations available.")
                return False

            if self.use_station(self.station_tiles[0]):
                self.uses -= 1
            
            if self.uses == 0:
                logging.info("Station depleted, moving to next station.")
                self.station_tiles.pop(0)
                self.uses = self.station_cap // self.station_uses

        time.sleep(0.3)
        return True

def start_bot():
    global bot
    try:
        bot_capacity = int(station_capacity_entry.get())
        bot_stations = int(number_of_stations_entry.get())
        bot_clicks = int(number_of_clicks_entry.get())
        bot_used_stations = int(stations_used_entry.get())
        rows = int(rows_entry.get())  # Get number of rows

        # start adb
        serial = 'localhost:5555'
        adb_path = os.path.join(os.getcwd(), 'platform-tools')
        subprocess.check_output(['adb', 'connect', serial], cwd=adb_path, shell=True)
    
        bot = Bot(bot_capacity, bot_clicks, bot_stations, bot_used_stations, rows)

        bot.running = True
        disable_fields()

        while bot.running:
            if not bot.run():
                logging.warning('\nNo stations available, exiting Bot.')
                break
    except Exception as e:
        logging.error(f"Error occurred: {e}")
    finally:
        enable_fields()

def stop_bot():
    # Stop the bot by setting the running flag to False
    bot.running = False

def disable_fields():
    station_capacity_entry.config(state='disabled')
    number_of_stations_entry.config(state='disabled')
    number_of_clicks_entry.config(state='disabled')
    stations_used_entry.config(state='disabled')
    rows_entry.config(state='disabled')  # Disable rows entry

def enable_fields():
    station_capacity_entry.config(state='normal')
    number_of_stations_entry.config(state='normal')
    number_of_clicks_entry.config(state='normal')
    stations_used_entry.config(state='normal')
    rows_entry.config(state='normal')  # Enable rows entry

def show_info(title, message):
    messagebox.showinfo(title, message)

# GUI Setup
root = tk.Tk()
root.title("Bot Control")

# Adding margins by using a frame
main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack()

# Labels and Entries for the fields
tk.Label(main_frame, text="Station Capacity").grid(row=0, column=0)
station_capacity_entry = tk.Entry(main_frame)
station_capacity_entry.grid(row=0, column=1)
tk.Button(main_frame, text="?", command=lambda: show_info("Station Capacity", "Enter the maximum number of uses the station can handle.")).grid(row=0, column=2)

tk.Label(main_frame, text="Number of Stations").grid(row=1, column=0)
number_of_stations_entry = tk.Entry(main_frame)
number_of_stations_entry.grid(row=1, column=1)
tk.Button(main_frame, text="?", command=lambda: show_info("Number of Stations", "Enter the total number of stations available.")).grid(row=1, column=2)

tk.Label(main_frame, text="Number of Clicks/Loop").grid(row=2, column=0)
number_of_clicks_entry = tk.Entry(main_frame)
number_of_clicks_entry.grid(row=2, column=1)
tk.Button(main_frame, text="?", command=lambda: show_info("Clicks per Loop", "Enter how many clicks each loop should perform.")).grid(row=2, column=2)
tk.Label(main_frame, text="Stations Already Used").grid(row=3, column=0)
stations_used_entry = tk.Entry(main_frame)
stations_used_entry.grid(row=3, column=1)
tk.Button(main_frame, text="?", command=lambda: show_info("Stations Already Used", "Enter the number of stations you have already utilized.")).grid(row=3, column=2)

tk.Label(main_frame, text="Number of Rows").grid(row=4, column=0)
rows_entry = tk.Entry(main_frame)
rows_entry.grid(row=4, column=1)
tk.Button(main_frame, text="?", command=lambda: show_info("Number of Rows", "Enter how many rows to be used in the bot's logic.")).grid(row=4, column=2)

# Add instruction text
instruction_label = tk.Label(main_frame, text="Please activate 'Batch Produce' in Flora's Craft Workshop.")
instruction_label.grid(row=5, column=0, columnspan=3, pady=(10, 0))

# Start and Stop buttons
start_button = tk.Button(main_frame, text="Start", command=lambda: threading.Thread(target=start_bot).start())
start_button.grid(row=6, column=0)

stop_button = tk.Button(main_frame, text="Stop", command=stop_bot)
stop_button.grid(row=6, column=1)


# Setting default values if needed
station_capacity_entry.insert(0, "5")
number_of_stations_entry.insert(0, "32")
number_of_clicks_entry.insert(0, "1")
stations_used_entry.insert(0, "0")
rows_entry.insert(0, "3")  # Default value for number of rows

# Start the GUI event loop
root.mainloop()