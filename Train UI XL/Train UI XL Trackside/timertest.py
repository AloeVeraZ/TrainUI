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
import traceback
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path

import requests
from google.transit import gtfs_realtime_pb2

# ---- Configuration -------------------------------------------------------
TEST_CONFIG = {
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
    path = Path(os.environ.get("TRAINUI_CONFIG", "~/.config/trainui-trackside/config.json")).expanduser()
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
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        if os.environ.get("TRAINUI_TEST_CONFIG") == "1":
            return TEST_CONFIG.copy()
        raise SystemExit(
            f"TrainUI is not configured. Rerun the installer to select a train and station: {path}"
        ) from exc


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
# Match Train UI Mini's fixed NYC weather reference so both displays report
# the same conditions regardless of the selected station.
LATITUDE, LONGITUDE = 40.5749, -73.9859

TRAIN_URL = TRAINUI_CONFIG["feed_url"]
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
    "&daily=weather_code,temperature_2m_max,temperature_2m_min"
    "&forecast_days=5"
    "&temperature_unit=fahrenheit&timezone=America%%2FNew_York"
    % (LATITUDE, LONGITUDE)
)
TRAIN_REFRESH_MS = 30_000
WEATHER_REFRESH_MS = 10 * 60_000
SYSTEM_REFRESH_MS = 5_000
NETWORK_IDENTITY_REFRESH_SECONDS = 60
HEARTBEAT_INTERVAL_SECONDS = 5

WIFI_SETUP_SSID = "TrainUI Trackside"
WIFI_SETUP_PASSWORD = "TRAINUI1"
WIFI_SETUP_URL = "http://10.42.0.1"
WIFI_SETUP_PROFILE = "TrainUI-Trackside-Setup"

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
SYSTEM_PANEL_PADDING_Y = 10
SYSTEM_STAT_FONT_SIZE = 10
SYSTEM_STAT_GAP = 1

# Trackside is designed to be read across a room.
TRACKSIDE_CLOCK_SIZE = 82
TRACKSIDE_DATE_SIZE = 20
TRACKSIDE_PRIMARY_TIME_SIZE = 56
TRACKSIDE_SECONDARY_TIME_SIZE = 34
TRACKSIDE_PRIMARY_UNIT_SIZE = 56
TRACKSIDE_SECONDARY_UNIT_SIZE = 34
TRACKSIDE_SYSTEM_FONT_SIZE = 10


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


def format_long_date(value):
    """Return a readable date with an ordinal day (for example, September 4th)."""
    day = value.day
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{value.strftime('%A')} - {value.strftime('%B')} {day}{suffix}"


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
            active = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"],
                capture_output=True, text=True, timeout=2,
            )
            if active.returncode == 0:
                for line in active.stdout.splitlines():
                    if line.startswith(f"{WIFI_SETUP_PROFILE}:"):
                        return WIFI_SETUP_SSID

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


