#!/usr/bin/env python3
import json, subprocess, time, os, hashlib
HOME = os.path.expanduser("~")
CC_DIR = os.path.join(HOME, ".cache", "waybar-cc")
IMG_DIR = os.path.join(CC_DIR, "clipimg")
PATH = os.path.join(CC_DIR, "clipboard.json")
os.makedirs(CC_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

def load():
    try:
        with open(PATH) as f:
            d = json.load(f)
        if isinstance(d, list):
            out = []
            for h in d:
                if isinstance(h, str):
                    out.append({"type": "text", "text": h})
                else:
                    out.append(h)
            return out
    except Exception:
        pass
    return []

def save(lst):
    with open(PATH, "w") as f:
        json.dump(lst[:20], f)

def types():
    try:
        return subprocess.check_output(["wl-paste", "--list-types"], stderr=subprocess.DEVNULL).decode().splitlines()
    except Exception:
        return []

def get_text():
    try:
        return subprocess.check_output(["wl-paste", "--no-newline"], stderr=subprocess.DEVNULL).decode("utf-8", "replace")
    except Exception:
        return None

def save_image(mime):
    # pick png if available else first image type
    t = "image/png" if "image/png" in mime else mime[0]
    ts = int(time.time()*1000)
    path = os.path.join(IMG_DIR, "clip_%d.png" % ts)
    try:
        with open(path, "wb") as f:
            subprocess.run(["wl-paste", "--type", t], stdout=f, stderr=subprocess.DEVNULL, check=True)
        if os.path.getsize(path) > 0:
            return path
    except Exception:
        pass
    try:
        os.remove(path)
    except Exception:
        pass
    return None

last_sig = None
history = load()
while True:
    m = types()
    img_types = [t for t in m if t.startswith("image/")]
    entry = None
    if img_types:
        p = save_image(img_types)
        if p:
            entry = {"type": "image", "path": p}
    else:
        txt = get_text()
        if txt is not None and txt.strip() != "":
            entry = {"type": "text", "text": txt}
    if entry is not None:
        # signature
        if entry["type"] == "text":
            sig = "text:" + entry["text"]
        else:
            sig = "img:" + entry["path"]
        if sig != last_sig:
            last_sig = sig
            # dedupe
            if entry["type"] == "text":
                history = [h for h in history if not ((isinstance(h, dict) and h.get("type") == "text" and h.get("text") == entry["text"]) or (isinstance(h, str) and h == entry["text"]))]
            else:
                history = [h for h in history if not (isinstance(h, dict) and h.get("type") == "image" and h.get("path") == entry["path"])]
            history.insert(0, entry)
            save(history)
    time.sleep(1)
