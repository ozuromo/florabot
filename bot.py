import numpy as np
import mss
import time
import pyautogui
import keyboard

class Bot:
    def __init__(self, station_cap, station_uses, station_num, rows):
        self.station_cap = station_cap
        self.station_uses = station_uses

        self.rows = rows
        self.cols = 9

        self.x_offset = 493
        self.y_offset = 227
        self.tile_height = 104
        self.tile_width = 104
        self.offset = 10

        self.empty_colors = [np.array([179, 208, 234]), np.array([165, 190, 223])]

        self.threshold = 0.9

        self.item_tiles = [(i, j) for i in range(self.rows) for j in range(self.cols)]
        self.station_tiles = self.create_station_tiles(station_num)
        self.uses = self.station_cap // self.station_uses

    def create_station_tiles(self, station_num):
        station_tiles_blueprint = [(6-i, j) for i in range(2) for j in range(7)] +\
            [(6-i, j) for i in range(2, 4) for j in range(9)]

        return station_tiles_blueprint[:station_num]


    def ccoeff_normed(self, template, target):
        template_norm = (template - np.mean(template)) / np.std(template)
        target_norm = (target - np.mean(target)) / np.std(target)
        
        cross_corr = np.correlate(target_norm.flatten(), template_norm.flatten())
        
        norm_factor = np.sqrt(np.sum(template_norm**2) * np.sum(target_norm**2))
        normalized_cc = cross_corr / norm_factor
        
        return normalized_cc

    def screenshot(self):
        with mss.mss() as sct:
            monitor = {
                "top"   : self.y_offset, 
                "left"  : self.x_offset, 
                "width" : self.tile_width * self.cols, 
                "height": self.tile_height * self.rows
            }
            sct_img = sct.grab(monitor)
            img = np.asarray(sct_img)
            return img[:, :, :3]

    def index_to_pixel(self, tile):
        i, j = tile
        return j * self.tile_width + self.tile_width // 2,\
            i * self.tile_height + self.tile_height // 2

    def index_to_screen_pixel(self, tile):
        i, j = tile
        return j * self.tile_width + self.tile_width // 2 + self.x_offset,\
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
                return match_tile
            
        return False

    def drag(self, match, tile):
        x, y = self.index_to_screen_pixel(match)
        z, w = self.index_to_screen_pixel(tile)

        pyautogui.moveTo(x, y)
        pyautogui.mouseDown(button='left')
        pyautogui.moveTo(z, w)
        pyautogui.mouseUp(button='left')

        time.sleep(0.1) # too fast and it does not work

    def use_station(self, tile):
        x, y = self.index_to_screen_pixel(tile)
        pyautogui.moveTo(x, y)

        for _ in range(self.station_uses):
            if keyboard.is_pressed('q'):
                return False

            pyautogui.mouseDown(button='left')
            pyautogui.mouseUp(button='left')
            pyautogui.mouseDown(button='left')
            pyautogui.mouseUp(button='left')
            time.sleep(0.025) # too fast and it does not work
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
                return False

            if self.use_station(self.station_tiles[0]):
                self.uses -= 1
            
            if self.uses == 0:
                self.station_tiles.pop(0)
                self.uses = self.station_cap // self.station_uses

        time.sleep(0.3) # wait before next screenshot so effect from fusing vanishes
        return True

if __name__ == "__main__":
    print('--- Bot by Ozuromo ---\n')

    station_cap = int(input('Station capacity (default: 30): ').strip() or "30")
    station_num = int(input('Number of stations (default: 32): ').strip() or "32")
    station_uses = 10
    rows = 3

    print("\nPress 'q' to start/stop or 'ESC' to quit.\n")
    print("--- --- --- --- --- ---\n")

    bot = Bot(station_cap, station_uses, station_num, rows)
    
    running = False
    while not keyboard.is_pressed('esc'):
        if keyboard.is_pressed('q'):
            running = not running

            if running:
                print('Bot running.')
            else:
                print('Bot paused.')
            time.sleep(5)

        if running:
            if not bot.run():
                print('No stations available, exiting Bot.')
                break

