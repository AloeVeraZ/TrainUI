#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fullscreen D-train departure board for a Raspberry Pi display with fluid animations."""

import math
import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime

import requests
from google.transit import gtfs_realtime_pb2

# ---- Configuration -------------------------------------------------------
STATION_NAME = "Bay 50 St"
STATION_SUBTITLE = "Brooklyn - D train"
NORTH_STOP_ID = "B23N"  # toward Manhattan
SOUTH_STOP_ID = "B23S"  # toward Coney Island
LATITUDE, LONGITUDE = 40.587, -73.984  # Bay 50 St

TRAIN_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm"
ALERT_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fall-alerts"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
    "&current=temperature_2m,weather_code,wind_speed_10m&temperature_unit=fahrenheit"
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
WHITE = "#f5f8ff"
MUTED = "#94aad0"
DIM = "#4d6385"
CYAN = "#00bfff"        # Deep Sky Blue
LIGHT_BLUE = "#87cefa"   # Light Sky Blue
BRIGHT_RED = "#ff3b30"   # Bright Red for urgent alerts
ORANGE = "#ff6319"
GREEN = "#38e6aa"
AMBER = "#ffbf4d"

# Uniform Separation Gap
GAP = 10


def weather_text(code):
    """Turn Open-Meteo WMO weather code into a short readable phrase."""
    names = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
             45: "Foggy", 48: "Foggy", 51: "Light drizzle", 53: "Drizzle",
             55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
             71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers",
             81: "Rain showers", 82: "Heavy showers", 95: "Thunderstorms"}
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


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("D Train Departures")
        self.configure(bg=BG)

        # Force geometry to fill screen and strip window borders
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.overrideredirect(True)
        self.attributes("-fullscreen", True)
        self.config(cursor="none")

        self.events = queue.Queue()
        self.last_updated = "UPDATING..."
        self.ticker_text_str = "D trains are operating normally."
        self.ticker_x = 0.0
        self.ticker_text_width = 800  # Safe default width
        self.anim_step = 0

        # Departure minute tracking for tier flashing
        self.north_minutes = []
        self.south_minutes = []

        self._build_ui()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<F11>", lambda _event: self.attributes("-fullscreen", not self.attributes("-fullscreen")))

        # Start animation loops & background fetches
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

    def card(self, parent, color=CARD):
        return tk.Frame(parent, bg=color, highlightbackground=BORDER, highlightthickness=2)

    def _build_ui(self):
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True, padx=GAP, pady=GAP)

        root.grid_columnconfigure(0, weight=1, uniform="col")
        root.grid_columnconfigure(1, weight=1, uniform="col")

        root.grid_rowconfigure(0, weight=0)  # Top Hero Header
        root.grid_rowconfigure(1, weight=0)  # Departures
        root.grid_rowconfigure(2, weight=0)  # Service Status (Ticker)
        root.grid_rowconfigure(3, weight=0)  # Weather
        root.grid_rowconfigure(4, weight=0)  # Bottom 50/50 Row
        root.grid_rowconfigure(5, weight=0)  # Footer Line

        # ---------------- 1. Connected Top Hero Header ----------------
        hero = self.card(root)
        hero.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=1)

        hero_left = tk.Frame(hero, bg=CARD)
        hero_left.grid(row=0, column=0, sticky="w", padx=18, pady=8)

        # Live Header Frame with Canvas Pulsing Indicator Dot
        live_frame = tk.Frame(hero_left, bg=CARD)
        live_frame.pack(anchor="w")

        self.live_canvas = tk.Canvas(live_frame, width=32, height=24, bg=CARD, highlightthickness=0)
        self.live_canvas.pack(side="left")

        # Multi-layered concentric pulse rings (outer, inner, core)
        self.pulse_ring_outer = self.live_canvas.create_oval(0, 0, 0, 0, fill="", outline="", width=2)
        self.pulse_ring_inner = self.live_canvas.create_oval(0, 0, 0, 0, fill="", outline="", width=2)
        self.live_core = self.live_canvas.create_oval(12, 8, 20, 16, fill=CYAN, outline="")

        self.live = self.label(live_frame, "LIVE DEPARTURES", 11, CYAN, "bold")
        self.live.pack(side="left")

        # Clock Display
        clock_frame = tk.Frame(hero_left, bg=CARD)
        clock_frame.pack(anchor="w", pady=(1, 0))

        self.clock_hours = self.label(clock_frame, "--", 50, WHITE, "bold")
        self.clock_hours.pack(side="left")

        self.colon_canvas = tk.Canvas(clock_frame, width=20, height=58, bg=CARD, highlightthickness=0)
        self.colon_canvas.pack(side="left", padx=2)
        self.colon_canvas.create_oval(6, 18, 14, 26, fill=WHITE, outline="")
        self.colon_canvas.create_oval(6, 36, 14, 44, fill=WHITE, outline="")

        self.clock_mins = self.label(clock_frame, "--", 50, WHITE, "bold")
        self.clock_mins.pack(side="left")

        self.date = self.label(hero_left, "", 16, MUTED, "bold")
        self.date.pack(anchor="w")

        hero_right = tk.Frame(hero, bg=CARD)
        hero_right.grid(row=0, column=1, sticky="e", padx=18, pady=8)
        self.label(hero_right, STATION_NAME, 26, WHITE, "bold").pack(anchor="e")
        self.label(hero_right, STATION_SUBTITLE, 15, MUTED, "bold").pack(anchor="e", pady=(4, 0))

        # ---------------- 2. Train Departures Section ----------------
        departures = tk.Frame(root, bg=BG)
        departures.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))
        departures.grid_columnconfigure((0, 1), weight=1, uniform="dept")

        self.north = self._departure_card(departures, 0, "Manhattan")
        self.south = self._departure_card(departures, 1, "Coney Island")

        # ---------------- 3. Service Status (Fluid Wrapping Marquee) ----------------
        self.status_card = self.card(root, "#08202a")
        self.status_card.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))

        status_inner = tk.Frame(self.status_card, bg="#08202a")
        status_inner.pack(fill="both", expand=True, padx=18, pady=12)

        self.status_title = self.label(status_inner, "OK  SERVICE STATUS", 15, MUTED, "bold")
        self.status_title.pack(anchor="w")

        self.status_main = self.label(status_inner, "Checking service...", 26, WHITE, "bold")
        self.status_main.pack(anchor="w", pady=(2, 0))

        # High-precision Canvas Ticker
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

        # ---------------- 4. Weather Section (Full-Width) ----------------
        weather = self.card(root, CARD_BLUE)
        weather.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))

        weather_left = tk.Frame(weather, bg=CARD_BLUE)
        weather_left.pack(side="left", padx=18, pady=8)
        self.label(weather_left, "WEATHER", 11, MUTED, "bold").pack(anchor="w")
        self.weather_temp = self.label(weather_left, "--\u00b0F", 32, WHITE, "bold")
        self.weather_temp.pack(anchor="w")

        weather_right = tk.Frame(weather, bg=CARD_BLUE)
        weather_right.pack(side="left", padx=(24, 18), pady=8)
        self.weather_detail = self.label(weather_right, "Connecting weather...", 15, MUTED, "bold")
        self.weather_detail.pack(anchor="w", pady=(14, 0))

        # ---------------- 5. Bottom Row: 50/50 Split (System Stats & Reserved Box) ----------------
        bottom_container = tk.Frame(root, bg=BG)
        bottom_container.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0, GAP))
        bottom_container.grid_columnconfigure(0, weight=1, uniform="bot")
        bottom_container.grid_columnconfigure(1, weight=1, uniform="bot")

        # Left 50% Card: System Health Stats
        sys_card = self.card(bottom_container, CARD)
        sys_card.grid(row=0, column=0, sticky="nsew", padx=(0, GAP // 2))

        sys_inner = tk.Frame(sys_card, bg=CARD)
        sys_inner.pack(fill="both", expand=True, padx=18, pady=12)

        self.label(sys_inner, "SYSTEM HEALTH", 11, MUTED, "bold").pack(anchor="w", pady=(0, 6))
        self.cpu_temp_label = self.label(sys_inner, "CPU Temp: --\u00b0F", 11, WHITE, "bold")
        self.cpu_temp_label.pack(anchor="w", pady=(2, 0))
        self.ram_label = self.label(sys_inner, "RAM: --%", 11, WHITE, "bold")
        self.ram_label.pack(anchor="w", pady=(2, 0))
        self.disk_label = self.label(sys_inner, "Disk: --%", 11, WHITE, "bold")
        self.disk_label.pack(anchor="w", pady=(2, 0))
        self.load_label = self.label(sys_inner, "Load Avg: --", 11, WHITE, "bold")
        self.load_label.pack(anchor="w", pady=(2, 0))
        self.uptime_label = self.label(sys_inner, "Uptime: --", 11, WHITE, "bold")
        self.uptime_label.pack(anchor="w", pady=(2, 0))

        # Right 50% Card: Reserved Box
        res_card = self.card(bottom_container, CARD)
        res_card.grid(row=0, column=1, sticky="nsew", padx=(GAP // 2, 0))

        res_inner = tk.Frame(res_card, bg=CARD)
        res_inner.pack(fill="both", expand=True, padx=18, pady=12)
        self.label(res_inner, "RESERVED", 11, DIM, "bold").pack(anchor="w")

        # ---------------- 6. Footer Line (Pinned Timestamp) ----------------
        self.footer = self.label(root, self.last_updated, 10, DIM, "bold")
        self.footer.grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def _departure_card(self, parent, column, destination):
        left_pad = 0 if column == 0 else GAP // 2
        right_pad = GAP // 2 if column == 0 else 0

        frame = self.card(parent)
        frame.grid(row=0, column=column, sticky="nsew", padx=(left_pad, right_pad))

        top = tk.Frame(frame, bg=CARD)
        top.pack(fill="x", padx=14, pady=(8, 2))

        badge = tk.Canvas(top, width=36, height=36, bg=CARD, highlightthickness=0)
        badge.pack(side="left")
        badge.create_oval(2, 2, 34, 34, fill=ORANGE, outline="")
        badge.create_text(18, 18, text="D", fill="white", font=("DejaVu Sans", 17, "bold"))

        self.label(top, destination, 20, WHITE, "bold").pack(side="left", padx=(10, 0))

        timetable = tk.Frame(frame, bg=CARD)
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

    def refresh_system_stats(self):
        """Reads all available system telemetry: CPU temp, RAM, Disk, Load Average, and Uptime."""
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

        # 4. CPU Load Average
        try:
            if os.path.exists("/proc/loadavg"):
                with open("/proc/loadavg", "r") as f:
                    load_vals = f.read().split()[:3]
                self.load_label.config(text=f"Load Avg: {load_vals[0]}, {load_vals[1]}, {load_vals[2]}")
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
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            now = int(time.time())
            result = {NORTH_STOP_ID: [], SOUTH_STOP_ID: []}
            for entity in feed.entity:
                if not entity.HasField("trip_update"):
                    continue
                trip = entity.trip_update.trip
                if trip.route_id and trip.route_id != "D":
                    continue
                for stop in entity.trip_update.stop_time_update:
                    if stop.stop_id not in result:
                        continue
                    stamp = stop.arrival.time or stop.departure.time
                    if stamp:
                        result[stop.stop_id].append(max(0, (stamp - now + 30) // 60))
            return {key: sorted(set(value))[:3] for key, value in result.items()}
        self._background("trains", fetch)
        self.after(TRAIN_REFRESH_MS, self.refresh_trains)

    def refresh_weather(self):
        def fetch():
            try:
                response = requests.get(WEATHER_URL, timeout=12)
                response.raise_for_status()
                current = response.json()["current"]
                return round(current["temperature_2m"]), weather_text(current["weather_code"]), round(current["wind_speed_10m"])
            except Exception:
                return 72, "Conditions unavailable", 5
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
                    if "D" not in routes:
                        continue
                    text = alert.header_text.translation[0].text if alert.header_text.translation else "D train service change"
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

        msg_str = messages[0] if has_alert else "D trains are operating normally."
        formatted_str = f"{msg_str}   \u2022   "

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
                self.last_updated = datetime.now().strftime("UPDATED %I:%M %p").lstrip("0")
                self.footer.config(text=self.last_updated)
            elif kind == "weather":
                temp, condition, wind = value
                self.weather_temp.config(text="%s\u00b0F" % temp)
                self.weather_detail.config(text="%s \u2022 %s mph wind" % (condition, wind))
            elif kind == "status":
                self._set_status(value)
        self.after(200, self._drain_events)


if __name__ == "__main__":
    Dashboard().mainloop()
