from com.dtmilano.android.viewclient import ViewClient
import time
import os
import numpy as np
import subprocess
import matplotlib.pyplot as plt

def Sell():
    def screenshot(save_img = False):
        img = device.takeSnapshot(reconnect=True) # PIL img
        if save_img:
            img.save('im.png', 'PNG')
        return np.array(img)[:, :, :3] # remove alpha
    
    def show_img(img):
        plt.axis("off")
        plt.imshow(img)
        plt.show()

    def ccoeff_normed(target, match):
        target_norm = (target - np.mean(target)) / np.std(target)
        match_norm  = (match  -  np.mean(match)) /  np.std(match)

        cross_corr = np.correlate(target_norm.flatten(), match_norm.flatten())
        norm_factor = np.sqrt(np.sum(target_norm**2) * np.sum(match_norm**2))

        normalized_cc = cross_corr / norm_factor

        # print(normalized_cc)
        return normalized_cc


    def click_idx(idx):
        x, y = idx_to_pixel(idx)
        device.touch(x, y)

    def idx_to_pixel(idx):
        i, j = idx
        x_offset, y_offset = 444, 205
        w, h = 115.25, 115.333
        x, y = x_offset + j*w + w/2, y_offset + i*h + h/2
        return  int(x), int(y)
    
    def is_empty(img):
        empty_colors = [np.array([223, 190, 165]), np.array([234, 208, 179])]
        y, x = img.shape[:2]
        return any((img[y//2, x//2] == color).all() for color in empty_colors)

    
    def get_item(idx, img):
        x, y = idx_to_pixel(idx)
        offset = 10

        item = img[y - offset:y + offset, x - offset:x + offset]
        return item
    
    def sell_item(idx):
        click_idx(idx)
        time.sleep(.2)
        device.touch(1680, 920) # sell button
        time.sleep(.2)
        device.touch(1100, 710) # yes button
        time.sleep(.2)
        pass

    def check_items():
        img = screenshot()
        for i in range(1, 3):
            for j in range(9):
                item = get_item((i, j), img)
                if is_empty(item): continue
                if not find_match(item, ns_list):
                    sell_item((i, j))

    def find_match(target, ns_list):
        threshold = .8
        for item in ns_list:
            if ccoeff_normed(target, item) > threshold:
                return True
        return False

    def not_sell():
        n = 9
        img = screenshot()
        ns_list = []
        for x in range(n):
            item = get_item((0, x), img)
            if is_empty(item): continue
            ns_list.append(item)
            # show_img(ns_list[i])
        return ns_list

    def sell():
        check_items()

    ns_list = not_sell()
    return sell

def Bot():
    def screenshot(save_img = False):
        img = device.takeSnapshot(reconnect=True) # PIL img
        if save_img:
            img.save('im.png', 'PNG')
        return np.array(img)[:, :, :3] # remove alpha
    
    def show_img(img):
        plt.axis("off")
        plt.imshow(img)
        plt.show()

    def click_visit():
        x, y = 1820, 70
        device.touch(x, y)

    def click_cube():
        x, y = 950, 340
        device.touch(x, y)

    def click_matching():
        x, y = 960, 850
        device.touch(x, y)

    def click_confirm():
        x, y = 960, 760
        device.touch(x, y)

    def click_slots():
        x_offset, y_offset = 506, 168
        w, h = 101, 101

        i = 0
        for j in range(7):
            x, y = x_offset + j*w + w/2, y_offset + i*h + h/2
            device.touch(x, y)
            time.sleep(.1)   
        device.touch(950, 950)
        time.sleep(.2)
        device.touch(950, 950)

    def use_cube():
        clicks = [
            click_visit,
            click_cube,
            click_matching,
            click_confirm,
            click_slots,
        ]
        
        for click in clicks:
            click()
            time.sleep(.3)

    return use_cube

if __name__ == "__main__":
    serial = 'localhost:5555'
    subprocess.check_output(['adb', 'connect', serial], shell=True)
    device, serialno = ViewClient.connectToDeviceOrExit(verbose=True)

    use_cube = Bot()
    sell = Sell()

    print("> Made by Ozuromo <")
    n = int(input("How many cubes you want to use? "))

    try:
        for _ in range(n):
            use_cube()
            sell()
    except KeyboardInterrupt:
        print('\nBot stopped.')
