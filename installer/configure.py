#!/usr/bin/env python3
"""Interactive route/station selection for the TrainUI installer."""

import argparse
import json
import os
from pathlib import Path


DEFAULT_ROUTE = "D"
DEFAULT_STATION = "B23"


def prompt_choice(items, label, describe):
    print(f"\n{label}")
    for number, item in enumerate(items, 1):
        print(f"  {number:>2}. {describe(item)}")
    while True:
        answer = input(f"Select 1-{len(items)}: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(items):
            return items[int(answer) - 1]
        print("Please enter one of the numbers shown above.")


def find_selection(catalog, route_id, station_id):
    route = next((item for item in catalog["routes"] if item["route_id"] == route_id), None)
    if not route:
        raise ValueError(f"Unknown route: {route_id}")
    station = next((item for item in route["stations"] if item["station_id"] == station_id), None)
    if not station:
        raise ValueError(f"{station_id} is not selectable for route {route_id}")
    return route, station


def make_config(route, station):
    return {
        "schema_version": 1,
        "route_id": route["route_id"],
        "route_ids": route["route_ids"],
        "badge": route["badge"],
        "service_name": route["service_name"],
        "route_name": route["route_name"],
        "route_color": route["route_color"],
        "route_text_color": route["route_text_color"],
        "feed_url": route["feed_url"],
        "station_id": station["station_id"],
        "station_name": station["station_name"],
        "borough": station["borough"],
        "directions": station["directions"],
    }


def existing_summary(config):
    return f"{config.get('service_name', config.get('route_id', '?'))} at {config.get('station_name', '?')}"


def write_config(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default=str(Path(__file__).with_name("subway_catalog.json")))
    parser.add_argument("--config", required=True)
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--route")
    parser.add_argument("--station")
    args = parser.parse_args()

    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    config_path = Path(args.config).expanduser()
    existing = None
    existing_selection = None
    if config_path.is_file():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
            existing_selection = find_selection(catalog, existing["route_id"], existing["station_id"])
        except (KeyError, ValueError, json.JSONDecodeError):
            existing = None
            existing_selection = None

    if args.route or args.station:
        if not (args.route and args.station):
            parser.error("--route and --station must be used together")
        route, station = find_selection(catalog, args.route.upper(), args.station)
    elif args.non_interactive:
        if existing:
            print(f"Keeping TrainUI selection: {existing_summary(existing)}")
            route, station = existing_selection
        else:
            route, station = find_selection(catalog, DEFAULT_ROUTE, DEFAULT_STATION)
            print(f"No terminal available; using default: {route['service_name']} at {station['station_name']}")
    else:
        if existing:
            answer = input(f"\nCurrent selection: {existing_summary(existing)}\nKeep it? [Y/n]: ").strip().casefold()
            if answer in ("", "y", "yes"):
                print("Keeping the existing TrainUI selection and refreshing its MTA data.")
                route, station = existing_selection
            else:
                existing = None
        if not existing:
            route = prompt_choice(
                catalog["routes"],
                "Choose a New York City train:",
                lambda item: f"{item['service_name']} — {item['route_name']}",
            )
            station = prompt_choice(
                route["stations"],
                f"Choose a station served by the {route['service_name']}:",
                lambda item: f"{item['station_name']} ({item['borough']})",
            )

    config = make_config(route, station)
    write_config(config_path, config)
    print(f"Configured TrainUI for {existing_summary(config)}.")
    for direction in ("N", "S"):
        if direction in config["directions"]:
            print(f"  {direction}: {config['directions'][direction]['label']}")


if __name__ == "__main__":
    main()
