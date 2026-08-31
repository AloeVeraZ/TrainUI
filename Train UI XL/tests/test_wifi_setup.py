import importlib.util
import subprocess
import unittest
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest.mock import patch


HELPER_PATH = Path(__file__).resolve().parents[1] / "installer" / "wifi_setup.py"
SPEC = importlib.util.spec_from_file_location("trainui_wifi_setup", HELPER_PATH)
wifi_setup = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(wifi_setup)


class WifiSetupTests(unittest.TestCase):
    def test_terse_parser_preserves_escaped_colons_and_backslashes(self):
        self.assertEqual(
            wifi_setup._split_terse(r"wlan0:City\:Tech\\Lab:100"),
            ["wlan0", "City:Tech\\Lab", "100"],
        )

    def test_wifi_credential_validation(self):
        self.assertEqual(wifi_setup._validate_ssid(" Home Wi-Fi "), "Home Wi-Fi")
        self.assertEqual(wifi_setup._validate_password(""), "")
        self.assertEqual(wifi_setup._validate_password("password"), "password")
        self.assertEqual(wifi_setup._validate_password("a" * 64), "a" * 64)
        with self.assertRaises(wifi_setup.NetworkError):
            wifi_setup._validate_ssid("x" * 33)
        with self.assertRaises(wifi_setup.NetworkError):
            wifi_setup._validate_password("short")
        with self.assertRaises(wifi_setup.NetworkError):
            wifi_setup._validate_password("g" * 64)

    def test_setup_page_escapes_network_errors(self):
        page = wifi_setup.render_setup_page("bad <network> & password")
        self.assertIn("bad &lt;network&gt; &amp; password", page)
        self.assertNotIn("bad <network>", page)

    def test_monitor_retries_saved_network_then_starts_hotspot_at_deadline(self):
        class StopWatch(Exception):
            pass

        class WatchManager(wifi_setup.NetworkManager):
            def __init__(self, sleep):
                super().__init__(sleep=sleep)
                self.attempts = 0

            def status(self):
                return {"wifi": {"mode": "disconnected"}}

            def retry_saved_connection(self):
                self.attempts += 1

            def start_hotspot(self):
                raise StopWatch

        clock = [0.0]

        def sleep(seconds):
            clock[0] += seconds

        manager = WatchManager(sleep)
        with (
            patch.object(wifi_setup, "_require_root"),
            patch.object(wifi_setup.time, "monotonic", side_effect=lambda: clock[0]),
            self.assertRaises(StopWatch),
        ):
            manager.watch(timeout_seconds=30)

        self.assertGreater(manager.attempts, 1)
        self.assertEqual(clock[0], 30)

    def test_hotspot_counts_as_connected_and_does_not_restart_deadline_action(self):
        class StopWatch(Exception):
            pass

        modes = iter(["hotspot", "hotspot", "client"])

        class WatchManager(wifi_setup.NetworkManager):
            def status(self):
                try:
                    return {"wifi": {"mode": next(modes)}}
                except StopIteration:
                    raise StopWatch

            def start_hotspot(self):
                self.fail("hotspot must not be recreated while it is active")

        callbacks = []
        with (
            patch.object(wifi_setup, "_require_root"),
            self.assertRaises(StopWatch),
        ):
            WatchManager(sleep=lambda _seconds: None).watch(30, callbacks.append)
        self.assertEqual(callbacks, ["hotspot", "hotspot", "client"])

    def test_status_identifies_active_hotspot_profile(self):
        def runner(command, **_kwargs):
            joined = " ".join(command)
            if "--fields DEVICE,TYPE device status" in joined:
                output = "wlan0:wifi\n"
            elif "GENERAL.STATE,GENERAL.CONNECTION,GENERAL.CON-UUID" in joined:
                output = (
                    "GENERAL.STATE:100 (connected)\n"
                    "GENERAL.CONNECTION:TrainUI-Setup\n"
                    "GENERAL.CON-UUID:hotspot-uuid\n"
                )
            elif "802-11-wireless.mode" in joined:
                output = "ap\n"
            else:
                raise AssertionError(command)
            return subprocess.CompletedProcess(command, 0, output, "")

        with patch.object(wifi_setup, "load_config", return_value=dict(wifi_setup.DEFAULT_CONFIG)):
            status = wifi_setup.NetworkManager(runner=runner).status()
        self.assertEqual(status["wifi"]["mode"], "hotspot")
        self.assertEqual(status["hotspot_url"], "http://10.42.0.1")

    def test_failed_portal_connection_restores_hotspot_without_exposing_password(self):
        class ConnectManager(wifi_setup.NetworkManager):
            def __init__(self):
                super().__init__()
                self.commands = []
                self.restored = False

            def wifi_interface(self):
                return "wlan0"

            def nmcli(self, *arguments, **_kwargs):
                self.commands.append(arguments)
                if "up" in arguments and "TrainUI-WiFi-" in " ".join(arguments):
                    raise wifi_setup.NetworkError("authentication failed")
                return subprocess.CompletedProcess(arguments, 0, "", "")

            @contextmanager
            def _password_file(self, _setting, _secret):
                yield "/run/fake-secret"

            def _start_hotspot_locked(self, _interface, _config):
                self.restored = True

        manager = ConnectManager()
        config = dict(wifi_setup.DEFAULT_CONFIG)
        with (
            patch.object(wifi_setup, "_require_root"),
            patch.object(wifi_setup, "network_file_lock", side_effect=lambda: nullcontext()),
            patch.object(wifi_setup, "load_config", return_value=config),
            patch.object(wifi_setup, "save_config"),
            self.assertRaisesRegex(wifi_setup.NetworkError, "authentication failed"),
        ):
            manager.connect("Home Wi-Fi", "home-password")

        self.assertTrue(manager.restored)
        self.assertNotIn("home-password", " ".join(" ".join(command) for command in manager.commands))
        self.assertTrue(any("passwd-file" in command for command in manager.commands))


if __name__ == "__main__":
    unittest.main()
