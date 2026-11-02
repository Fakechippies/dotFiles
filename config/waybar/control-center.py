#!/usr/bin/env python3
import os, sys, json, subprocess, signal, time, urllib.request, tempfile, threading

HOME = os.path.expanduser("~")
CC_DIR = os.path.join(HOME, ".cache", "waybar-cc")
PIDFILE = os.path.join(CC_DIR, "cc.pid")
os.makedirs(CC_DIR, exist_ok=True)

def is_running():
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None

existing = is_running()
if existing and existing != os.getpid():
    try:
        os.kill(existing, signal.SIGTERM)
    except Exception:
        pass
    sys.exit(0)

with open(PIDFILE, "w") as f:
    f.write(str(os.getpid()))

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf, GtkLayerShell

ORANGE = "#ff6a00"
BLACK = "#0d0d0d"
SURF = "#1a1a1a"
BORDER = "#2a2a2a"
TEXT = "#e8e8e8"
MUTED = "#8a8a8a"

CSS = """
window.cc { background-image: none; background-color: #0d0d0d; color: #e8e8e8; font-family: 'JetBrainsMono Nerd Font'; }
.cc-box { background-image: none; background-color: #0d0d0d; border: 2px solid #ff6a00; border-radius: 0; padding: 8px; }
.card { background-image: none; background-color: transparent; border: none; border-radius: 0; padding: 6px 0; margin: 0; }
.row { margin-bottom: 4px; }
.sep { background-color: #ff6a00; min-height: 1px; margin: 2px 0; }
.icon-btn { min-width: 36px; min-height: 36px; padding: 0; border-radius: 0; font-size: 16px; background-image: none; box-shadow: none; text-shadow: none; }
.icon-btn.on { background-image: none; background-color: #ff6a00; color: #1a1a1a; border: 1px solid #ff6a00; }
.icon-btn.off { background-image: none; background-color: #0d0d0d; color: #8a8a8a; border: 1px solid #2a2a2a; }
.mute-btn { padding-left: 0; padding-right: 4px; }
.text-btn { background-image: none; box-shadow: none; text-shadow: none; background-color: #0d0d0d; border: 1px solid #2a2a2a; border-radius: 0; padding: 4px 8px; color: #e8e8e8; }
.text-btn:hover { background-image: none; background-color: #1a1a1a; }
.title { color: #e8e8e8; font-size: 12px; font-weight: 700; }
.sub { color: #8a8a8a; font-size: 11px; }
.accent { color: #ff6a00; }
.muted { color: #8a8a8a; font-size: 11px; }
.val { color: #e8e8e8; font-size: 12px; }
button { background-image: none; box-shadow: none; text-shadow: none; background-color: #0d0d0d; color: #e8e8e8; border: 1px solid #2a2a2a; border-radius: 0; padding: 2px 6px; font-size: 11px; }
button:hover { background-image: none; background-color: #1a1a1a; color: #ffffff; }
button:active, button:checked { background-image: none; background-color: #ff6a00; color: #ffffff; }
button.ctrl { min-width: 30px; min-height: 30px; padding: 0; border-radius: 0; }
scale { background-color: transparent; background-image: none; }
scale trough { background-image: none; box-shadow: none; background-color: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 0; min-height: 3px; }
scale highlight { background-image: none; box-shadow: none; background-color: #ff8c00; border-radius: 0; }
scale slider { background-image: none; box-shadow: none; background-color: #ff8c00; border: 1px solid #ff8c00; min-width: 12px; min-height: 12px; border-radius: 0; }
scale value { color: #e8e8e8; }
.tab-btn { padding: 5px 12px; border-radius: 0; }
.tab-btn.active { background-color: #ff6a00; color: #1a1a1a; font-weight: 700; }
.list-row { padding: 4px 2px; border-bottom: 1px solid #1f1f1f; }
"""

def run(cmd, shell=True):
    try:
        if shell:
            return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return ""

def sh(cmd):
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---------- data ----------
def wifi_status():
    radio = run("nmcli -t -f WIFI g").lower()
    on = radio == "enabled"
    ssid = ""
    if on:
        out = run("nmcli -t -f NAME,TYPE connection show --active")
        for line in out.splitlines():
            parts = line.rsplit(":", 1)
            if len(parts) == 2 and parts[1] == "802-11-wireless":
                ssid = parts[0]; break
    return on, (ssid if ssid else ("Connected" if on else "Off"))

