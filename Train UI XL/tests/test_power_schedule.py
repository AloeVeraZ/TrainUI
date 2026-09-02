import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "installer" / "power_schedule.py"
SPEC = importlib.util.spec_from_file_location("trainui_power_schedule", MODULE_PATH)
power_schedule = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(power_schedule)


class PowerScheduleTests(unittest.TestCase):
    def test_terminal_help_explains_requested_input_formats(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("[Y/N or 1/2]", source)
        self.assertIn("24-hour clock", source)
        for example in ("2300 = 11:00 PM", "0800 = 8:00 AM", "2400 = midnight"):
            self.assertIn(example, source)

    def test_accepts_four_digit_and_colon_24_hour_times(self):
        cases = {
            "0000": "00:00",
            "0800": "08:00",
            "23:59": "23:59",
            "2400": "00:00",
            "24:00": "00:00",
        }
        for entered, expected in cases.items():
            with self.subTest(entered=entered):
                self.assertEqual(power_schedule.parse_time(entered), expected)

    def test_rejects_invalid_times(self):
        for entered in ("8", "800", "8:00", "2360", "2401", "2500", "noon"):
            with self.subTest(entered=entered):
                with self.assertRaises(ValueError):
                    power_schedule.parse_time(entered)

    def test_accepts_both_requested_yes_no_styles(self):
        for entered in ("Y", "yes", "1"):
            self.assertTrue(power_schedule.parse_yes_no(entered))
        for entered in ("N", "no", "2"):
            self.assertFalse(power_schedule.parse_yes_no(entered))
        with self.assertRaises(ValueError):
            power_schedule.parse_yes_no("maybe")

    def test_overnight_sleep_interval(self):
        self.assertTrue(power_schedule.schedule_is_sleeping("23:30", "23:00", "08:00"))
        self.assertTrue(power_schedule.schedule_is_sleeping("07:59", "23:00", "08:00"))
        self.assertFalse(power_schedule.schedule_is_sleeping("08:00", "23:00", "08:00"))
        self.assertFalse(power_schedule.schedule_is_sleeping("12:00", "23:00", "08:00"))

    def test_daytime_sleep_interval(self):
        self.assertTrue(power_schedule.schedule_is_sleeping("12:00", "09:00", "17:00"))
        self.assertFalse(power_schedule.schedule_is_sleeping("18:00", "09:00", "17:00"))

    def test_apply_config_writes_normalized_config_and_timer_overrides(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_path = root / "etc" / "trainui" / "power-schedule.json"
            env_path = root / "etc" / "trainui" / "power-schedule.env"
            systemd_dir = root / "etc" / "systemd" / "system"

            power_schedule.apply_config(
                {
                    "enabled": True,
                    "sleep_time": "2400",
                    "wake_time": "0800",
                    "user": "trainui",
                    "home": "/home/trainui",
                },
                config_path=config_path,
                env_path=env_path,
                systemd_dir=systemd_dir,
                use_systemctl=False,
            )

            self.assertIn('"sleep_time": "00:00"', config_path.read_text())
            self.assertIn('TRAINUI_USER="trainui"', env_path.read_text())
            sleep_override = (
                systemd_dir / "trainui-sleep.timer.d" / "schedule.conf"
            ).read_text()
            wake_override = (
                systemd_dir / "trainui-wake.timer.d" / "schedule.conf"
            ).read_text()
            self.assertIn("OnCalendar=*-*-* 00:00:00", sleep_override)
            self.assertIn("OnCalendar=*-*-* 08:00:00", wake_override)


if __name__ == "__main__":
    unittest.main()
