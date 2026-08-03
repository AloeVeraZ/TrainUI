#!/usr/bin/env python3
"""Optional network smoke test for every realtime feed used by the catalog."""

import json
import os
import sys
from pathlib import Path

import requests
from google.transit import gtfs_realtime_pb2


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TRAINUI_TEST_CONFIG", "1")
import timertest


CATALOG = json.loads((ROOT / "installer" / "subway_catalog.json").read_text(encoding="utf-8"))


def main():
    routes_by_feed = {}
    for route in CATALOG["routes"]:
        routes_by_feed.setdefault(route["feed_url"], []).append(route["route_id"])

    content_by_url = {}
    for url, route_ids in sorted(routes_by_feed.items()):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content_by_url[url] = response.content
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        if not feed.header.gtfs_realtime_version:
            raise AssertionError(f"Missing GTFS-RT header: {url}")
        print(f"OK {', '.join(route_ids):<24} {len(feed.entity):>5} realtime entities")

    choices = 0
    for route in CATALOG["routes"]:
        for station in route["stations"]:
            stop_ids = [station["directions"][key]["stop_id"] for key in ("N", "S")]
            arrivals = timertest.parse_arrivals(
                content_by_url[route["feed_url"]],
                frozenset(route["route_ids"]),
                stop_ids,
            )
            if set(arrivals) != set(stop_ids):
                raise AssertionError(f"Arrival result mismatch for {route['route_id']} {station['station_id']}")
            choices += 1

    print(
        f"Validated {len(routes_by_feed)} realtime feeds for "
        f"{len(CATALOG['routes'])} services and {choices} route/station choices."
    )


if __name__ == "__main__":
    main()
