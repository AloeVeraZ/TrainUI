#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configurable NYC subway/SIR departure board with a low-power background."""

import json
import math
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path

import requests
from google.transit import gtfs_realtime_pb2

# ---- Configuration -------------------------------------------------------
DEFAULT_CONFIG = {
    "schema_version": 1,
    "route_id": "D",
    "route_ids": ["D"],
    "badge": "D",
    "service_name": "D train",
    "route_name": "6 Avenue Express",
    "route_color": "#EB6800",
    "route_text_color": "#FFFFFF",
    "feed_url": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "station_id": "B23",
    "station_name": "Bay 50 St",
    "borough": "Brooklyn",
    "directions": {
        "N": {"stop_id": "B23N", "label": "Manhattan"},
        "S": {"stop_id": "B23S", "label": "Coney Island"},
    },
}


def load_trainui_config():
    path = Path(os.environ.get("TRAINUI_CONFIG", "~/.config/trainui/config.json")).expanduser()
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        required = (
            "route_id", "route_ids", "badge", "service_name", "route_color",
            "route_text_color", "feed_url", "station_id", "station_name",
            "borough", "directions",
        )
        if any(key not in config for key in required):
            raise ValueError("missing configuration field")
        for direction in ("N", "S"):
            if direction not in config["directions"]:
                raise ValueError("both travel directions are required")
            if not config["directions"][direction].get("stop_id"):
                raise ValueError("direction stop ID is required")
        return config
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return DEFAULT_CONFIG.copy()


TRAINUI_CONFIG = load_trainui_config()
ROUTE_ID = TRAINUI_CONFIG["route_id"]
ROUTE_IDS = frozenset(TRAINUI_CONFIG["route_ids"])
ROUTE_BADGE = TRAINUI_CONFIG["badge"]
ROUTE_COLOR = TRAINUI_CONFIG["route_color"]
ROUTE_TEXT_COLOR = TRAINUI_CONFIG["route_text_color"]
SERVICE_NAME = TRAINUI_CONFIG["service_name"]
STATION_ID = TRAINUI_CONFIG["station_id"]
STATION_NAME = TRAINUI_CONFIG["station_name"]
STATION_SUBTITLE = f"{TRAINUI_CONFIG['borough']} · {SERVICE_NAME}"
NORTH_STOP_ID = TRAINUI_CONFIG["directions"]["N"]["stop_id"]
SOUTH_STOP_ID = TRAINUI_CONFIG["directions"]["S"]["stop_id"]
NORTH_DIRECTION_LABEL = TRAINUI_CONFIG["directions"]["N"]["label"]
SOUTH_DIRECTION_LABEL = TRAINUI_CONFIG["directions"]["S"]["label"]
LATITUDE, LONGITUDE = 40.587, -73.984  # Bay 50 St

TRAIN_URL = TRAINUI_CONFIG["feed_url"]
ALERT_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fall-alerts"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
    "&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m&temperature_unit=fahrenheit"
    % (LATITUDE, LONGITUDE)
)
TRAIN_REFRESH_MS = 30_000
WEATHER_REFRESH_MS = 10 * 60_000
STATUS_REFRESH_MS = 5 * 60_000
SYSTEM_REFRESH_MS = 5_000

# ---- Palette & Geometry Constants ---------------------------------------
BG = "#030914"
CARD = "#071321"
CARD_BLUE = "#091936"
BORDER = "#203555"
# Opaque low-power card aliases.
GLASS_CARD = CARD
GLASS_BORDER = BORDER
WHITE = "#f5f8ff"
MUTED = "#94aad0"
DIM = "#4d6385"
CYAN = "#00bfff"        # Deep Sky Blue
LIGHT_BLUE = "#87cefa"    # Light Sky Blue
BRIGHT_RED = "#ff3b30"    # Bright Red for urgent alerts
ORANGE = "#ff6319"
GREEN = "#38e6aa"
AMBER = "#ffbf4d"

# Uniform Separation Gap
GAP = 12


def weather_text(code):
    """Turn Open-Meteo WMO weather code into a short readable phrase."""
    names = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
             45: "Foggy", 48: "Freezing fog", 51: "Light drizzle", 53: "Drizzle",
             55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Heavy freezing drizzle",
             61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain",
             67: "Heavy freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
             77: "Snow grains", 80: "Rain showers", 81: "Rain showers",
             82: "Heavy showers", 85: "Snow showers", 86: "Heavy snow showers",
             95: "Thunderstorms", 96: "Thunderstorms with hail",
             99: "Severe thunderstorms with hail"}
    return names.get(code, "Conditions unavailable")


