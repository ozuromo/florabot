import logging
from com.dtmilano.android.viewclient import ViewClient
import time
import os
import numpy as np
import subprocess

# Function to configure logging based on user input
def setup_logging():
    enable_logging = input('Do you want to enable logging? (y/n): ').strip().lower()
    if enable_logging == 'y':
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("Logging is enabled.")
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
        self.empty_colors = [np.array([223, 190, 165]), np.array([234, 208, 179])]
        self.threshold = 0.91
        self.item_tiles = [(i, j) for i in range(self.rows) for j in range(self.cols)]
        self.station_tiles = self.create_station_tiles(station_start, station_num)
        self.uses = self.station_cap // self.station_uses

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
        is_empty = any((img[y, x] == color).all() for color in self.empty_colors)
        logging.debug("Tile %s is empty: %s", tile, is_empty)
        return is_empty

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
        for _ in range(self.station_uses):
            time.sleep(.4)
            self.device.touch(x, y)
        return True

    def run(self):
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

if __name__ == "__main__":
    setup_logging()
    
    logging.info('--- Bot by Ozuromo ---\n')   

    station_cap = int(input('Station capacity: ').strip() or "30")
    station_num = int(input('Number of stations: ').strip() or "32")
    station_uses = int(input('Number of clicks/loop: ').strip() or "10")
    station_start = int(input('Stations already used: ').strip() or "0")
    rows = int(input('Number of rows to be used: ').strip() or "3")

    logging.info("\nPress 'Ctrl+C' to stop the Bot.\n")

    # start adb
    serial = 'localhost:5555'
    adb_path = os.path.join(os.getcwd(), 'platform-tools')
    subprocess.check_output(['adb', 'connect', serial], cwd=adb_path, shell=True)

    bot = Bot(station_cap, station_uses, station_num, station_start, rows)
    
    try:
        while True:
            if not bot.run():
                logging.warning('\nNo stations available, exiting Bot.')
                break
    except KeyboardInterrupt:
        logging.info('\nBot stopped.')
    finally:
        os._exit(0)
