# FloraBot
Bot for Flora's Workshop on Idle Heroes, made by me.

If you want to donate some SG my in-game id is: 111352605190.

Demo video: https://www.youtube.com/watch?v=dJXlgxsMnc0

ADB Files: https://developer.android.com/tools/releases/platform-tools

# Installation
Install python then run the following command:
```
pip install numpy androidviewclient
```
Download "bot_adb.py" and place it in a folder. 

Download the ADB Files and unzip "platform-tools" at the same folder your "bot_adb.py" file is.

# Usage
Make sure you activate the ADB server on Bluestack's Advanced Settings before you do anything.

Use 1920x1080 resolution on Bluestack.

Your Flora's House should be at the bottom right corner, and your stations should be organized bottom->top left->right.

On the folder where "bot_adb.py" is, open a Terminal screen and use the following commnand:
```
python bot_adb.py
```
Press CTRL+C to stop the Bot anytime.

# Settings

*Station capacity* should be the cap your production item has (for example 30 for lv8 sewing machines), if it's not doing all 30 try increasing the delay on line 98 (use_station). The default value is 30.

*Number of stations* is how many stations you have, for example 32 for 4 rows of sewing machines. The default value is 32.

*Number of clicks/loop* is how many times the bot will click the station each loop, for example if you use 10 clicks/loop it will take 3 loops to do the 30 clicks capacity of a lv8 sewing machine. The default value is 10.

*Stations already used* is how many stations you already used, this is useful if you stop the bot mid-run so you can set to like 8 and it will skip the first 8 machines. The default value is 0.

*Number of rows* is how many rows you have available for items, for example 3 rows, because if you use 4 rows of sewing machines that leaves you with 3 rows for the clothing items. The default value is 3.

