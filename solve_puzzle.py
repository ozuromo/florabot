from com.dtmilano.android.viewclient import ViewClient
import time
import os
import numpy as np
import subprocess
import matplotlib.pyplot as plt

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

    def ccoeff_normed(target, match):
        target_norm = (target - np.mean(target)) / np.std(target)
        match_norm  = (match  -  np.mean(match)) /  np.std(match)

        cross_corr = np.correlate(target_norm.flatten(), match_norm.flatten())
        norm_factor = np.sqrt(np.sum(target_norm**2) * np.sum(match_norm**2))

        normalized_cc = cross_corr / norm_factor

        # print(normalized_cc)
        return normalized_cc

    def open_puzzle():
        def click_visit():
            x, y = 1820, 70
            device.touch(x, y)

        def click_glove():
            x, y = 750, 340
            device.touch(x, y)

        def click_matching():
            x, y = 960, 850
            device.touch(x, y)

        def click_confirm():
            x, y = 960, 760
            device. touch(x, y)

        clicks = [
            click_visit,
            #click_glove,
            click_matching,
            click_confirm
        ]
        
        for click in clicks:
            click()
            time.sleep(.3)

    def solve_puzzle():
        cards_idxs = [(i, j) for i in range(4) for j in range(4)]
        cards_imgs = []

        def click_idx(idx):
            x, y = idx_to_pixel(idx)
            device.touch(x, y)

        def idx_to_pixel(idx):
            i, j = idx
            x_offset, y_offset = 644, 282
            w, h = 164.33, 164.66
            x, y = x_offset + j*w + w/2, y_offset + i*h + h/2
            return  int(x), int(y)
        
        
        def get_card(idx):
            x, y = idx_to_pixel(idx)
            offset = 10
            
            click_idx(idx)
            time.sleep(0.6)

            img = screenshot()
            card = img[y - offset:y + offset, x - offset:x + offset]
            return card

        def save_cards():
            for card_idx in cards_idxs:
                card = get_card(card_idx)
                cards_imgs.append(card)

        def find_match(target):
            max_idx = 0
            max_coef = 0
            for match, idx in zip(cards_imgs, cards_idxs):
                coef = ccoeff_normed(target, match)
                if coef > max_coef:
                    max_idx = idx
                    max_coef = coef
            print(max_coef)
            return max_idx

        def solve():
            while cards_imgs:
                card_img = cards_imgs.pop(0)
                card_idx = cards_idxs.pop(0)

                if not (match_idx := find_match(card_img)):
                    print("Match not found, something's wrong!")
                    return
                
                idx = cards_idxs.index(match_idx)
                cards_idxs.pop(idx)
                cards_imgs.pop(idx)

                
                click_idx(card_idx)
                time.sleep(.3)
                click_idx(match_idx)
                time.sleep(.3)

        save_cards()
        time.sleep(1)
        solve()
    
    def run():
        def click_confirm():
            x, y = 960, 960
            device.touch(x, y)

        open_puzzle()
        solve_puzzle()

        time.sleep(1)
        click_confirm()

    return run

if __name__ == "__main__":
    serial = 'localhost:5555'
    adb_path = os.path.join(os.getcwd(), 'platform-tools')
    subprocess.check_output(['adb', 'connect', serial], cwd=adb_path, shell=True)
    device, serialno = ViewClient.connectToDeviceOrExit(verbose=True)

    run = Bot()

    print("> Made by Ozuromo <")

    try:
        while True:
            run()
    except KeyboardInterrupt:
        print('\nBot stopped.')
