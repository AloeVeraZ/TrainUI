#!/usr/bin/env python3
"""Build TrainUI's selectable NYC subway/SIR catalog from official MTA data."""

import argparse
import csv
import io
import json
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


GTFS_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"
STATIONS_URL = "https://data.ny.gov/resource/39hk-dx4f.csv?$limit=5000"
API_ROOT = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2F"

ROUTE_ORDER = [
    "1", "2", "3", "4", "5", "6", "7",
    "A", "C", "E", "B", "D", "F", "M", "G", "J", "Z", "L",
    "N", "Q", "R", "W", "GS", "FS", "H", "SI",
]
ROUTE_ALIASES = {"F": ["F", "FX"], "6": ["6", "6X"], "7": ["7", "7X"]}
FEEDS = {
    "1": "gtfs", "2": "gtfs", "3": "gtfs", "4": "gtfs",
    "5": "gtfs", "6": "gtfs", "7": "gtfs", "GS": "gtfs",
    "A": "gtfs-ace", "C": "gtfs-ace", "E": "gtfs-ace", "H": "gtfs-ace",
    "B": "gtfs-bdfm", "D": "gtfs-bdfm", "F": "gtfs-bdfm",
    "M": "gtfs-bdfm", "FS": "gtfs-bdfm",
    "G": "gtfs-g", "J": "gtfs-jz", "Z": "gtfs-jz", "L": "gtfs-l",
    "N": "gtfs-nqrw", "Q": "gtfs-nqrw", "R": "gtfs-nqrw", "W": "gtfs-nqrw",
    "SI": "gtfs-si",
}
SERVICE_NAMES = {
    "GS": "42 St Shuttle",
    "FS": "Franklin Av Shuttle",
    "H": "Rockaway Park Shuttle",
    "SI": "Staten Island Railway",
}
BADGES = {"GS": "S", "FS": "S", "H": "S", "SI": "SIR"}
BOROUGHS = {
    "B": "Brooklyn", "Bk": "Brooklyn", "Bx": "Bronx", "M": "Manhattan",
    "Q": "Queens", "SI": "Staten Island",
}


def read_bytes(path, url):
    if path:
        return Path(path).read_bytes()
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


def zip_rows(archive, name):
    with archive.open(name) as raw:
        return list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig")))


def best_headsign(counter, fallback):
    for headsign, _count in counter.most_common():
        if headsign:
            return headsign
    return fallback


def build_catalog(gtfs_bytes, station_bytes):
    station_details = {}
    station_text = station_bytes.decode("utf-8-sig")
    for row in csv.DictReader(io.StringIO(station_text)):
        station_details[row["gtfs_stop_id"]] = row

    with zipfile.ZipFile(io.BytesIO(gtfs_bytes)) as archive:
        routes = {row["route_id"]: row for row in zip_rows(archive, "routes.txt")}
        stops = {row["stop_id"]: row for row in zip_rows(archive, "stops.txt")}
        trips = zip_rows(archive, "trips.txt")
        stop_times = zip_rows(archive, "stop_times.txt")
        feed_info = zip_rows(archive, "feed_info.txt")[0]

    canonical_by_route = {}
    for route_id in ROUTE_ORDER:
        for realtime_id in ROUTE_ALIASES.get(route_id, [route_id]):
            canonical_by_route[realtime_id] = route_id

    trip_info = {}
    for trip in trips:
        canonical = canonical_by_route.get(trip["route_id"])
        if canonical:
            trip_info[trip["trip_id"]] = (
                canonical,
                trip.get("trip_headsign", ""),
            )

    served = defaultdict(lambda: defaultdict(lambda: defaultdict(Counter)))
    for stop_time in stop_times:
        info = trip_info.get(stop_time["trip_id"])
        stop = stops.get(stop_time["stop_id"])
        if not info or not stop:
            continue
        parent_id = stop.get("parent_station") or stop["stop_id"]
        direction = stop["stop_id"][-1:]
        if direction not in ("N", "S"):
            continue
        canonical, headsign = info
        served[canonical][parent_id][direction][headsign] += 1

    catalog_routes = []
    for route_id in ROUTE_ORDER:
        route = routes[route_id]
        station_list = []
        for parent_id, direction_data in served[route_id].items():
            parent = stops[parent_id]
            detail = station_details.get(parent_id, {})
            directions = {}
            for direction, field in (("N", "north_direction_label"), ("S", "south_direction_label")):
                child_id = parent_id + direction
                if child_id not in stops:
                    continue
                label = (detail.get(field) or "").strip()
                if not label or label.casefold() == "last stop":
                    label = best_headsign(direction_data[direction], parent["stop_name"])
                directions[direction] = {"stop_id": child_id, "label": label}
            if not directions:
                continue
            station_list.append({
                "station_id": parent_id,
                "station_name": parent["stop_name"],
                "borough": BOROUGHS.get(detail.get("borough", ""), "New York City"),
                "directions": directions,
            })

        station_list.sort(key=lambda item: (item["station_name"].casefold(), item["station_id"]))
        service_name = SERVICE_NAMES.get(route_id, f"{route['route_short_name']} train")
        catalog_routes.append({
            "route_id": route_id,
            "route_ids": ROUTE_ALIASES.get(route_id, [route_id]),
            "badge": BADGES.get(route_id, route["route_short_name"]),
            "service_name": service_name,
            "route_name": route["route_long_name"],
            "route_color": "#" + route["route_color"],
            "route_text_color": "#" + route["route_text_color"],
            "feed_url": API_ROOT + FEEDS[route_id],
            "stations": station_list,
        })

    return {
        "schema_version": 1,
        "source": {
            "gtfs_url": GTFS_URL,
            "stations_url": STATIONS_URL,
            "feed_publisher": feed_info.get("feed_publisher_name", "MTA"),
            "feed_version": feed_info.get("feed_version", ""),
            "feed_start_date": feed_info.get("feed_start_date", ""),
            "feed_end_date": feed_info.get("feed_end_date", ""),
        },
        "routes": catalog_routes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gtfs-zip", help="Use a local official gtfs_subway.zip")
    parser.add_argument("--stations-csv", help="Use a local official station CSV")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).with_name("subway_catalog.json")),
    )
    args = parser.parse_args()

    catalog = build_catalog(
        read_bytes(args.gtfs_zip, GTFS_URL),
        read_bytes(args.stations_csv, STATIONS_URL),
    )
    output = Path(args.output)
    output.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {sum(len(route['stations']) for route in catalog['routes'])} route/station choices to {output}")


if __name__ == "__main__":
    main()
