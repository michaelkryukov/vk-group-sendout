# Performing send outs for vk.com groups
### Installation
1. Install python 3.5 or greater (https://www.python.org/downloads/)   

### Usage
- Reads proxies from raw_proxies.txt and validates them. Result is saved to proxies.txt
```
python3 script.py proxies
```

- Uses proxies from proxies.txt and settings from `SETTINGS` section in `script.py` and performs send out.
```
python3 script.py
```

**WARNINGS:**
- thees examples are for execution in terminal
- python3 can be python or python3.6 on your system

### Example settings
```python
################################### SETTINGS ###################################


MESSAGE = "Привет. Проверка скрипта для рассылки.\nЯ поспамлю, прости ;)"
ATTACHMENT = "photo-145935681_456239429"

MINIMUM_MESSAGES_TO_SEND = 500
REPEAT = 1
REPEAT_PAUSE = 30
UPDATE_TARGET_USERS = True
OFFSET_FOR_TARGETS = 0

SEND_MESSAGES_AFTER_UNREAD = True

TOKENS = [
    "TOKEN_HERE"
]

PROXIES = [
    {}
]

ONE_SENDOUT_SIZE = 50


################################################################################
```

### Proxies
You can find proxies on internet for free or buy it. You can get a pack of proxies here: https://awmproxy.com/freeproxy.php

### Possible `configuration.py` file
You can create file `configuration.py` in same folder as `script.py` and settings in `script.py` will be overwritten by settings in `configuration.py`. `configuration.py` can consist only from settings (see `Example settings`).
