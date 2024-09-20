import numpy as np
import mss
import time
import pyautogui
import keyboard
import logging
import configparser
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = 'bot_config.ini'

# Load config file or create it if it doesn't exist
def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        # Create default config if it doesn't exist
        config['DEFAULT'] = {
            'station_cap': '30',
            'station_num': '32',
            'station_uses': '10',
            'rows': '3',
            'x_offset': '493',
            'y_offset': '227',
            'tile_height': '104',
            'tile_width': '104',
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        logging.info(f"{CONFIG_FILE} created with default values.")
    else:
        config.read(CONFIG_FILE)
        logging.info(f"{CONFIG_FILE} loaded.")
    return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    logging.info(f"{CONFIG_FILE} updated.")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Bot:
    def __init__(self, station_cap, station_uses, station_num, rows, x_offset, y_offset, tile_height, tile_width):
        self.station_cap = station_cap
        self.station_uses = station_uses

        self.rows = rows
        self.cols = 9

        self.x_offset = x_offset
        self.y_offset = y_offset

        self.tile_height = tile_height
        self.tile_width = tile_width
       
        self.offset = 10 # 10 pixels around the center of the tile for matching purposes

        self.empty_colors = [np.array([179, 208, 234]), np.array([165, 190, 223])] # windows
        #self.empty_colors = [np.array([168, 191, 218]), np.array([182, 209, 230])] # mac os

        self.threshold = 0.8 # 0-1 range, closer to 1 means more strict matching

        self.item_tiles = [(i, j) for i in range(self.rows) for j in range(self.cols)]
        self.station_tiles = self.create_station_tiles(station_num)
        self.uses = self.station_cap // self.station_uses

        logging.info(f"Bot initialized with offsets: x={self.x_offset}, y={self.y_offset}")

    def create_station_tiles(self, station_num):
        station_tiles_blueprint = [(6 - i, j) for i in range(2) for j in range(7)] + \
                                  [(6 - i, j) for i in range(2, 4) for j in range(9)]
        return station_tiles_blueprint[:station_num]

    def ccoeff_normed(self, template, target):
        template_norm = (template - np.mean(template)) / np.std(template)
        target_norm = (target - np.mean(target)) / np.std(target)
        cross_corr = np.correlate(target_norm.flatten(), template_norm.flatten())
        norm_factor = np.sqrt(np.sum(template_norm ** 2) * np.sum(target_norm ** 2))
        normalized_cc = cross_corr / norm_factor
        return normalized_cc

    def screenshot(self):
        with mss.mss() as sct:
            monitor = {
                "top": self.y_offset,
                "left": self.x_offset,
                "width": self.tile_width * self.cols,
                "height": self.tile_height * self.rows
            }
            sct_img = sct.grab(monitor)
            img = np.asarray(sct_img)
            logging.info("Screenshot captured")
            return img[:, :, :3]

    def index_to_pixel(self, tile):
        i, j = tile
        return j * self.tile_width + self.tile_width // 2, \
               i * self.tile_height + self.tile_height // 2

    def index_to_screen_pixel(self, tile):
        i, j = tile
        return j * self.tile_width + self.tile_width // 2 + self.x_offset, \
               i * self.tile_height + self.tile_height // 2 + self.y_offset

    def is_empty(self, tile, img):
        x, y = self.index_to_pixel(tile)
        return any((img[y, x] == color).all() for color in self.empty_colors)

    def find_match(self, target_tile, tiles, img):
        if not tiles:
            return False

        x, y = self.index_to_pixel(target_tile)
        target = img[y - self.offset:y + self.offset, x - self.offset:x + self.offset]

        for match_tile in tiles:
            if self.is_empty(match_tile, img):
                continue

            x, y = self.index_to_pixel(match_tile)
            match = img[y - self.offset:y + self.offset, x - self.offset:x + self.offset]

            coef = self.ccoeff_normed(match, target)
            if coef > self.threshold:
                logging.info(f"Match found between {target_tile} and {match_tile}")
                return match_tile

        return False

    def drag(self, match, tile):
        x, y = self.index_to_screen_pixel(match)
        z, w = self.index_to_screen_pixel(tile)

        logging.info(f"Dragging item from {match} to {tile}")
        pyautogui.moveTo(x, y)
        pyautogui.dragTo(z, w, duration=0.1, button='left')

    def use_station(self, tile):
        x, y = self.index_to_screen_pixel(tile)
        pyautogui.moveTo(x, y)

        logging.info(f"Using station at {tile}")
        for _ in range(self.station_uses):
            if keyboard.is_pressed('q'):
                logging.info("Bot stopped by user input")
                return False

            pyautogui.click(button='left')
            pyautogui.click(button='left')
            time.sleep(0.025)
        return True

    def run(self):
        matched = False
        tiles = self.item_tiles.copy()
        img = self.screenshot()

        while tiles and not keyboard.is_pressed('q'):
            tile = tiles.pop(0)

            if self.is_empty(tile, img):
                continue

            match = self.find_match(tile, tiles, img)

            if match:
                matched = True
                self.drag(match, tile)
                tiles.remove(match)

        if not matched:
            if not self.station_tiles:
                logging.warning("No stations available, exiting Bot.")
                return False

            if self.use_station(self.station_tiles[0]):
                self.uses -= 1

            if self.uses == 0:
                self.station_tiles.pop(0)
                self.uses = self.station_cap // self.station_uses

        time.sleep(0.3)
        return True

if __name__ == "__main__":
    print('--- Bot by Ozuromo ---\n')
    # Load configuration
    config = load_config()

    # Default inputs
    station_cap = int(input(f'Station capacity (default: {config["DEFAULT"]["station_cap"]}): ').strip() or config["DEFAULT"]["station_cap"])
    station_num = int(input(f'Number of stations (default: {config["DEFAULT"]["station_num"]}): ').strip() or config["DEFAULT"]["station_num"])
    station_uses = int(config["DEFAULT"]["station_uses"])
    rows = int(config["DEFAULT"]["rows"])

    # User-defined offsets
    try:
        x_offset = int(input(f'X Offset (default: {config["DEFAULT"]["x_offset"]}): ').strip() or config["DEFAULT"]["x_offset"])
        y_offset = int(input(f'Y Offset (default: {config["DEFAULT"]["y_offset"]}): ').strip() or config["DEFAULT"]["y_offset"])
        tile_height = int(input(f'Tile Height (default: {config["DEFAULT"]["tile_height"]}): ').strip() or config["DEFAULT"]["tile_height"])
        tile_width = int(input(f'Tile Width (default: {config["DEFAULT"]["tile_width"]}): ').strip() or config["DEFAULT"]["tile_width"])
    except ValueError:
        logging.error("Invalid offset values, using default.")
        x_offset, y_offset = int(config["DEFAULT"]["x_offset"]), int(config["DEFAULT"]["y_offset"])
        tile_height, tile_width = int(config["DEFAULT"]["tile_height"]), int(config["DEFAULT"]["tile_width"])

    # Update the config file if new values are entered
    config["DEFAULT"]["station_cap"] = str(station_cap)
    config["DEFAULT"]["station_num"] = str(station_num)
    config["DEFAULT"]["x_offset"] = str(x_offset)
    config["DEFAULT"]["y_offset"] = str(y_offset)
    config["DEFAULT"]["tile_height"] = str(tile_height)
    config["DEFAULT"]["tile_width"] = str(tile_width)
    save_config(config)

    logging.info(f"Starting bot with station_cap={station_cap}, station_num={station_num}, x_offset={x_offset}, y_offset={y_offset}")

    print("\nPress 'q' to start/stop or 'ESC' to quit.\n")
    print("--- --- --- --- --- ---\n")

    bot = Bot(station_cap, station_uses, station_num, rows, x_offset, y_offset, tile_height, tile_width)

    running = False
    while not keyboard.is_pressed('esc'):
        if keyboard.is_pressed('q'):
            running = not running
            if running:
                logging.info("Bot running.")
            else:
                logging.info("Bot paused.")
            time.sleep(2)
        if running:
            if not bot.run():
                logging.info("No stations available, exiting Bot.")
                break