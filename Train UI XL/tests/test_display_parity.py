import importlib.util
import json
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
TIMETEST_PATH = ROOT / "timertest.py"
CATALOG_PATH = ROOT / "installer" / "subway_catalog.json"
MINI_CATALOG_PATH = (
    REPOSITORY_ROOT / "Train UI Mini" / "TrainUIMiniCode" / "SubwayCatalog.h"
)


def load_runtime_module():
    """Import pure runtime helpers even on test hosts without app packages."""
    try:
        import requests  # noqa: F401
    except ImportError:
        sys.modules["requests"] = types.ModuleType("requests")

    try:
        from google.transit import gtfs_realtime_pb2  # noqa: F401
    except ImportError:
        google = types.ModuleType("google")
        transit = types.ModuleType("google.transit")
        transit.gtfs_realtime_pb2 = types.ModuleType("google.transit.gtfs_realtime_pb2")
        google.transit = transit
        sys.modules["google"] = google
        sys.modules["google.transit"] = transit
        sys.modules["google.transit.gtfs_realtime_pb2"] = transit.gtfs_realtime_pb2

    os.environ["TRAINUI_TEST_CONFIG"] = "1"
    spec = importlib.util.spec_from_file_location("trainui_runtime", TIMETEST_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_runtime_module()


class DisplayParityTests(unittest.TestCase):
    def test_ticker_uses_requested_reference_multiplier(self):
        self.assertEqual(300.0, runtime.TICKER_SPEED_PX_PER_SECOND)
        self.assertAlmostEqual(-150.0, runtime.advance_ticker(0.0, 1000.0, 0.5))

    def test_ticker_wraps_without_a_gap_or_frame_dependency(self):
        self.assertAlmostEqual(-50.0, runtime.advance_ticker(-900.0, 1000.0, 0.5))
        self.assertEqual(0.0, runtime.advance_ticker(-100.0, 0.0, 1.0))

    def test_service_panel_receives_height_freed_by_system_health(self):
        source = TIMETEST_PATH.read_text(encoding="utf-8")
        self.assertIn("root.grid_rowconfigure(2, weight=1)", source)
        self.assertIn("root.grid_rowconfigure(5, weight=0)", source)
        self.assertEqual(10, runtime.SYSTEM_PANEL_PADDING_Y)
        self.assertEqual(10, runtime.SYSTEM_STAT_FONT_SIZE)
        self.assertEqual(1, runtime.SYSTEM_STAT_GAP)
        self.assertGreater(runtime.SERVICE_TITLE_GAP, 0)
        self.assertGreater(runtime.SERVICE_MESSAGE_GAP, runtime.SERVICE_TITLE_GAP)

    def test_periodic_work_is_spread_out_and_cached(self):
        source = TIMETEST_PATH.read_text(encoding="utf-8")
        self.assertGreaterEqual(runtime.NETWORK_IDENTITY_REFRESH_SECONDS, 60)
        self.assertIn('"trains": requests.Session()', source)
        self.assertIn("self.after(2_500, self.refresh_weather)", source)
        self.assertIn("self.after(5_000, self.refresh_status)", source)

    def test_system_health_only_shows_password_for_setup_hotspot(self):
        self.assertEqual(
            (
                "Setup page: http://10.42.0.1",
                "Hotspot: TrainUI  Password: TRAINUI1",
            ),
            runtime.format_network_debug("10.42.0.1", "TrainUI"),
        )
        normal_rows = runtime.format_network_debug("192.168.1.50", "Home Wi-Fi")
        self.assertEqual(
            ("IP: 192.168.1.50", "Connection: Home Wi-Fi"),
            normal_rows,
        )
        self.assertNotIn("Password", " ".join(normal_rows))

    def test_visible_clock_drives_a_tmpfs_heartbeat(self):
        source = TIMETEST_PATH.read_text(encoding="utf-8")
        clock_method = source[
            source.index("    def _tick_clock"):
            source.index("    def _get_total_net_bytes")
        ]
        self.assertEqual(5, runtime.HEARTBEAT_INTERVAL_SECONDS)
        self.assertIn("self._mark_alive()", clock_method)
        self.assertIn("def report_callback_exception", source)

        with tempfile.TemporaryDirectory() as directory:
            heartbeat = Path(directory) / "trainui.heartbeat"
            dashboard = types.SimpleNamespace(
                heartbeat_path=str(heartbeat),
                _last_heartbeat=0.0,
            )
            runtime.Dashboard._mark_alive(dashboard)
            self.assertTrue(heartbeat.is_file())
            self.assertGreater(dashboard._last_heartbeat, 0.0)

    def test_unchanged_status_and_flash_colors_do_not_redraw(self):
        source = TIMETEST_PATH.read_text(encoding="utf-8")
        self.assertIn("if signature == previous_signature:", source)
        self.assertIn('if card_dict["_tier_color"] == color:', source)
        self.assertIn('if card["_times"] == times_key:', source)
        self.assertIn("if self._system_values.get(key) != value[key]:", source)
        status_method = source[source.index("    def _set_status"):source.index("    def _drain_events")]
        self.assertNotIn("update_idletasks", status_method)

    def test_large_weather_query_matches_mini_units_and_reference(self):
        self.assertEqual((40.5749, -73.9859), (runtime.LATITUDE, runtime.LONGITUDE))
        self.assertIn("wind_speed_unit=mph", runtime.WEATHER_URL)
        self.assertIn("timezone=America%2FNew_York", runtime.WEATHER_URL)

    def test_large_and_mini_route_station_catalogs_match(self):
        header = MINI_CATALOG_PATH.read_text(encoding="utf-8")
        station_section = header[
            header.index("static const StationDef STATIONS[]"):
            header.index("static const RouteDef ROUTES[]")
        ]
        route_section = header[header.index("static const RouteDef ROUTES[]"):]

        mini_stations = [
            match.groups()
            for match in re.finditer(
                r'\{"([^"]*)","([^"]*)","([^"]*)","([^"]*)",'
                r'"([^"]*)","([^"]*)","([^"]*)"\}',
                station_section,
            )
        ]
        mini_routes = [
            match.groups()
            for match in re.finditer(
                r'\{"([^"]*)","([^"]*)","([^"]*)","([^"]*)",'
                r'"([^"]*)",(\d+),(\d+)\}',
                route_section,
            )
        ]
        large_routes = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["routes"]

        self.assertEqual(len(large_routes), len(mini_routes))
        self.assertEqual(
            sum(len(route["stations"]) for route in large_routes),
            len(mini_stations),
        )

        for mini_route, large_route in zip(mini_routes, large_routes):
            start, count = map(int, mini_route[-2:])
            self.assertEqual(
                mini_route[:5],
                (
                    large_route["route_id"],
                    large_route["badge"],
                    large_route["service_name"],
                    large_route["feed_url"],
                    ",".join(large_route["route_ids"]),
                ),
            )
            for mini_station, large_station in zip(
                mini_stations[start:start + count],
                large_route["stations"],
            ):
                self.assertEqual(
                    mini_station,
                    (
                        large_station["station_id"],
                        large_station["station_name"],
                        large_station["borough"],
                        large_station["directions"]["N"]["stop_id"],
                        large_station["directions"]["N"]["label"],
                        large_station["directions"]["S"]["stop_id"],
                        large_station["directions"]["S"]["label"],
                    ),
                )


if __name__ == "__main__":
    unittest.main()
