import logging
from com.dtmilano.android.viewclient import ViewClient
import time
import os
import numpy as np
import subprocess
import tkinter as tk
from tkinter import messagebox
import threading


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Bot:
    def __init__(self, bot_station_attempts, station_num, station_start, rows):
        logging.info(
            "Initializing bot with station_attempts=%s, station_num=%s, station_start=%s, rows=%s",
            bot_station_attempts,
            station_num,
            station_start,
            rows,
        )

        self.station_uses = int(np.ceil(bot_station_attempts / (rows * 9))) + 1
        self.rows = rows
        self.cols = 9
        self.offset = 10
        self.empty_colors = [np.array([223, 190, 164]), np.array([234, 208, 178])]
        self.threshold = 0.90
        self.item_tiles = [(i, j) for i in range(self.rows) for j in range(self.cols)]
        self.station_tiles = self.create_station_tiles(station_start, station_num)
        self.uses = self.station_uses
        self.running = False

        self.device, self.serialno = ViewClient.connectToDeviceOrExit(verbose=True)
        logging.info("Bot initialized and connected to device.")

    def create_station_tiles(self, station_start, station_num):
        logging.debug(
            "Creating station tiles from station_start=%s to station_num=%s",
            station_start,
            station_num,
        )
        station_tiles_blueprint = [(6 - i, j) for i in range(2) for j in range(7)] + [
            (6 - i, j) for i in range(2, 4) for j in range(9)
        ]
        return station_tiles_blueprint[station_start : station_start + station_num]

    def ccoeff_normed(self, template, target):
        logging.debug("Performing normalized cross-correlation.")
        template_norm = (template - np.mean(template)) / np.std(template)
        target_norm = (target - np.mean(target)) / np.std(target)
        cross_corr = np.correlate(target_norm.flatten(), template_norm.flatten())
        norm_factor = np.sqrt(np.sum(template_norm**2) * np.sum(target_norm**2))
        normalized_cc = cross_corr / norm_factor
        return normalized_cc

    def screenshot(self):
        logging.debug("Taking a screenshot.")
        im = self.device.takeSnapshot(reconnect=True)  # PIL img
        return np.array(im)[:, :, :3]

    def index_to_pixel(self, tile):
        i, j = tile
        x_offset = 444
        y_offset = 205
        tile_height = 115.333
        tile_width = 115.25
        x = int(x_offset + tile_width * j + tile_width / 2)
        y = int(y_offset + tile_height * i + tile_height / 2)
        logging.debug("Tile %s converted to pixel coordinates (%s, %s)", tile, x, y)
        return x, y

    def is_empty(self, tile, img):
        x, y = self.index_to_pixel(tile)
        tile_color = img[y, x]
        return any((tile_color == color).all() for color in self.empty_colors)

    def find_match(self, target_tile, tiles, img):
        if not tiles:
            logging.debug("No tiles to match.")
            return False

        x, y = self.index_to_pixel(target_tile)
        target = img[
            y - self.offset : y + self.offset, x - self.offset : x + self.offset
        ]

        for match_tile in tiles:
            if self.is_empty(match_tile, img):
                continue

            x, y = self.index_to_pixel(match_tile)
            match = img[
                y - self.offset : y + self.offset, x - self.offset : x + self.offset
            ]

            coef = self.ccoeff_normed(match, target)
            logging.debug(
                "Correlation coefficient for tiles %s and %s: %s",
                target_tile,
                match_tile,
                coef,
            )
            if coef > self.threshold:
                logging.debug("Found a match for tile %s", target_tile)
                return match_tile

        logging.debug("No match found for tile %s", target_tile)
        return False

    def drag(self, match, tile):
        x, y = self.index_to_pixel(match)
        z, w = self.index_to_pixel(tile)
        logging.debug("Dragging from %s to %s", (x, y), (z, w))
        self.device.drag((x, y), (z, w), duration=100)

    def use_station(self, tile):
        x, y = self.index_to_pixel(tile)
        logging.info("Using station at tile %s", tile)
        self.device.touch(x, y)
        time.sleep(0.3)
        self.device.touch(x, y)
        return True

    def run(self):
        logging.debug("Start run")
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
                time.sleep(1)

            if self.uses == 0:
                logging.info("Station depleted, moving to next station.")
                self.station_tiles.pop(0)
                self.uses = self.station_uses

        time.sleep(0.3)
        return True