def interpolate_color(color1_hex, color2_hex, factor):
    """Smoothly interpolate between two HEX colors (0.0 <= factor <= 1.0)."""
    factor = max(0.0, min(1.0, factor))
    r1, g1, b1 = int(color1_hex[1:3], 16), int(color1_hex[3:5], 16), int(color1_hex[5:7], 16)
    r2, g2, b2 = int(color2_hex[1:3], 16), int(color2_hex[3:5], 16), int(color2_hex[5:7], 16)
    r = int(r1 + (r2 - r1) * factor)
    g = int(g1 + (g2 - g1) * factor)
    b = int(b1 + (b2 - b1) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def truncate(text, max_len=24):
    """Safely truncate strings to prevent text clipping on screen edges."""
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "N/A"


def get_wifi_ssid():
    if shutil.which("iwgetid"):
        try:
            res = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass

    if shutil.which("nmcli"):
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
                capture_output=True, text=True, timeout=2,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if line.startswith("yes:"):
                        return line.split(":", 1)[1]
        except (OSError, subprocess.SubprocessError):
            pass

    if shutil.which("ip"):
        try:
            res = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True, text=True, timeout=2,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.split()
                if "dev" in parts:
                    dev = parts[parts.index("dev") + 1]
                    return f"Connected ({dev})"
        except (OSError, subprocess.SubprocessError):
            pass

    return "Disconnected"


def parse_arrivals(content, route_ids, stop_ids, now=None):
    """Extract the next three arrivals for configured stops from an MTA feed."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    current_time = int(time.time()) if now is None else int(now)
    result = {stop_id: [] for stop_id in stop_ids}
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        trip = entity.trip_update.trip
        if trip.route_id and trip.route_id not in route_ids:
            continue
        for stop in entity.trip_update.stop_time_update:
            if stop.stop_id not in result:
                continue
            stamp = stop.arrival.time or stop.departure.time
            if stamp:
                result[stop.stop_id].append(max(0, (stamp - current_time + 30) // 60))
    return {key: sorted(set(value))[:3] for key, value in result.items()}


class RoundedCard(tk.Canvas):
    """Custom container widget that draws rounded rectangles with clean borders."""
    def __init__(self, parent, bg=CARD, border_color=BORDER, radius=16, **kwargs):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, **kwargs)
        self.bg_color = bg
        self.border_color = border_color
        self.radius = radius
        self.bind("<Configure>", self._draw)

    def config(self, cnf=None, **kwargs):
        # ``bg`` controls the rounded card fill, not the square Canvas corners.
        # The outer Canvas color is managed separately to match the backdrop.
        options = dict(kwargs)
        if "bg" in options:
            self.bg_color = options.pop("bg")
        if cnf and isinstance(cnf, dict) and "bg" in cnf:
            cnf = dict(cnf)
            self.bg_color = cnf.pop("bg")
        super().config(cnf, **options)
        self._draw()

    configure = config

    def set_outer_bg(self, color):
        tk.Canvas.configure(self, bg=color)

    def _draw(self, event=None):
        self.delete("card_bg")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return
        r = self.radius
        self._create_rounded_rect(1, 1, w - 1, h - 1, r, fill=self.bg_color, outline=self.border_color, width=2, tags="card_bg")
        self.tag_lower("card_bg")

    def _create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x1 + r, y1,
            x2 - r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1 + r,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class StaticBackground(tk.Frame):
    """Plain, zero-animation background for maximum Raspberry Pi Zero W performance."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG, bd=0, highlightthickness=0)


class Dashboard(tk.Tk):
    def __init__(self, start_services=True, fullscreen=True):
        super().__init__()
        self.title(f"{SERVICE_NAME} Departures — {STATION_NAME}")
        self.configure(bg=BG)

        # Production kiosk mode fills the screen and strips window borders.
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        if fullscreen:
            self.overrideredirect(True)
            self.attributes("-fullscreen", True)
            self.config(cursor="none")

        self.events = queue.Queue()
        self.last_updated = "UPDATING..."
        self.ticker_text_str = f"{SERVICE_NAME} service is operating normally."
        self.ticker_x = 0.0
        self.ticker_text_width = 800  # Safe default width
        self.anim_step = 0

        # Departure minute tracking for tier flashing
        self.north_minutes = []
        self.south_minutes = []

        # Network speed baseline tracking
        self.last_rx_bytes, self.last_tx_bytes = self._get_total_net_bytes()
        self.last_net_time = time.time()

        self._build_ui()
        # Freeze cards that contain changing network text so updates cannot
        # alter the overall screen proportions.
        self.after_idle(self._lock_dynamic_card_sizes)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<F11>", lambda _event: self.attributes("-fullscreen", not self.attributes("-fullscreen")))

        if start_services:
            # Start animation loops and background fetches only in production.
            self._tick_clock()
            self._animate_ticker()
            self._animate_led_breathing()
            self._drain_events()
            self.refresh_trains()
            self.refresh_weather()
            self.refresh_status()
            self.refresh_system_stats()

    def label(self, parent, text="", size=14, color=WHITE, weight="normal", **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("DejaVu Sans", size, weight), **kwargs)

    def card(self, parent, color=GLASS_CARD, border_color=GLASS_BORDER):
        return RoundedCard(parent, bg=color, border_color=border_color, radius=16)

    def fitted_font_size(self, text, max_pixels, max_size, min_size=9, weight="bold"):
        """Return the largest font size that fits without changing its container."""
        for size in range(max_size, min_size - 1, -1):
            candidate = tkfont.Font(self, family="DejaVu Sans", size=size, weight=weight)
            if candidate.measure(text) <= max_pixels:
                return size
        # Extremely narrow displays still must not enlarge the fixed cards.
        for size in range(min_size - 1, 0, -1):
            candidate = tkfont.Font(self, family="DejaVu Sans", size=size, weight=weight)
            if candidate.measure(text) <= max_pixels:
                return size
        return 1

    def _build_ui(self):
        # Plain static layout background with no stars, planets, particles,
        # weather effects, redraw loop, or background animation.
        root = StaticBackground(self)
        self.space_background = root
        root.pack(fill="both", expand=True, padx=GAP, pady=GAP)

        root.grid_columnconfigure(0, weight=1, uniform="col")
        root.grid_columnconfigure(1, weight=1, uniform="col")

        root.grid_rowconfigure(0, weight=0)  # Top Hero Header
        root.grid_rowconfigure(1, weight=0)  # Departures
        root.grid_rowconfigure(2, weight=0)  # Service Status
        root.grid_rowconfigure(3, weight=0)  # Weather
        root.grid_rowconfigure(4, weight=0)  # Zero-height spacer
        root.grid_rowconfigure(5, weight=1)  # Full-width System Health
        root.grid_rowconfigure(6, weight=0)  # Footer

        # ---------------- 1. Connected Top Hero Header (Row 0) ----------------
        hero = self.card(root, GLASS_CARD)
        hero.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=1)

        hero_left = tk.Frame(hero, bg=GLASS_CARD)
        hero_left.grid(row=0, column=0, sticky="w", padx=18, pady=8)

        live_frame = tk.Frame(hero_left, bg=GLASS_CARD)
        live_frame.pack(anchor="w")

        self.live_canvas = tk.Canvas(live_frame, width=32, height=24, bg=GLASS_CARD, highlightthickness=0)
        self.live_canvas.pack(side="left")

        self.pulse_ring_outer = self.live_canvas.create_oval(0, 0, 0, 0, fill="", outline="", width=2)
        self.pulse_ring_inner = self.live_canvas.create_oval(0, 0, 0, 0, fill="", outline="", width=2)
        self.live_core = self.live_canvas.create_oval(12, 8, 20, 16, fill=CYAN, outline="")

        self.live = self.label(live_frame, "LIVE DEPARTURES", 11, CYAN, "bold")
        self.live.pack(side="left")

        clock_frame = tk.Frame(hero_left, bg=GLASS_CARD)
        clock_frame.pack(anchor="w", pady=(1, 0))

        self.clock_hours = self.label(clock_frame, "--", 50, WHITE, "bold")
        self.clock_hours.pack(side="left")

        self.colon_canvas = tk.Canvas(clock_frame, width=20, height=58, bg=GLASS_CARD, highlightthickness=0)
        self.colon_canvas.pack(side="left", padx=2)
        self.colon_canvas.create_oval(6, 18, 14, 26, fill=WHITE, outline="")
        self.colon_canvas.create_oval(6, 36, 14, 44, fill=WHITE, outline="")

        self.clock_mins = self.label(clock_frame, "--", 50, WHITE, "bold")
        self.clock_mins.pack(side="left")

        self.date = self.label(hero_left, "", 16, MUTED, "bold")
        self.date.pack(anchor="w")

        hero_right = tk.Frame(hero, bg=GLASS_CARD)
        hero_right.grid(row=0, column=1, sticky="e", padx=18, pady=8)
        hero_text_width = max(110, self.winfo_screenwidth() // 2 - 48)
        station_size = self.fitted_font_size(STATION_NAME, hero_text_width, 26, 6)
        subtitle_size = self.fitted_font_size(STATION_SUBTITLE, hero_text_width, 15, 6)
        self.label(hero_right, STATION_NAME, station_size, WHITE, "bold").pack(anchor="e")
        self.label(hero_right, STATION_SUBTITLE, subtitle_size, MUTED, "bold").pack(anchor="e", pady=(4, 0))

        # ---------------- 2. Train Departures Section (Row 1) ----------------
        self.north = self._departure_card(root, 0, NORTH_DIRECTION_LABEL, row=1)
        self.south = self._departure_card(root, 1, SOUTH_DIRECTION_LABEL, row=1)

        # ---------------- 3. Service Status (Row 2) ----------------
        self.status_card = self.card(root, "#08202a", BORDER)
        self.status_card.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))

        status_inner = tk.Frame(self.status_card, bg="#08202a")
        status_inner.pack(fill="both", expand=True, padx=18, pady=12)

        self.status_title = self.label(status_inner, "OK  SERVICE STATUS", 15, MUTED, "bold")
        self.status_title.pack(anchor="w")

        self.status_main = self.label(status_inner, "Checking service...", 26, WHITE, "bold")
        self.status_main.pack(anchor="w", pady=(2, 0))

        self.ticker_canvas = tk.Canvas(status_inner, bg="#08202a", highlightthickness=0, height=36)
        self.ticker_canvas.pack(fill="x", expand=True, pady=(4, 0))

        self.ticker_text_1 = self.ticker_canvas.create_text(
            0, 18, text=self.ticker_text_str, anchor="w", fill=MUTED, font=("DejaVu Sans", 20, "bold")
        )
        self.ticker_text_2 = self.ticker_canvas.create_text(
            0, 18, text=self.ticker_text_str, anchor="w", fill=MUTED, font=("DejaVu Sans", 20, "bold")
        )

        self.update_idletasks()
        bbox = self.ticker_canvas.bbox(self.ticker_text_1)
        if bbox:
            self.ticker_text_width = bbox[2] - bbox[0]

        # ---------------- 4. Weather Section (Row 3) ----------------
        self.weather_card = self.card(root, GLASS_CARD, GLASS_BORDER)
        self.weather_card.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))
        weather = self.weather_card

        weather_left = tk.Frame(weather, bg=GLASS_CARD)
        weather_left.pack(side="left", padx=18, pady=8)
        self.label(weather_left, "WEATHER", 11, MUTED, "bold").pack(anchor="w")
        self.weather_temp = self.label(weather_left, "--\u00b0F", 32, WHITE, "bold")
        self.weather_temp.pack(anchor="w")

        weather_right = tk.Frame(weather, bg=GLASS_CARD)
        weather_right.pack(side="left", padx=(24, 18), pady=8)
        self.weather_cond = self.label(weather_right, "Connecting weather...", 14, WHITE, "bold")
        self.weather_cond.pack(anchor="w", pady=(4, 2))
        self.weather_humidity = self.label(weather_right, "Humidity: --%", 13, MUTED, "bold")
        self.weather_humidity.pack(anchor="w", pady=(0, 0))

        # ---------------- Spacer (Row 4) ----------------
        spacer = tk.Frame(root, bg=root.cget("bg"), height=0)
        spacer.grid(row=4, column=0, columnspan=2, sticky="ew")

        # ---------------- 5. Full-width System Health (Row 5) ----------------
        sys_card = self.card(root, GLASS_CARD)
        sys_card.grid(
            row=5, column=0, columnspan=2,
            sticky="nsew", pady=(0, GAP)
        )

        sys_inner = tk.Frame(sys_card, bg=GLASS_CARD)
        sys_inner.pack(fill="both", expand=True, padx=22, pady=12)

        self.label(
            sys_inner, "SYSTEM HEALTH", 11, MUTED, "bold"
        ).pack(anchor="w", pady=(0, 6))

        stats_wrapper = tk.Frame(sys_inner, bg=GLASS_CARD)
        stats_wrapper.pack(fill="both", expand=True, anchor="nw")

        label_options = {
            "size": 11,
            "color": WHITE,
            "weight": "bold",
            "anchor": "w",
            "justify": "left",
        }

        self.cpu_temp_label = self.label(stats_wrapper, "CPU Temp: --\u00b0F", **label_options)
        self.ram_label = self.label(stats_wrapper, "RAM: --%", **label_options)
        self.disk_label = self.label(stats_wrapper, "Disk: --%", **label_options)
        self.load_label = self.label(stats_wrapper, "Load Avg: --", **label_options)
        self.uptime_label = self.label(stats_wrapper, "Uptime: --", **label_options)
        self.ip_label = self.label(stats_wrapper, "IP: --", **label_options)
        self.net_label = self.label(stats_wrapper, "Connection: --", **label_options)
        self.down_speed_label = self.label(stats_wrapper, "Download: --", **label_options)
        self.up_speed_label = self.label(stats_wrapper, "Upload: --", **label_options)

        stat_labels = [
            self.cpu_temp_label, self.ram_label, self.disk_label,
            self.load_label, self.uptime_label, self.ip_label,
            self.net_label, self.down_speed_label, self.up_speed_label,
        ]
        for stat_label in stat_labels:
            stat_label.pack(anchor="w", fill="x", pady=2)

        # ---------------- 6. Footer Line (Row 6) ----------------
        self.footer = self.label(root, self.last_updated, 10, DIM, "bold")
        self.footer.grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 0))

    def _lock_dynamic_card_sizes(self):
        """Lock Weather and Service Status to their initial rendered heights.

        Tk normally lets a child label update its requested geometry. These two
        cards display changing external text, so their requested size could
        otherwise shift the rows around. Capturing the initial height and then
        disabling propagation keeps every section perfectly stable.
        """
        self.update_idletasks()

        for row, card in ((2, self.status_card), (3, self.weather_card)):
            locked_height = max(1, card.winfo_height())
            card.configure(height=locked_height)
            card.pack_propagate(False)
            self.space_background.grid_rowconfigure(row, minsize=locked_height)

    def _departure_card(self, parent, column, destination, row=0):
        left_pad = 0 if column == 0 else GAP // 2
        right_pad = GAP // 2 if column == 0 else 0

        frame = self.card(parent, GLASS_CARD)
        frame.grid(
            row=row, column=column, sticky="nsew",
            padx=(left_pad, right_pad), pady=(0, GAP)
        )

        top = tk.Frame(frame, bg=GLASS_CARD)
        top.pack(fill="x", padx=14, pady=(8, 2))

        badge = tk.Canvas(top, width=36, height=36, bg=GLASS_CARD, highlightthickness=0)
        badge.pack(side="left")
        badge.create_oval(2, 2, 34, 34, fill=ROUTE_COLOR, outline="")
        badge_size = self.fitted_font_size(ROUTE_BADGE, 27, 17, 8)
        badge.create_text(
            18, 18, text=ROUTE_BADGE, fill=ROUTE_TEXT_COLOR,
            font=("DejaVu Sans", badge_size, "bold"),
        )

        direction_width = max(80, self.winfo_screenwidth() // 2 - 88)
        direction_size = self.fitted_font_size(destination, direction_width, 20, 6)
        self.label(top, destination, direction_size, WHITE, "bold").pack(side="left", padx=(10, 0))

        timetable = tk.Frame(frame, bg=GLASS_CARD)
        timetable.pack(fill="both", expand=True, padx=14, pady=(2, 8))

        next_time = self.label(timetable, "--", 38, CYAN, "bold", width=3, anchor="w")
        next_time.grid(row=0, column=0, sticky="w")
        next_unit = self.label(timetable, "MIN", 13, CYAN, "bold")
        next_unit.grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(10, 0))

        second = self.label(timetable, "--", 24, MUTED, "bold", width=3, anchor="w")
        second.grid(row=1, column=0, sticky="w")
        self.label(timetable, "MIN", 11, MUTED, "bold").grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(2, 0))

        third = self.label(timetable, "--", 24, MUTED, "bold", width=3, anchor="w")
        third.grid(row=2, column=0, sticky="w")
        self.label(timetable, "MIN", 11, MUTED, "bold").grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(2, 0))

        return {"next": next_time, "next_unit": next_unit, "second": second, "third": third}

    # ---- Animations & Synchronized Transitions ----------------------------

    def _apply_tier_flashing(self, card_dict, minutes_list, flash_red, flash_blue):
        """Applies synchronized fast flashing colors to arrival text and MIN label."""
        if not minutes_list:
            card_dict["next"].config(fg=CYAN)
            card_dict["next_unit"].config(fg=CYAN)
            return

        mins = minutes_list[0]

        if mins <= 3:  # 0 (DUE), 1, 2, or 3 MIN: Fast Snappy Flash (Red <-> Gray)
            card_dict["next"].config(fg=flash_red)
            card_dict["next_unit"].config(fg=flash_red)
        elif mins <= 5:  # 4 or 5 MIN: Fast Snappy Flash (Blue <-> Gray)
            card_dict["next"].config(fg=flash_blue)
            card_dict["next_unit"].config(fg=flash_blue)
        else:  # 6+ MIN: Steady Cyan
            card_dict["next"].config(fg=CYAN)
            card_dict["next_unit"].config(fg=CYAN)

    def _animate_led_breathing(self):
        """Pulse animation for dot rings and sharp, snappy synchronized countdown flashing."""
        CYCLE_FRAMES = 18
        self.anim_step = (self.anim_step + 1) % CYCLE_FRAMES

        raw_sine = (math.sin(math.radians(self.anim_step * 50)) + 1) / 2.0
        snappy_factor = raw_sine ** 4

        flash_red = interpolate_color(MUTED, BRIGHT_RED, snappy_factor)
        flash_blue = interpolate_color(MUTED, CYAN, snappy_factor)

        progress_outer = self.anim_step / float(CYCLE_FRAMES)
        progress_inner = (self.anim_step + (CYCLE_FRAMES // 2)) % CYCLE_FRAMES / float(CYCLE_FRAMES)

        center_x, center_y = 16, 12
        min_r, max_r = 4, 14

        # Outer Wave
        r_outer = min_r + (max_r - min_r) * progress_outer
        color_outer = interpolate_color(LIGHT_BLUE, CARD, progress_outer)
        self.live_canvas.coords(
            self.pulse_ring_outer,
            center_x - r_outer, center_y - r_outer,
            center_x + r_outer, center_y + r_outer
        )
        self.live_canvas.itemconfig(self.pulse_ring_outer, outline=color_outer)

        # Inner Wave
        r_inner = min_r + (max_r - min_r) * progress_inner
        color_inner = interpolate_color(CYAN, CARD, progress_inner)
        self.live_canvas.coords(
            self.pulse_ring_inner,
            center_x - r_inner, center_y - r_inner,
            center_x + r_inner, center_y + r_inner
        )
        self.live_canvas.itemconfig(self.pulse_ring_inner, outline=color_inner)

        # Apply synchronized colors to both North & South cards simultaneously
        self._apply_tier_flashing(self.north, self.north_minutes, flash_red, flash_blue)
        self._apply_tier_flashing(self.south, self.south_minutes, flash_red, flash_blue)

        self.after(33, self._animate_led_breathing)

    def _animate_ticker(self):
        """Rock-solid marquee math that wraps flawlessly at high speed."""
        STEP = 10.0  # Fast scroll speed

        self.ticker_x -= STEP

        if self.ticker_x <= -self.ticker_text_width:
            self.ticker_x += self.ticker_text_width

        rx = int(self.ticker_x)

        self.ticker_canvas.coords(self.ticker_text_1, rx, 18)
        self.ticker_canvas.coords(self.ticker_text_2, rx + int(self.ticker_text_width), 18)

        self.after(16, self._animate_ticker)  # 60 FPS update

    def _tick_clock(self):
        now = datetime.now()
        self.clock_hours.config(text=now.strftime("%I").lstrip("0"))
        self.clock_mins.config(text=now.strftime("%M"))
        self.date.config(text=now.strftime("%A - %B %-d") if hasattr(now, "strftime") else "")
        self.after(1000, self._tick_clock)

    def _get_total_net_bytes(self):
        rx_total = 0
        tx_total = 0
        try:
            with open("/proc/net/dev", "r") as f:
                lines = f.readlines()
            for line in lines[2:]:
                parts = line.strip().split(":")
                if len(parts) == 2:
                    iface = parts[0].strip()
                    if iface == "lo":
                        continue
                    data = parts[1].split()
                    if len(data) >= 9:
                        rx_total += int(data[0])
                        tx_total += int(data[8])
        except Exception:
            pass
        return rx_total, tx_total

    def refresh_system_stats(self):
        """Reads all available system telemetry: CPU temp, RAM, Disk, Load Average, Uptime, IP, Connection, and Speeds."""
        # 1. CPU Temperature
        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp_c = float(f.read()) / 1000.0
                    temp_f = temp_c * 9.0 / 5.0 + 32.0
                    self.cpu_temp_label.config(text=f"CPU Temp: {round(temp_f)}\u00b0F ({round(temp_c)}\u00b0C)")
            else:
                self.cpu_temp_label.config(text="CPU Temp: Normal")
        except Exception:
            self.cpu_temp_label.config(text="CPU Temp: N/A")

        # 2. RAM Usage
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].strip().split()[0])
            total = mem.get("MemTotal", 0)
            available = mem.get("MemAvailable", mem.get("MemFree", 0))
            if total > 0:
                used_kb = total - available
                used_pct = round(used_kb / total * 100)
                total_mb = round(total / 1024)
                used_mb = round(used_kb / 1024)
                self.ram_label.config(text=f"RAM: {used_mb}MB / {total_mb}MB ({used_pct}%)")
            else:
                self.ram_label.config(text="RAM: N/A")
        except Exception:
            self.ram_label.config(text="RAM: N/A")

        # 3. Disk Usage
        try:
            st = os.statvfs('/')
            total_bytes = st.f_blocks * st.f_frsize
            free_bytes = st.f_bavail * st.f_frsize
            used_bytes = total_bytes - free_bytes
            if total_bytes > 0:
                disk_pct = round(used_bytes / total_bytes * 100)
                total_gb = round(total_bytes / (1024**3), 1)
                used_gb = round(used_bytes / (1024**3), 1)
                self.disk_label.config(text=f"Disk: {used_gb}GB / {total_gb}GB ({disk_pct}%)")
            else:
                self.disk_label.config(text="Disk: N/A")
        except Exception:
            self.disk_label.config(text="Disk: N/A")

        # 4. CPU Load Average (Truncated to prevent clipping)
        try:
            if os.path.exists("/proc/loadavg"):
                with open("/proc/loadavg", "r") as f:
                    load_vals = f.read().split()[:3]
                load_str = f"Load Avg: {load_vals[0]}, {load_vals[1]}, {load_vals[2]}"
                self.load_label.config(text=truncate(load_str, 28))
            else:
                self.load_label.config(text="Load Avg: N/A")
        except Exception:
            self.load_label.config(text="Load Avg: N/A")

        # 5. Uptime
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.read().split()[0])
                hours = int(uptime_seconds // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                self.uptime_label.config(text=f"Uptime: {hours}h {minutes}m")
            else:
                self.uptime_label.config(text="Uptime: N/A")
        except Exception:
            self.uptime_label.config(text="Uptime: N/A")

        # 6. Network IP & Connection
        ip_addr = get_ip_address()
        ssid = truncate(get_wifi_ssid(), 16)
        self.ip_label.config(text=f"IP: {ip_addr}")
        self.net_label.config(text=f"Connection: {ssid}")

        # 7. Network Upload/Download Speeds
        current_rx, current_tx = self._get_total_net_bytes()
        now_time = time.time()
        time_delta = now_time - getattr(self, 'last_net_time', now_time - 5)
        if time_delta > 0:
            rx_rate = (current_rx - getattr(self, 'last_rx_bytes', current_rx)) / time_delta
            tx_rate = (current_tx - getattr(self, 'last_tx_bytes', current_tx)) / time_delta
        else:
            rx_rate = 0
            tx_rate = 0

        self.last_rx_bytes = current_rx
        self.last_tx_bytes = current_tx
        self.last_net_time = now_time

        def format_speed(bytes_sec):
            if bytes_sec > 1024 * 1024:
                return f"{bytes_sec / (1024 * 1024):.1f} MB/s"
            elif bytes_sec > 1024:
                return f"{bytes_sec / 1024:.1f} KB/s"
            else:
                return f"{int(bytes_sec)} B/s"

        self.down_speed_label.config(text=f"Download: {format_speed(rx_rate)}")
        self.up_speed_label.config(text=f"Upload: {format_speed(tx_rate)}")

        self.after(SYSTEM_REFRESH_MS, self.refresh_system_stats)

    def _background(self, kind, func):
        def worker():
            try:
                self.events.put((kind, func(), None))
            except Exception as exc:
                self.events.put((kind, None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def refresh_trains(self):
        def fetch():
            response = requests.get(TRAIN_URL, timeout=12)
            response.raise_for_status()
            return parse_arrivals(
                response.content,
                ROUTE_IDS,
                (NORTH_STOP_ID, SOUTH_STOP_ID),
            )
        self._background("trains", fetch)
        self.after(TRAIN_REFRESH_MS, self.refresh_trains)

    def refresh_weather(self):
        def fetch():
            try:
                response = requests.get(WEATHER_URL, timeout=12)
                response.raise_for_status()
                current = response.json()["current"]
                weather_code = int(current["weather_code"])
                return (
                    round(current["temperature_2m"]),
                    weather_text(weather_code),
                    round(current["wind_speed_10m"]),
                    round(current["relative_humidity_2m"]),
                    weather_code
                )
            except Exception:
                return 72, "Conditions unavailable", 5, 50, 0
        self._background("weather", fetch)
        self.after(WEATHER_REFRESH_MS, self.refresh_weather)

    def refresh_status(self):
        def fetch():
            try:
                response = requests.get(ALERT_URL, timeout=12)
                response.raise_for_status()
                feed = gtfs_realtime_pb2.FeedMessage()
                feed.ParseFromString(response.content)
                messages = []
                for entity in feed.entity:
                    if not entity.HasField("alert"):
                        continue
                    alert = entity.alert
                    routes = {item.route_id for item in alert.informed_entity if item.route_id}
                    stops = {item.stop_id for item in alert.informed_entity if item.stop_id}
                    selected_stops = {STATION_ID, NORTH_STOP_ID, SOUTH_STOP_ID}
                    if not routes.intersection(ROUTE_IDS) and not stops.intersection(selected_stops):
                        continue
                    text = alert.header_text.translation[0].text if alert.header_text.translation else f"{SERVICE_NAME} service change"
                    messages.append(text.replace("\n", " "))
                return messages
            except Exception:
                return []
        self._background("status", fetch)
        self.after(STATUS_REFRESH_MS, self.refresh_status)

    def _apply_arrivals(self, card, times, is_north=True):
        if is_north:
            self.north_minutes = times
        else:
            self.south_minutes = times

        if not times:
            card["next"].config(text="--")
            card["next_unit"].config(text="MIN")
            card["second"].config(text="--")
            card["third"].config(text="")
            return

        if times[0] == 0:
            card["next"].config(text="DUE")
            card["next_unit"].config(text="")
        else:
            card["next"].config(text=str(times[0]))
            card["next_unit"].config(text="MIN")

        second = "" if len(times) < 2 else ("DUE" if times[1] == 0 else str(times[1]))
        card["second"].config(text=second)

        third = "" if len(times) < 3 else ("DUE" if times[2] == 0 else str(times[2]))
        card["third"].config(text=third)

    def _set_status(self, messages):
        has_alert = bool(messages)
        color = AMBER if has_alert else GREEN
        card_color = "#29200e" if has_alert else "#08202a"

        self.status_card.config(bg=card_color)
        for child in self.status_card.winfo_children():
            child.config(bg=card_color)
            for grand in child.winfo_children():
                grand.config(bg=card_color)

        self.ticker_canvas.config(bg=card_color)
        self.status_title.config(text=("!  SERVICE ALERT" if has_alert else "OK  SERVICE STATUS"), fg=color)
        self.status_main.config(text=("Service Change" if has_alert else "Good Service"))

        msg_str = messages[0] if has_alert else f"{SERVICE_NAME} service is operating normally."
        formatted_str = f"{msg_str}    \u2022    "

        if self.ticker_text_str != formatted_str:
            self.ticker_text_str = formatted_str
            self.ticker_canvas.itemconfig(self.ticker_text_1, text=self.ticker_text_str)
            self.ticker_canvas.itemconfig(self.ticker_text_2, text=self.ticker_text_str)
            self.ticker_x = 0
            
            self.update_idletasks()
            bbox = self.ticker_canvas.bbox(self.ticker_text_1)
            if bbox:
                self.ticker_text_width = bbox[2] - bbox[0]

    def _drain_events(self):
        while True:
            try:
                kind, value, error = self.events.get_nowait()
            except queue.Empty:
                break
            if error:
                self.footer.config(text="LAST UPDATE FAILED - RETRYING AUTOMATICALLY")
                continue
            if kind == "trains":
                self._apply_arrivals(self.north, value[NORTH_STOP_ID], is_north=True)
                self._apply_arrivals(self.south, value[SOUTH_STOP_ID], is_north=False)
                time_str = datetime.now().strftime("%I:%M %p").lstrip("0")
                self.last_updated = f"UPDATED AT {time_str}"
                self.footer.config(text=self.last_updated)
            elif kind == "weather":
                temp, condition, wind, humidity, weather_code = value
                self.weather_temp.config(text="%s\u00b0F" % temp)
                weather_line = "%s \u2022 %s mph wind" % (condition, wind)
                self.weather_cond.config(text=truncate(weather_line, 42))
                self.weather_humidity.config(text="Humidity: %s%%" % humidity)
            elif kind == "status":
                self._set_status(value)
        self.after(200, self._drain_events)


def smoke_test_ui():
    """Construct the complete layout without fullscreen mode or network work."""
    dashboard = Dashboard(start_services=False, fullscreen=False)
    dashboard.withdraw()
    dashboard.update_idletasks()
    dashboard.destroy()
    print(f"TrainUI UI smoke test passed: {SERVICE_NAME} at {STATION_NAME}")


if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        smoke_test_ui()
    else:
        Dashboard().mainloop()
