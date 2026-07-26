#!/usr/bin/env python3
"""Fullscreen D-train departure board for a Raspberry Pi display.

Install once on the Pi:
    python3 -m pip install requests gtfs-realtime-bindings
Run:
    DISPLAY=:0 python3 mirror.py

Press Escape to leave fullscreen.  All settings likely to need changing are
grouped below.  The dashboard continues showing its last good data if Wi-Fi
or an API is temporarily unavailable.
"""
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
NORTH_STOP_ID = "B23N"                 # toward Manhattan
SOUTH_STOP_ID = "B23S"                 # toward Coney Island
LATITUDE, LONGITUDE = 40.587, -73.984   # Bay 50 St

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

# ---- Palette -------------------------------------------------------------
BG = "#030914"
CARD = "#071321"
CARD_BLUE = "#091936"
BORDER = "#203555"
WHITE = "#f5f8ff"
MUTED = "#94aad0"
DIM = "#4d6385"
CYAN = "#08d7f4"
ORANGE = "#ff6319"
GREEN = "#38e6aa"
AMBER = "#ffbf4d"
RED = "#ff6874"


def weather_text(code):
    """Turn Open-Meteo WMO weather code into a short readable phrase."""
    names = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
             45: "Foggy", 48: "Foggy", 51: "Light drizzle", 53: "Drizzle",
             55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
             71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers",
             81: "Rain showers", 82: "Heavy showers", 95: "Thunderstorms"}
    return names.get(code, "Conditions unavailable")


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("D Train Departures")
        self.configure(bg=BG)
        self.attributes("-fullscreen", True)
        self.config(cursor="none")
        self.events = queue.Queue()
        self.last_updated = "Starting up"
        self._build_ui()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<F11>", lambda _event: self.attributes("-fullscreen", not self.attributes("-fullscreen")))
        self._tick_clock()
        self._drain_events()
        self.refresh_trains()
        self.refresh_weather()
        self.refresh_status()

    def label(self, parent, text="", size=14, color=WHITE, weight="normal", **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("DejaVu Sans", size, weight), **kwargs)

    def card(self, parent, color=CARD):
        return tk.Frame(parent, bg=color, highlightbackground=BORDER, highlightthickness=2)

    def _build_ui(self):
        root = tk.Frame(self, bg=BG)
        # Tuned for the common 1024x600 Raspberry Pi display.  The deliberately
        # modest padding keeps every destination and arrival readable on-screen.
        root.pack(fill="both", expand=True, padx=22, pady=16)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=3)

        # Hero panel
        hero = self.card(root)
        hero.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=1)
        left = tk.Frame(hero, bg=CARD)
        left.grid(row=0, column=0, sticky="nsew", padx=24, pady=14)
        self.live = self.label(left, "o  LIVE DEPARTURES", 14, CYAN, "bold")
        self.live.pack(anchor="w")
        self.clock = self.label(left, "--:--", 52, WHITE, "bold")
        self.clock.pack(anchor="w", pady=(3, 0))
        self.date = self.label(left, "", 19, MUTED, "bold")
        self.date.pack(anchor="w")
        right = tk.Frame(hero, bg=CARD)
        right.grid(row=0, column=1, sticky="nsew", padx=24, pady=14)
        self.label(right, STATION_NAME, 27, WHITE, "bold").pack(anchor="e", pady=(17, 0))
        self.label(right, STATION_SUBTITLE, 16, MUTED).pack(anchor="e")

        # Two arrival panels
        departures = tk.Frame(root, bg=BG)
        departures.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        departures.grid_columnconfigure((0, 1), weight=1, uniform="departures")
        departures.grid_rowconfigure(0, weight=1)
        self.north = self._departure_card(departures, 0, "VIA MANHATTAN", "Manhattan", "Track toward Manhattan")
        self.south = self._departure_card(departures, 1, "SOUTHBOUND", "Coney Island", "Track toward Coney Island")

        # Alerts need the full screen width to be readable, so they live below
        # the weather card rather than being squeezed into the right half.
        bottom = tk.Frame(root, bg=BG)
        bottom.grid(row=2, column=0, sticky="nsew")
        bottom.grid_columnconfigure(0, weight=1)
        weather = self.card(bottom, CARD_BLUE)
        weather.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.label(weather, "OUTSIDE", 11, MUTED, "bold").pack(anchor="w", padx=22, pady=(12, 0))
        self.weather_temp = self.label(weather, "-- F", 36, WHITE, "bold")
        self.weather_temp.pack(anchor="w", padx=22)
        self.weather_detail = self.label(weather, "Loading weather...", 13, MUTED)
        self.weather_detail.pack(anchor="w", padx=22, pady=(0, 12))
        self.status_card = self.card(bottom, "#08202a")
        self.status_card.grid(row=1, column=0, sticky="nsew")
        self.status_title = self.label(self.status_card, "OK  SERVICE STATUS", 14, MUTED, "bold")
        self.status_title.pack(anchor="w", padx=22, pady=(12, 0))
        self.status_main = self.label(self.status_card, "Checking service...", 24, WHITE, "bold")
        self.status_main.pack(anchor="w", padx=22)
        self.status_detail = self.label(self.status_card, "", 14, MUTED, wraplength=900, justify="left")
        self.status_detail.pack(anchor="w", padx=22, pady=(2, 12))
        self.footer = self.label(root, "UPDATING...", 10, DIM, "bold")
        self.footer.grid(row=3, column=0, sticky="w", pady=(12, 0))

    def _departure_card(self, parent, column, direction, destination, track):
        frame = self.card(parent)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 9) if column == 0 else (9, 0))
        top = tk.Frame(frame, bg=CARD)
        top.pack(fill="x", padx=22, pady=(14, 0))
        # This is the standard MTA D-route bullet: official D orange (#FF6319),
        # white route letter, and a circular outline.  Drawing it keeps this a
        # single self-contained file--no image asset can go missing on the Pi.
        badge = tk.Canvas(top, width=54, height=54, bg=CARD, highlightthickness=0)
        badge.pack()
        badge.create_oval(3, 3, 51, 51, fill=ORANGE, outline="")
        badge.create_text(27, 28, text="D", fill="white", font=("DejaVu Sans", 26, "bold"))
        # Direction wording is intentionally omitted: it was the only long
        # element in this row and could be clipped on smaller Pi displays.
        self.label(frame, destination, 24, WHITE, "bold").pack(pady=(6, 0))
        # A fixed two-column block creates a centered timetable: all numbers
        # share one left edge and every MIN label shares one right column.
        timetable = tk.Frame(frame, bg=CARD)
        timetable.pack(pady=(12, 10))
        next_time = self.label(timetable, "--", 43, CYAN, "bold")
        next_time.grid(row=0, column=0, sticky="w")
        self.label(timetable, "MIN", 13, CYAN, "bold").grid(row=0, column=1, sticky="w", padx=(28, 0), pady=(16, 0))
        second = self.label(timetable, "--", 25, "#9aacc8", "bold")
        second.grid(row=1, column=0, sticky="w")
        self.label(timetable, "MIN", 12, "#9aacc8", "bold").grid(row=1, column=1, sticky="w", padx=(28, 0), pady=(8, 0))
        third = self.label(timetable, "--", 25, "#9aacc8", "bold")
        third.grid(row=2, column=0, sticky="w")
        self.label(timetable, "MIN", 12, "#9aacc8", "bold").grid(row=2, column=1, sticky="w", padx=(28, 0), pady=(8, 0))
        return {"next": next_time, "second": second, "third": third}

    def _tick_clock(self):
        now = datetime.now()
        self.clock.config(text=now.strftime("%I:%M").lstrip("0"))
        self.date.config(text=now.strftime("%A - %B %-d") if hasattr(now, "strftime") else "")
        self._tick_clock_id = self.after(1000, self._tick_clock)

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
            response = requests.get(WEATHER_URL, timeout=12)
            response.raise_for_status()
            current = response.json()["current"]
            return round(current["temperature_2m"]), weather_text(current["weather_code"]), round(current["wind_speed_10m"])
        self._background("weather", fetch)
        self.after(WEATHER_REFRESH_MS, self.refresh_weather)

    def refresh_status(self):
        def fetch():
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
        self._background("status", fetch)
        self.after(STATUS_REFRESH_MS, self.refresh_status)

    def _apply_arrivals(self, card, times):
        if not times:
            card["next"].config(text="--")
            card["second"].config(text="--")
            card["third"].config(text="")
            return
        first = "DUE" if times[0] == 0 else str(times[0])
        card["next"].config(text=first)
        second = "" if len(times) < 2 else ("DUE" if times[1] == 0 else str(times[1]))
        third = "" if len(times) < 3 else ("DUE" if times[2] == 0 else str(times[2]))
        card["second"].config(text=second)
        card["third"].config(text=third)

    def _set_status(self, messages):
        has_alert = bool(messages)
        color = AMBER if has_alert else GREEN
        card_color = "#29200e" if has_alert else "#08202a"
        self.status_card.config(bg=card_color)
        for child in self.status_card.winfo_children(): child.config(bg=card_color)
        self.status_title.config(text=("!  SERVICE ALERT" if has_alert else "OK  SERVICE STATUS"), fg=color)
        self.status_main.config(text=("Service change" if has_alert else "Good service"))
        self.status_detail.config(text=(messages[0] if has_alert else "D trains are operating normally."))

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
                self._apply_arrivals(self.north, value[NORTH_STOP_ID])
                self._apply_arrivals(self.south, value[SOUTH_STOP_ID])
                self.last_updated = datetime.now().strftime("UPDATED %I:%M %p").lstrip("0")
                self.footer.config(text=self.last_updated)
            elif kind == "weather":
                temp, condition, wind = value
                self.weather_temp.config(text="%s F" % temp)
                self.weather_detail.config(text="%s - %s mph wind" % (condition, wind))
            elif kind == "status":
                self._set_status(value)
        self.after(200, self._drain_events)


if __name__ == "__main__":
    Dashboard().mainloop()