def bt_status():
    out = run("bluetoothctl show")
    powered = "Powered: yes" in out
    name = "Off"
    if powered:
        dev = run("bluetoothctl devices Connected")
        lines = [l for l in dev.splitlines() if l.strip()]
        if lines:
            name = lines[0].split(" ", 2)[-1]
        else:
            name = "On (no device)"
    return powered, name

def battery_info():
    cap = run("cat /sys/class/power_supply/BAT1/capacity")
    status = run("cat /sys/class/power_supply/BAT1/status")
    return cap, status

def brightness_get():
    out = run("brightnessctl -m")
    parts = out.split(",")
    if len(parts) >= 4:
        try:
            return int(parts[3].strip().rstrip("%"))
        except Exception:
            try:
                cur = int(parts[2]); mx = int(parts[4])
                return int(cur * 100 / mx) if mx else 0
            except Exception:
                return 0
    return 0

def brightness_set(pct):
    sh("brightnessctl set %d%%" % pct)

def volume_get():
    vol = run("pamixer --get-volume")
    mute = run("pamixer --get-mute")
    try: v = int(vol)
    except: v = 0
    return v, (mute.lower() == "true")

def volume_set(v):
    sh("pamixer --set-volume %d" % v)

def mute_toggle():
    sh("pamixer -t")

def wifi_toggle(on):
    sh("nmcli radio wifi %s" % ("on" if on else "off"))

def bt_toggle(on):
    sh("bluetoothctl power %s" % ("on" if on else "off"))

def notifications_list():
    out = run("makoctl history -j")
    try: data = json.loads(out) if out else []
    except: data = []
    items = []
    for n in data[:5]:
        app = n.get("app-name") or n.get("app_name") or ""
        summary = n.get("summary") or ""
        body = n.get("body") or ""
        items.append((app, summary, body))
    return items

def clipboard_list():
    path = os.path.join(CC_DIR, "clipboard.json")
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list): return data[:20]
    except: pass
    return []

def media_info():
    status = run("playerctl status")
    if not status or status.lower() in ("no players found", ""):
        return None
    title = run("playerctl metadata title") or "Unknown"
    artist = run("playerctl metadata artist") or ""
    art = run("playerctl metadata mpris:artUrl")
    player = run("playerctl metadata --format '{{playerName}}'") or "player"
    return {"status": status, "title": title, "artist": artist, "art": art, "player": player}

def load_pixbuf(url, size=56):
    if not url: return None
    path = url
    if url.startswith("http"):
        try:
            fd, tmp = tempfile.mkstemp(suffix=".img")
            os.close(fd)
            urllib.request.urlretrieve(url, tmp)
            path = tmp
        except Exception:
            return None
    elif url.startswith("file://"):
        path = url[7:]
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
        return pb
    except Exception:
        return None

