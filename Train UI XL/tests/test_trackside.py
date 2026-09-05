import unittest
from pathlib import Path


XL_ROOT = Path(__file__).resolve().parents[1]
TRACKSIDE_ROOT = XL_ROOT / "Train UI XL Trackside"
TRACKSIDE_APP = TRACKSIDE_ROOT / "timertest.py"
TRACKSIDE_INSTALLER = TRACKSIDE_ROOT / "installer" / "install.sh"


class TracksideLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (TRACKSIDE_ROOT / "README.md").read_text(encoding="utf-8")
        cls.app = TRACKSIDE_APP.read_text(encoding="utf-8")
        cls.installer = TRACKSIDE_INSTALLER.read_text(encoding="utf-8")

    def test_trackside_is_a_self_contained_bar_variant(self):
        self.assertIn("commissioned for a", self.readme)
        for relative_path in (
            "timertest.py",
            "requirements.txt",
            "installer/configure.py",
            "installer/subway_catalog.json",
            "installer/wifi_setup.py",
            "installer/power_schedule.py",
            "installer/display-power.sh",
        ):
            self.assertTrue((TRACKSIDE_ROOT / relative_path).is_file())

    def test_trackside_has_large_readable_layout_and_no_service_panel(self):
        self.assertIn("TRACKSIDE_CLOCK_SIZE = 100", self.app)
        self.assertIn("TRACKSIDE_PRIMARY_TIME_SIZE = 76", self.app)
        self.assertIn("TRACKSIDE_PRIMARY_UNIT_SIZE = 76", self.app)
        self.assertIn("TRACKSIDE_SECONDARY_TIME_SIZE = 48", self.app)
        self.assertIn("TRACKSIDE_SECONDARY_UNIT_SIZE = 48", self.app)
        self.assertNotIn("self.status_card", self.app)
        self.assertNotIn("self.ticker_canvas", self.app)
        self.assertNotIn("self.ram_label", self.app)
        self.assertNotIn("self.disk_label", self.app)
        self.assertNotIn("self.load_label", self.app)

    def test_trackside_uses_five_day_forecast_and_compact_health(self):
        self.assertIn("daily=weather_code,temperature_2m_max,temperature_2m_min", self.app)
        self.assertIn("forecast_days=5", self.app)
        self.assertIn('self.system_label_map = {', self.app)
        self.assertIn('"cpu_temp": self.cpu_temp_label', self.app)
        self.assertIn('"uptime": self.uptime_label', self.app)
        self.assertIn('"ip": self.ip_label', self.app)
        self.assertIn('"network": self.net_label', self.app)
        self.assertNotIn('stats["ram"]', self.app)
        self.assertNotIn('stats["disk"]', self.app)
        self.assertNotIn('stats["load"]', self.app)
        self.assertNotIn('stats["download"]', self.app)
        self.assertNotIn('stats["upload"]', self.app)

    def test_trackside_installer_uses_isolated_names(self):
        self.assertIn('APP_DIR="$REPO_DIR/Train UI XL/Train UI XL Trackside"', self.installer)
        self.assertIn('TRAINUI_CONFIG_DIR="$HOME/.config/trainui-trackside"', self.installer)
        self.assertIn("trainui-trackside-wifi-setup.service", self.installer)
        self.assertIn("trainui-trackside-schedule", self.installer)
        self.assertNotIn('APP_DIR="$REPO_DIR/Train UI XL"', self.installer)


if __name__ == "__main__":
    unittest.main()