def start_bot():
    global bot
    try:
        bot_station_attempts = int(station_attempts_entry.get())
        bot_station_num = int(station_num_entry.get())
        bot_station_start = int(station_start_entry.get())
        rows = int(rows_entry.get())  # Get number of rows

        # start adb
        serial = "localhost:5555"
        adb_executable = os.path.join(os.getcwd(), "platform-tools", "adb")
        subprocess.check_output([adb_executable, "connect", serial])

        bot = Bot(bot_station_attempts, bot_station_num, bot_station_start, rows)

        bot.running = True
        disable_fields()

        while bot.running:
            if not bot.run():
                logging.warning("\nNo stations available, exiting Bot.")
                break
    except Exception as e:
        logging.error(f"Error occurred: {e}")
    finally:
        enable_fields()


def stop_bot():
    # Stop the bot by setting the running flag to False
    bot.running = False


def disable_fields():
    station_attempts_entry.config(state="disabled")
    station_num_entry.config(state="disabled")
    station_start_entry.config(state="disabled")
    rows_entry.config(state="disabled")  # Disable rows entry


def enable_fields():
    station_attempts_entry.config(state="disabled")
    station_num_entry.config(state="disabled")
    station_start_entry.config(state="disabled")
    rows_entry.config(state="normal")  # Enable rows entry


def show_info(title, message):
    messagebox.showinfo(title, message)


# GUI Setup
root = tk.Tk()
root.title("Bot Control")

# Adding margins by using a frame
main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack()

# Labels and Entries for the fields
tk.Label(main_frame, text="Station attempts").grid(row=0, column=0)
station_attempts_entry = tk.Entry(main_frame)
station_attempts_entry.grid(row=0, column=1)
tk.Button(
    main_frame,
    text="?",
    command=lambda: show_info(
        "Station attempts",
        "Enter the number of attempts the station can handle.",
    ),
).grid(row=0, column=2)

tk.Label(main_frame, text="Number of stations").grid(row=1, column=0)
station_num_entry = tk.Entry(main_frame)
station_num_entry.grid(row=1, column=1)
tk.Button(
    main_frame,
    text="?",
    command=lambda: show_info(
        "Number of stations", "Enter the total number of stations available."
    ),
).grid(row=1, column=2)

tk.Label(main_frame, text="Stations already used").grid(row=3, column=0)
station_start_entry = tk.Entry(main_frame)
station_start_entry.grid(row=3, column=1)
tk.Button(
    main_frame,
    text="?",
    command=lambda: show_info(
        "Stations already used",
        "Enter the number of stations you have already utilized.",
    ),
).grid(row=3, column=2)

tk.Label(main_frame, text="Number of rows").grid(row=4, column=0)
rows_entry = tk.Entry(main_frame)
rows_entry.grid(row=4, column=1)
tk.Button(
    main_frame,
    text="?",
    command=lambda: show_info(
        "Number of rows",
        "Enter how many rows are available for the items. Top to bottom.",
    ),
).grid(row=4, column=2)

# Add instruction text
instruction_label = tk.Label(
    main_frame, text="Please activate 'Batch Produce' in Flora's Craft Workshop."
)
instruction_label.grid(row=5, column=0, columnspan=3, pady=(10, 0))

# Start and Stop buttons
start_button = tk.Button(
    main_frame, text="Start", command=lambda: threading.Thread(target=start_bot).start()
)
start_button.grid(row=6, column=0)

stop_button = tk.Button(main_frame, text="Stop", command=stop_bot)
stop_button.grid(row=6, column=1)


# Setting default values if needed
station_attempts_entry.insert(0, "30")
station_num_entry.insert(0, "32")
station_start_entry.insert(0, "0")
rows_entry.insert(0, "3")  # Default value for number of rows

# Start the GUI event loop
root.mainloop()