def format_network_debug(ip_address, wifi_ssid):
    """Return the two System Health network rows for the active Wi-Fi mode."""

    if wifi_ssid == WIFI_SETUP_SSID:
        return (
            f"Setup page: {WIFI_SETUP_URL}",
            f"Hotspot: {WIFI_SETUP_SSID}  Password: {WIFI_SETUP_PASSWORD}",
        )
    return (
        f"IP: {ip_address}",
        f"Connection: {truncate(wifi_ssid, 16)}",
    )


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
        if cnf is None and not kwargs:
            return super().config()

        options = dict(kwargs)
        fill_changed = False
        if "bg" in options:
            new_bg = options.pop("bg")
            fill_changed = new_bg != self.bg_color
            self.bg_color = new_bg
        if cnf and isinstance(cnf, dict) and "bg" in cnf:
            cnf = dict(cnf)
            new_bg = cnf.pop("bg")
            fill_changed = fill_changed or new_bg != self.bg_color
            self.bg_color = new_bg
        if cnf or options:
            super().config(cnf, **options)
        if fill_changed:
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
        # Apply cursor hiding to the root and every child widget. This is more
        # reliable on Raspberry Pi OS Wayland than setting only the root after
        # fullscreen mode has already been entered.
        self.option_add("*Cursor", "none")
        self.configure(cursor="none")

        # Production kiosk mode fills the screen and strips window borders.
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        if fullscreen:
            self.overrideredirect(True)
            self.attributes("-fullscreen", True)

        self.events = queue.Queue()
        self.background_jobs = set()
        self.last_updated = "UPDATING..."
        self.arrival_error = None
        self._system_values = {}
        self._weather_values = None
        self.http_sessions = {}
        self.heartbeat_path = os.environ.get("TRAINUI_HEARTBEAT_FILE")
        self._last_heartbeat = 0.0

        # Departure minute tracking for tier flashing
        self.north_minutes = []
        self.south_minutes = []
        self.anim_step = 0

        self.network_identity = ("N/A", "Checking...")
        self.network_identity_checked_at = 0.0

        self._build_ui()
        self.after_idle(self._hide_pointer)
        # Freeze cards that contain changing network text so updates cannot
        # alter the overall screen proportions.
        self.after_idle(self._lock_dynamic_card_sizes)
        self.protocol("WM_DELETE_WINDOW", self._shutdown)
        self.bind("<Escape>", lambda _event: self._shutdown())
        self.bind("<F11>", lambda _event: self.attributes("-fullscreen", not self.attributes("-fullscreen")))

        if start_services:
            self.http_sessions = {
                "trains": requests.Session(),
                "weather": requests.Session(),
            }
            for session in self.http_sessions.values():
                session.headers.update({"User-Agent": "TrainUI-XL-Trackside/1.0"})

            # Start animation loops and background fetches only in production.
            self._tick_clock()
            self._animate_led_breathing()
            self._drain_events()
            self.refresh_trains()
            # Spread CPU, TLS, and protobuf work across separate moments. On the
            # single-core Pi Zero W, starting every job together causes a short
            # but visible animation stall.
            self.after(1_000, self.refresh_system_stats)
            self.after(2_500, self.refresh_weather)

    def label(self, parent, text="", size=14, color=WHITE, weight="normal", **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("DejaVu Sans", size, weight), **kwargs)

    def card(self, parent, color=GLASS_CARD, border_color=GLASS_BORDER):
        return RoundedCard(parent, bg=color, border_color=border_color, radius=16)

    def _hide_pointer(self):
        """Hide the mouse over the complete passive kiosk surface."""
        pending = [self]
        while pending:
            widget = pending.pop()
            try:
                widget.configure(cursor="none")
                pending.extend(widget.winfo_children())
            except tk.TclError:
                continue

    def _shutdown(self):
        for session in self.http_sessions.values():
            session.close()
        self.destroy()

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        """Exit after an unexpected Tk callback error so the launcher can recover."""
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        try:
            self.destroy()
        except tk.TclError:
            pass

    def _mark_alive(self):
        """Refresh the launcher's heartbeat only while the visible clock is alive."""
        if not self.heartbeat_path:
            return

        now = time.monotonic()
        if now - self._last_heartbeat < HEARTBEAT_INTERVAL_SECONDS:
            return

        try:
            Path(self.heartbeat_path).touch()
        except OSError:
            # The launcher will restart us if its runtime directory disappears.
            return
        self._last_heartbeat = now

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
        root.grid_rowconfigure(2, weight=1)  # Five-day weather gets spare height
        root.grid_rowconfigure(3, weight=0)  # Compact system health
        root.grid_rowconfigure(4, weight=0)  # Footer

        # ---------------- 1. Connected Top Hero Header (Row 0) ----------------
        hero = self.card(root, GLASS_CARD)
        hero.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))
        # Give the clock/date a little more room than the station block. This
        # keeps the minute digits visible on the 600-pixel-wide portrait panel.
        hero.grid_columnconfigure(0, weight=3, uniform="hero")
        hero.grid_columnconfigure(1, weight=2, uniform="hero")

        hero_left = tk.Frame(hero, bg=GLASS_CARD)
        hero_left.grid(row=0, column=0, sticky="nsew", padx=18, pady=8)

        live_frame = tk.Frame(hero_left, bg=GLASS_CARD)
        live_frame.pack(anchor="w")

        self.live_canvas = tk.Canvas(live_frame, width=32, height=24, bg=GLASS_CARD, highlightthickness=0)
        self.live_canvas.pack(side="left")

        self.pulse_ring_outer = self.live_canvas.create_oval(0, 0, 0, 0, fill="", outline="", width=2)
        self.pulse_ring_inner = self.live_canvas.create_oval(0, 0, 0, 0, fill="", outline="", width=2)
        self.live_core = self.live_canvas.create_oval(12, 8, 20, 16, fill=CYAN, outline="")

        self.live = self.label(live_frame, "LIVE DEPARTURES", 11, CYAN, "bold")
        self.live.pack(side="left")

        clock_width = max(220, self.winfo_screenwidth() * 3 // 5 - 72)
        clock_frame = tk.Frame(
            hero_left, bg=GLASS_CARD, width=clock_width,
            height=TRACKSIDE_CLOCK_SIZE + 8,
        )
        clock_frame.pack(anchor="w", pady=(1, 0))
        clock_frame.pack_propagate(False)

        colon_width = max(20, TRACKSIDE_CLOCK_SIZE // 2)
        digit_width = max(72, (clock_width - colon_width - 8) // 2)
        clock_size = self.fitted_font_size(
            "88", digit_width, TRACKSIDE_CLOCK_SIZE, 48,
        )
        self.clock_hours = self.label(clock_frame, "--", clock_size, WHITE, "bold")
        self.clock_hours.pack(side="left")

        colon_height = clock_size + 8
        colon_width = max(20, clock_size // 2)
        self.colon_canvas = tk.Canvas(clock_frame, width=colon_width, height=colon_height, bg=GLASS_CARD, highlightthickness=0)
        self.colon_canvas.pack(side="left", padx=2)
        dot = max(7, clock_size // 10)
        center_x = colon_width // 2
        self.colon_canvas.create_oval(center_x - dot // 2, colon_height // 3 - dot // 2,
                                      center_x + dot // 2, colon_height // 3 + dot // 2,
                                      fill=WHITE, outline="")
        self.colon_canvas.create_oval(center_x - dot // 2, colon_height * 2 // 3 - dot // 2,
                                      center_x + dot // 2, colon_height * 2 // 3 + dot // 2,
                                      fill=WHITE, outline="")

        self.clock_mins = self.label(clock_frame, "--", clock_size, WHITE, "bold")
        self.clock_mins.pack(side="left")

        date_width = max(180, self.winfo_screenwidth() * 3 // 5 - 36)
        date_size = self.fitted_font_size(
            "Wednesday - September 30th", date_width,
            TRACKSIDE_DATE_SIZE, 14,
        )
        self.date = self.label(hero_left, "", date_size, MUTED, "bold")
        self.date.pack(anchor="w")

        hero_right = tk.Frame(hero, bg=GLASS_CARD)
        hero_right.grid(row=0, column=1, sticky="nsew", padx=18, pady=8)
        hero_text_width = max(120, self.winfo_screenwidth() * 2 // 5 - 36)
        station_size = self.fitted_font_size(STATION_NAME, hero_text_width, 26, 6)
        # Keep long railroad names readable instead of allowing the final
        # words to disappear at the edge of the portrait display.
        subtitle_text = STATION_SUBTITLE.replace(" Railroad", "\nRailroad")
        subtitle_sample = max(subtitle_text.splitlines(), key=len)
        subtitle_size = self.fitted_font_size(subtitle_sample, hero_text_width, 15, 8)
        self.label(
            hero_right, STATION_NAME, station_size, WHITE, "bold",
            wraplength=hero_text_width, justify="right", anchor="e",
        ).pack(anchor="e", fill="x")
        self.label(
            hero_right, subtitle_text, subtitle_size, MUTED, "bold",
            wraplength=hero_text_width, justify="right", anchor="e",
        ).pack(anchor="e", fill="x", pady=(4, 0))

        # ---------------- 2. Train Departures Section (Row 1) ----------------
        self.north = self._departure_card(root, 0, NORTH_DIRECTION_LABEL, row=1)
        self.south = self._departure_card(root, 1, SOUTH_DIRECTION_LABEL, row=1)

        # ---------------- 3. Five-day Weather Forecast (Row 2) ----------------
        self.weather_card = self.card(root, GLASS_CARD, GLASS_BORDER)
        self.weather_card.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))
        weather_inner = tk.Frame(self.weather_card, bg=GLASS_CARD)
        weather_inner.pack(fill="both", expand=True, padx=18, pady=10)
        self.label(weather_inner, "WEATHER — 5 DAY FORECAST", 18, MUTED, "bold").pack(anchor="w", pady=(0, 6))
        self.forecast_rows = []
        for _index in range(5):
            row_frame = tk.Frame(weather_inner, bg=GLASS_CARD)
            row_frame.pack(fill="x", expand=True, pady=2)
            day_label = self.label(row_frame, "---", 18, WHITE, "bold", width=5, anchor="w")
            day_label.pack(side="left")
            condition_label = self.label(row_frame, "Loading...", 16, MUTED, "bold", anchor="w")
            condition_label.pack(side="left", fill="x", expand=True, padx=(10, 4))
            temperature_label = self.label(row_frame, "-- / --°F", 20, CYAN, "bold", anchor="e")
            temperature_label.pack(side="right")
            self.forecast_rows.append((day_label, condition_label, temperature_label))

        # ---------------- 4. Compact System Health (Row 3) ----------------
        self.sys_card = self.card(root, GLASS_CARD)
        self.sys_card.grid(
            row=3, column=0, columnspan=2,
            sticky="nsew", pady=(0, GAP)
        )

        sys_inner = tk.Frame(self.sys_card, bg=GLASS_CARD)
        self.sys_inner = sys_inner
        sys_inner.pack(
            fill="both", expand=True,
            padx=22, pady=SYSTEM_PANEL_PADDING_Y,
        )

        self.label(
            sys_inner, "SYSTEM HEALTH", TRACKSIDE_SYSTEM_FONT_SIZE, MUTED, "bold"
        ).pack(anchor="w", pady=(0, 6))

        stats_wrapper = tk.Frame(sys_inner, bg=GLASS_CARD)
        stats_wrapper.pack(fill="x", anchor="nw")

        label_options = {
            "size": TRACKSIDE_SYSTEM_FONT_SIZE,
            "color": WHITE,
            "weight": "bold",
            "anchor": "w",
            "justify": "left",
        }

        self.cpu_temp_label = self.label(stats_wrapper, "CPU Temp: --\u00b0F", **label_options)
        self.uptime_label = self.label(stats_wrapper, "Uptime: --", **label_options)
        self.ip_label = self.label(stats_wrapper, "IP: --", **label_options)
        self.net_label = self.label(stats_wrapper, "Connection: --", **label_options)

        stat_labels = [
            self.cpu_temp_label, self.uptime_label, self.ip_label, self.net_label,
        ]
        self.system_stat_labels = stat_labels
        self.system_label_map = {
            "cpu_temp": self.cpu_temp_label,
            "uptime": self.uptime_label,
            "ip": self.ip_label,
            "network": self.net_label,
        }
        for index, stat_label in enumerate(stat_labels):
            top_pad = 0 if index == 0 else SYSTEM_STAT_GAP
            bottom_pad = 0 if index == len(stat_labels) - 1 else SYSTEM_STAT_GAP
            stat_label.pack(
                anchor="w", fill="x", pady=(top_pad, bottom_pad)
            )

        # ---------------- 5. Footer Line (Row 4) ----------------
        self.footer = self.label(root, self.last_updated, 10, DIM, "bold")
        self.footer.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 0))

    def _lock_dynamic_card_sizes(self):
        """Keep dynamic text from moving the weather and health boundaries.

        The five-day forecast receives the spare height. System Health is kept
        compact at the bottom of the portrait display.
        """
        self.update_idletasks()

        weather_height = max(1, self.weather_card.winfo_height())
        self.weather_card.configure(height=weather_height)
        self.weather_card.pack_propagate(False)
        self.space_background.grid_rowconfigure(2, minsize=weather_height)

        system_height = max(
            1,
            self.sys_inner.winfo_reqheight()
            + (SYSTEM_PANEL_PADDING_Y * 2)
            + 4,
        )
        self.sys_card.configure(height=system_height)
        self.sys_card.pack_propagate(False)
        self.space_background.grid_rowconfigure(3, minsize=system_height)

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

        available_width = max(180, self.winfo_screenwidth() // 2 - 44)
        primary_size = self.fitted_font_size(
            "DUE MIN", available_width - 12,
            TRACKSIDE_PRIMARY_TIME_SIZE, 32,
        )
        secondary_size = self.fitted_font_size(
            "000 MIN", available_width - 12,
            TRACKSIDE_SECONDARY_TIME_SIZE, 22,
        )

        next_time = self.label(timetable, "--", primary_size, CYAN, "bold", width=3, anchor="w")
        next_time.grid(row=0, column=0, sticky="w")
        next_unit = self.label(timetable, "MIN", primary_size, CYAN, "bold")
        next_unit.grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(10, 0))

        second = self.label(timetable, "--", secondary_size, MUTED, "bold", width=3, anchor="w")
        second.grid(row=1, column=0, sticky="w")
        self.label(timetable, "MIN", secondary_size, MUTED, "bold").grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(2, 0))

        third = self.label(timetable, "--", secondary_size, MUTED, "bold", width=3, anchor="w")
        third.grid(row=2, column=0, sticky="w")
        self.label(timetable, "MIN", secondary_size, MUTED, "bold").grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(2, 0))

        return {
            "next": next_time,
            "next_unit": next_unit,
            "second": second,
            "third": third,
            "_tier_color": None,
            "_times": None,
        }

    # ---- Animations & Synchronized Transitions ----------------------------

    def _apply_tier_flashing(self, card_dict, minutes_list, flash_red, flash_blue):
        """Applies synchronized fast flashing colors to arrival text and MIN label."""
        if not minutes_list:
            color = CYAN
        else:
            mins = minutes_list[0]
            if mins <= 3:
                color = flash_red
            elif mins <= 5:
                color = flash_blue
            else:
                color = CYAN

        # Tk label reconfiguration is expensive on the original Pi Zero W.
        # Most arrivals are steady, so do not redraw them 30 times per second.
        if card_dict["_tier_color"] == color:
            return
        card_dict["_tier_color"] = color
        card_dict["next"].config(fg=color)
        card_dict["next_unit"].config(fg=color)

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

    def _tick_clock(self):
        now = datetime.now()
        clock_values = (
            now.strftime("%I").lstrip("0"),
            now.strftime("%M"),
            format_long_date(now),
        )
        if getattr(self, "_clock_values", None) != clock_values:
            self._clock_values = clock_values
            self.clock_hours.config(text=clock_values[0])
            self.clock_mins.config(text=clock_values[1])
            self.date.config(text=clock_values[2])
        self._mark_alive()
        self.after(1000, self._tick_clock)

    def _collect_system_stats(self):
        """Collect only the compact Trackside telemetry shown on screen."""
        stats = {}

        try:
            if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp_c = float(f.read()) / 1000.0
                    temp_f = temp_c * 9.0 / 5.0 + 32.0
                    stats["cpu_temp"] = f"CPU Temp: {round(temp_f)}\u00b0F ({round(temp_c)}\u00b0C)"
            else:
                stats["cpu_temp"] = "CPU Temp: Normal"
        except Exception:
            stats["cpu_temp"] = "CPU Temp: N/A"

        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.read().split()[0])
                hours = int(uptime_seconds // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                stats["uptime"] = f"Uptime: {hours}h {minutes}m"
            else:
                stats["uptime"] = "Uptime: N/A"
        except Exception:
            stats["uptime"] = "Uptime: N/A"

        # Interface discovery starts subprocesses, so cache it.
        identity_now = time.monotonic()
        if (
            identity_now - self.network_identity_checked_at
            >= NETWORK_IDENTITY_REFRESH_SECONDS
        ):
            self.network_identity = (
                get_ip_address(),
                get_wifi_ssid(),
            )
            self.network_identity_checked_at = identity_now
        ip_addr, wifi_ssid = self.network_identity
        # The UI thread applies these values in _drain_events. Only the setup
        # hotspot exposes its password; client Wi-Fi never does.
        stats["ip"], stats["network"] = format_network_debug(
            ip_addr, wifi_ssid
        )

        return stats

    def refresh_system_stats(self):
        """Refresh telemetry without pausing the clock or departures."""
        self._background("system", self._collect_system_stats)

        self.after(SYSTEM_REFRESH_MS, self.refresh_system_stats)

    def _background(self, kind, func):
        if kind in self.background_jobs:
            return
        self.background_jobs.add(kind)

        def worker():
            try:
                self.events.put((kind, func(), None))
            except Exception as exc:
                self.events.put((kind, None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def refresh_trains(self):
        def fetch():
            response = self.http_sessions["trains"].get(TRAIN_URL, timeout=12)
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
                response = self.http_sessions["weather"].get(
                    WEATHER_URL, timeout=12
                )
                response.raise_for_status()
                daily = response.json()["daily"]
                forecast = []
                for index, date_value in enumerate(daily["time"][:5]):
                    weather_code = int(daily["weather_code"][index])
                    day = datetime.strptime(date_value, "%Y-%m-%d").strftime("%a")
                    forecast.append((
                        day,
                        weather_text(weather_code),
                        round(daily["temperature_2m_max"][index]),
                        round(daily["temperature_2m_min"][index]),
                        weather_code,
                    ))
                return forecast
            except Exception:
                return [("---", "Conditions unavailable", "--", "--", 0)] * 5
        self._background("weather", fetch)
        self.after(WEATHER_REFRESH_MS, self.refresh_weather)

    def _apply_arrivals(self, card, times, is_north=True):
        if is_north:
            self.north_minutes = times
        else:
            self.south_minutes = times

        times_key = tuple(times)
        if card["_times"] == times_key:
            return
        card["_times"] = times_key

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

    def _drain_events(self):
        while True:
            try:
                kind, value, error = self.events.get_nowait()
            except queue.Empty:
                break
            self.background_jobs.discard(kind)
            if error:
                self.footer.config(text="LAST UPDATE FAILED - RETRYING AUTOMATICALLY")
                if kind == "trains":
                    self.arrival_error = error
                continue
            if kind == "trains":
                self.arrival_error = None
                self._apply_arrivals(self.north, value[NORTH_STOP_ID], is_north=True)
                self._apply_arrivals(self.south, value[SOUTH_STOP_ID], is_north=False)
                time_str = datetime.now().strftime("%I:%M %p").lstrip("0")
                updated_text = f"UPDATED AT {time_str}"
                if updated_text != self.last_updated:
                    self.last_updated = updated_text
                    self.footer.config(text=self.last_updated)
            elif kind == "weather":
                if value != self._weather_values:
                    self._weather_values = value
                    for row_widgets, forecast in zip(self.forecast_rows, value):
                        day_label, condition_label, temperature_label = row_widgets
                        day, condition, high, low, _weather_code = forecast
                        condition_label.config(text=truncate(condition, 22))
                        temperature_label.config(text=f"{high} / {low}\u00b0F")
                        day_label.config(text=day)
            elif kind == "system":
                for key, label in self.system_label_map.items():
                    if self._system_values.get(key) != value[key]:
                        label.config(text=value[key])
                self._system_values = value
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
