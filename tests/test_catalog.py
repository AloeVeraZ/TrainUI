import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "installer" / "subway_catalog.json"
CONFIGURE_PATH = ROOT / "installer" / "configure.py"
EXPECTED_ROUTES = {
    "1", "2", "3", "4", "5", "6", "7",
    "A", "C", "E", "B", "D", "F", "M", "G", "J", "Z", "L",
    "N", "Q", "R", "W", "GS", "FS", "H", "SI",
}
EXPECTED_FEEDS = {
    "gtfs", "gtfs-ace", "gtfs-bdfm", "gtfs-g", "gtfs-jz", "gtfs-l",
    "gtfs-nqrw", "gtfs-si",
}


spec = importlib.util.spec_from_file_location("trainui_configure", CONFIGURE_PATH)
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_exact_supported_route_set(self):
        self.assertEqual(EXPECTED_ROUTES, {route["route_id"] for route in self.catalog["routes"]})
        self.assertNotIn("LIRR", EXPECTED_ROUTES)
        self.assertNotIn("MNR", EXPECTED_ROUTES)

    def test_all_eight_official_realtime_feed_groups_are_used(self):
        feeds = {route["feed_url"].rsplit("%2F", 1)[-1] for route in self.catalog["routes"]}
        self.assertEqual(EXPECTED_FEEDS, feeds)

    def test_every_route_station_builds_a_complete_runtime_config(self):
        choices = 0
        for route in self.catalog["routes"]:
            self.assertTrue(route["stations"], route["route_id"])
            station_ids = set()
            for station in route["stations"]:
                with self.subTest(route=route["route_id"], station=station["station_id"]):
                    self.assertNotIn(station["station_id"], station_ids)
                    station_ids.add(station["station_id"])
                    self.assertEqual({"N", "S"}, set(station["directions"]))
                    self.assertTrue(station["borough"])
                    for direction in ("N", "S"):
                        value = station["directions"][direction]
                        self.assertEqual(direction, value["stop_id"][-1])
                        self.assertTrue(value["label"].strip())
                    config = configure.make_config(route, station)
                    self.assertEqual(route["route_id"], config["route_id"])
                    self.assertEqual(station["station_id"], config["station_id"])
                    self.assertTrue(config["feed_url"].startswith("https://api-endpoint.mta.info/"))
                    choices += 1
        self.assertGreaterEqual(choices, 900)

    def test_default_bay_50_d_selection_remains_available(self):
        route, station = configure.find_selection(
            self.catalog, configure.DEFAULT_ROUTE, configure.DEFAULT_STATION,
        )
        self.assertEqual("D", route["route_id"])
        self.assertEqual("Bay 50 St", station["station_name"])
        self.assertEqual("Manhattan", station["directions"]["N"]["label"])
        self.assertEqual("Coney Island", station["directions"]["S"]["label"])

    def test_long_labels_exist_for_dynamic_scaling_coverage(self):
        labels = [
            direction["label"]
            for route in self.catalog["routes"]
            for station in route["stations"]
            for direction in station["directions"].values()
        ]
        names = [
            station["station_name"]
            for route in self.catalog["routes"]
            for station in route["stations"]
        ]
        self.assertGreater(max(map(len, labels)), 20)
        self.assertGreater(max(map(len, names)), 25)

    def test_noninteractive_update_preserves_choice_and_refreshes_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            subprocess.run(
                [
                    sys.executable, str(CONFIGURE_PATH), "--config", str(config_path),
                    "--route", "SI", "--station", "S31",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["feed_url"] = "obsolete"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable, str(CONFIGURE_PATH), "--config", str(config_path),
                    "--non-interactive",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            refreshed = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual("SI", refreshed["route_id"])
            self.assertEqual("S31", refreshed["station_id"])
            self.assertTrue(refreshed["feed_url"].endswith("gtfs-si"))


if __name__ == "__main__":
    unittest.main()