# ---------- UI ----------
class ControlCenter(Gtk.Window):
    def __init__(self):
        super().__init__(title="Control Center")
        self.set_name("cc")
        self.get_style_context().add_class("cc")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)
        self.set_default_size(360, -1)

        # anchor as a top-right layer-shell popup
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 8)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 8)
        GtkLayerShell.set_namespace(self, "control-center")
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.get_style_context().add_class("cc-box")
        self.add(outer)

        # top row: wifi + bluetooth
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top.set_homogeneous(True)
        top.get_style_context().add_class("row")
        self.wifi_card = self.make_toggle_card("󰖩", "WIFI", "...", self.on_wifi_toggle, lambda: sh("nm-connection-editor"))
        self.bt_card = self.make_toggle_card("󰂯", "BLUETOOTH", "...", self.on_bt_toggle, lambda: sh("blueman-manager"))
        top.pack_start(self.wifi_card["box"], True, True, 0)
        top.pack_start(self.bt_card["box"], True, True, 0)
        outer.pack_start(top, False, False, 0)
        outer.pack_start(self.make_sep(), False, False, 0)

        # media
        self.media_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.media_box.get_style_context().add_class("card")
        outer.pack_start(self.media_box, False, False, 0)
        outer.pack_start(self.make_sep(), False, False, 0)

        # brightness
        br_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        br_card.get_style_context().add_class("card")
        br_lbl = Gtk.Label(label="BRIGHTNESS")
        br_lbl.set_halign(Gtk.Align.START); br_lbl.get_style_context().add_class("muted")
        br_card.pack_start(br_lbl, False, False, 0)
        self.br_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.br_scale.set_draw_value(True); self.br_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.br_scale.connect("value-changed", self.on_br_changed)
        br_card.pack_start(self.br_scale, False, False, 0)
        outer.pack_start(br_card, False, False, 0)

        # volume
        vol_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vol_card.get_style_context().add_class("card")
        vol_lbl = Gtk.Label(label="VOLUME")
        vol_lbl.set_halign(Gtk.Align.START); vol_lbl.get_style_context().add_class("muted")
        vol_card.pack_start(vol_lbl, False, False, 0)
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_draw_value(True); self.vol_scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.vol_scale.connect("value-changed", self.on_vol_changed)
        hb.pack_start(self.vol_scale, True, True, 0)
        self.mute_btn = Gtk.Button()
        self.mute_btn.get_style_context().add_class("icon-btn")
        self.mute_btn.get_style_context().add_class("mute-btn")
        self.mute_btn.set_size_request(36, 36)
        self.mute_btn.set_hexpand(False)
        self.mute_btn.set_halign(Gtk.Align.CENTER)
        ch = self.mute_btn.get_child()
        if isinstance(ch, Gtk.Label):
            ch.set_xalign(0.5); ch.set_yalign(0.5)
        self.mute_btn.connect("clicked", lambda *_: (mute_toggle(), GLib.timeout_add(200, self.refresh_volume)))
        hb.pack_end(self.mute_btn, False, False, 0)
        vol_card.pack_start(hb, False, False, 0)
        outer.pack_start(vol_card, False, False, 0)

        # tabs
        tab_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tab_card.get_style_context().add_class("card")
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.tab_notif = Gtk.Button(label="Notifications")
        self.tab_clip = Gtk.Button(label="Clipboard")
        self.tab_notif.get_style_context().add_class("tab-btn")
        self.tab_clip.get_style_context().add_class("tab-btn")
        self.tab_notif.connect("clicked", lambda *_: self.show_tab("notif"))
        self.tab_clip.connect("clicked", lambda *_: self.show_tab("clip"))
        hb.pack_start(self.tab_notif, True, True, 0)
        hb.pack_start(self.tab_clip, True, True, 0)
        tab_card.pack_start(hb, False, False, 0)
        self.list_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(40)
        scrolled.set_max_content_height(200)
        scrolled.add(self.list_container)
        tab_card.pack_start(scrolled, False, False, 0)
        outer.pack_start(tab_card, False, False, 0)

        self.current_tab = "notif"
        self.tab_notif.get_style_context().add_class("active")
        self._art_cache = {}
        self._art_pending = set()
        self._media_sig = None
        self._media_img = None
        self._media_art_url = None

        self.refresh_media()
        self.show_all()
        self.refresh_all()
        GLib.timeout_add(2000, self.refresh_all)
        GLib.timeout_add(3000, self.refresh_media)

    def make_sep(self):
        b = Gtk.Box()
        b.set_size_request(-1, 1)
        b.get_style_context().add_class("sep")
        return b

    def make_toggle_card(self, icon, title, sub, on_toggle, on_open):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.get_style_context().add_class("card")
        ib = Gtk.Button(label=icon)
        ib.get_style_context().add_class("icon-btn")
        ib.set_size_request(36, 36)
        ib.set_valign(Gtk.Align.CENTER)
        child = ib.get_child()
        if isinstance(child, Gtk.Label):
            child.set_xalign(0.5)
            child.set_yalign(0.5)
        ib.connect("clicked", lambda *_: on_toggle())
        box.pack_start(ib, False, False, 0)
        tb = Gtk.Button()
        tb.get_style_context().add_class("text-btn")
        tb.connect("clicked", lambda *_: on_open())
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        t = Gtk.Label(label=title); t.set_halign(Gtk.Align.START); t.get_style_context().add_class("title")
        s = Gtk.Label(label=sub); s.set_halign(Gtk.Align.START); s.get_style_context().add_class("sub")
        s.set_ellipsize(Pango.EllipsizeMode.END)
        s.set_max_width_chars(16)
        s.set_xalign(0.0)
        inner.pack_start(t, False, False, 0)
        inner.pack_start(s, False, False, 0)
        tb.add(inner)
        box.pack_start(tb, True, True, 0)
        return {"box": box, "icon_btn": ib, "sub_label": s, "title": title}

    def on_wifi_toggle(self):
        on, _ = wifi_status()
        wifi_toggle(not on)
        GLib.timeout_add(400, self.refresh_wifi)

    def on_bt_toggle(self):
        powered, _ = bt_status()
        bt_toggle(not powered)
        GLib.timeout_add(400, self.refresh_bt)

    def on_br_changed(self, scale):
        if getattr(self, "_br_lock", False): return
        brightness_set(int(scale.get_value()))

    def on_vol_changed(self, scale):
        if getattr(self, "_vol_lock", False): return
        volume_set(int(scale.get_value()))

    def refresh_wifi(self):
        on, ssid = wifi_status()
        self.wifi_card["sub_label"].set_text(ssid)
        ib = self.wifi_card["icon_btn"]
        ctx = ib.get_style_context()
        ctx.remove_class("on"); ctx.remove_class("off")
        ctx.add_class("on" if on else "off")
        return False

    def refresh_bt(self):
        powered, name = bt_status()
        self.bt_card["sub_label"].set_text(name)
        ib = self.bt_card["icon_btn"]
        ctx = ib.get_style_context()
        ctx.remove_class("on"); ctx.remove_class("off")
        ctx.add_class("on" if powered else "off")
        return False

    def refresh_volume(self):
        self._vol_lock = True
        v, muted = volume_get()
        self.vol_scale.set_value(v)
        self.mute_btn.set_label("\uf026" if muted else "\uf028")
        ch = self.mute_btn.get_child()
        if isinstance(ch, Gtk.Label):
            ch.set_xalign(0.5); ch.set_yalign(0.5)
        ctx = self.mute_btn.get_style_context()
        ctx.remove_class("on"); ctx.remove_class("off")
        ctx.add_class("on" if muted else "off")
        self._vol_lock = False
        return False

    def copy_text(self, txt):
        try:
            subprocess.run(["wl-copy"], input=txt.encode("utf-8"), check=False)
        except Exception:
            pass

    def copy_image(self, path):
        try:
            with open(path, "rb") as f:
                subprocess.run(["wl-copy", "--type", "image/png"], stdin=f, check=False)
        except Exception:
            pass

    def media_cmd(self, cmd):
        sh(cmd)
        GLib.timeout_add(250, self.refresh_media)
        GLib.timeout_add(900, self.refresh_media)

    def get_art(self, url):
        if not url:
            return None
        if url in self._art_cache:
            return self._art_cache[url]
        if url not in self._art_pending:
            self._art_pending.add(url)
            def worker():
                pb = load_pixbuf(url, 56)
                GLib.idle_add(self._art_loaded, url, pb)
            threading.Thread(target=worker, daemon=True).start()
        return None

    def _art_loaded(self, url, pb):
        self._art_pending.discard(url)
        if pb:
            self._art_cache[url] = pb
            if url == self._media_art_url and self._media_img is not None:
                self._media_img.set_from_pixbuf(pb)
                self._media_img.show()
        return False

    def refresh_media(self):
        info = media_info()
        if not info:
            info = {"title": "Nothing playing", "artist": "", "player": "media", "art": "", "status": "Stopped"}
        sig = (info["title"], info["artist"], info["art"], info["player"], info["status"])
        if sig == self._media_sig:
            return True
        self._media_sig = sig

        for c in self.media_box.get_children():
            self.media_box.remove(c)

        # layout: left text+controls, right art
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        t = Gtk.Label(label=info["title"]); t.set_halign(Gtk.Align.START)
        t.get_style_context().add_class("title")
        left.pack_start(t, False, False, 0)
        sub = "%s  ·  %s" % (info["artist"], info["player"]) if info["artist"] else info["player"]
        s = Gtk.Label(label=sub); s.set_halign(Gtk.Align.START); s.get_style_context().add_class("sub")
        left.pack_start(s, False, False, 0)
        cb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        playing = info["status"].lower() == "playing"
        mid_icon = "\uf04c" if playing else "\uf04b"  # fa-pause / fa-play
        for lbl, cmd in [("\uf04a", "playerctl previous"), (mid_icon, "playerctl play-pause"), ("\uf04e", "playerctl next")]:
            b = Gtk.Button(label=lbl); b.get_style_context().add_class("ctrl")
            b.set_size_request(30, 30)
            ch = b.get_child()
            if isinstance(ch, Gtk.Label):
                ch.set_xalign(0.5); ch.set_yalign(0.5)
            b.connect("clicked", lambda _, c=cmd: self.media_cmd(c))
            cb.pack_start(b, False, False, 0)
        left.pack_start(cb, False, False, 0)
        hb.pack_start(left, True, True, 0)
        # art on right (cached / async)
        img = Gtk.Image()
        img.set_size_request(56, 56)
        pb = self.get_art(info["art"])
        if pb:
            img.set_from_pixbuf(pb)
        self._media_img = img
        self._media_art_url = info["art"]
        hb.pack_end(img, False, False, 0)
        self.media_box.pack_start(hb, False, False, 0)
        self.media_box.show_all()
        return True

    def refresh_all(self):
        self.refresh_wifi()
        self.refresh_bt()
        self._br_lock = True
        self.br_scale.set_value(brightness_get())
        self._br_lock = False
        self.refresh_volume()
        self.populate_tab()
        return True

    def show_tab(self, name):
        self.current_tab = name
        ctx_n = self.tab_notif.get_style_context()
        ctx_c = self.tab_clip.get_style_context()
        if name == "notif":
            ctx_n.add_class("active"); ctx_c.remove_class("active")
        else:
            ctx_c.add_class("active"); ctx_n.remove_class("active")
        self.populate_tab()

    def populate_tab(self):
        for c in self.list_container.get_children():
            self.list_container.remove(c)
        if self.current_tab == "notif":
            items = notifications_list()
            if not items:
                l = Gtk.Label(label="No notifications"); l.get_style_context().add_class("muted")
                self.list_container.pack_start(l, False, False, 0)
            for app, summary, body in items:
                row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                row.get_style_context().add_class("list-row")
                title = Gtk.Label(label=(app or "App") + "  —  " + (summary or ""))
                title.set_halign(Gtk.Align.START); title.set_line_wrap(True); title.set_max_width_chars(44)
                title.get_style_context().add_class("val")
                row.pack_start(title, False, False, 0)
                if body:
                    b = Gtk.Label(label=body[:100]); b.set_halign(Gtk.Align.START); b.set_line_wrap(True); b.set_max_width_chars(44)
                    b.get_style_context().add_class("muted")
                    row.pack_start(b, False, False, 0)
                self.list_container.pack_start(row, False, False, 0)
        else:
            items = clipboard_list()
            if not items:
                l = Gtk.Label(label="No clipboard history"); l.get_style_context().add_class("muted")
                self.list_container.pack_start(l, False, False, 0)
            for e in items:
                if isinstance(e, str):
                    e = {"type": "text", "text": e}
                if e.get("type") == "image":
                    path = e.get("path", "")
                    hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    try:
                        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 48, 48, True)
                        img = Gtk.Image.new_from_pixbuf(pb)
                    except Exception:
                        img = Gtk.Label(label="[img]")
                    hb.pack_start(img, False, False, 0)
                    lbl = Gtk.Label(label=os.path.basename(path))
                    lbl.set_halign(Gtk.Align.START)
                    lbl.get_style_context().add_class("muted")
                    hb.pack_start(lbl, True, True, 0)
                    btn = Gtk.Button()
                    btn.get_style_context().add_class("text-btn")
                    btn.add(hb)
                    btn.connect("clicked", lambda _ , p=path: self.copy_image(p))
                    self.list_container.pack_start(btn, False, False, 0)
                else:
                    txt = e.get("text", "")
                    btn = Gtk.Button(label=txt[:80])
                    btn.get_style_context().add_class("text-btn")
                    btn.set_halign(Gtk.Align.FILL)
                    ch = btn.get_child()
                    if isinstance(ch, Gtk.Label):
                        ch.set_xalign(0.0)
                        ch.set_ellipsize(Pango.EllipsizeMode.END)
                        ch.set_max_width_chars(40)
                    btn.connect("clicked", lambda _ , t=txt: self.copy_text(t))
                    self.list_container.pack_start(btn, False, False, 0)
        self.list_container.show_all()

    def destroy(self, *a):
        try: os.remove(PIDFILE)
        except: pass
        Gtk.main_quit()

def main():
    win = ControlCenter()
    win.connect("destroy", win.destroy)
    def on_key(w, e):
        if e.keyval == Gdk.KEY_Escape:
            w.destroy()
    win.connect("key-press-event", on_key)
    Gtk.main()

if __name__ == "__main__":
    main()

