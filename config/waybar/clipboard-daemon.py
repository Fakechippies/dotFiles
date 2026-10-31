#!/usr/bin/env python3
import json, subprocess, time, os
HOME = os.path.expanduser("~")
CC_DIR = os.path.join(HOME, ".cache", "waybar-cc")
PATH = os.path.join(CC_DIR, "clipboard.json")
os.makedirs(CC_DIR, exist_ok=True)

def load():
    try:
        with open(PATH) as f:
            d = json.load(f)
        if isinstance(d, list):
            return d
    except Exception:
        pass
    return []

def save(lst):
    with open(PATH, "w") as f:
        json.dump(lst[:20], f)

def get_clip():
    try:
        return subprocess.check_output(["wl-paste", "--no-newline"], stderr=subprocess.DEVNULL).decode("utf-8", "replace")
    except Exception:
        return None

last = None
history = load()
while True:
    cur = get_clip()
    if cur is not None and cur.strip() != "":
        if cur != last:
            last = cur
            # dedupe
            history = [h for h in history if h != cur]
            history.insert(0, cur)
            save(history)
    time.sleep(1)
