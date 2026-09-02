import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "installer" / "power_schedule.py"
SPEC = importlib.util.spec_from_file_location("trainui_power_schedule", MODULE_PATH)
power_schedule = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(power_schedule)


class PowerScheduleTests(unittest.TestCase):
    def test_terminal_help_explains_requested_input_formats(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("[Y/N]", source)
        self.assertNotIn("Y/N or 1/2", source)
        self.assertNotIn("You may also type", source)
        self.assertIn("24-hour clock", source)
        for example in ("2300 = 11:00 PM", "0800 = 8:00 AM", "2400 = midnight"):
            self.assertIn(example, source)

    def test_accepts_only_four_digit_24_hour_input(self):
        cases = {
            "0000": "00:00",
            "0800": "08:00",
            "2359": "23:59",
            "2400": "00:00",
        }
        for entered, expected in cases.items():
            with self.subTest(entered=entered):
                self.assertEqual(power_schedule.parse_time(entered), expected)

    def test_rejects_invalid_times(self):
        for entered in (
            "8",
            "800",
            "8:00",
            "08:00",
            "23:00",
            "23.00",
            "2360",
            "2401",
            "2500",
            "noon",
        ):
            with self.subTest(entered=entered):
                with self.assertRaises(ValueError):
                    power_schedule.parse_time(entered)

    def test_accepts_only_y_or_n(self):
        self.assertTrue(power_schedule.parse_yes_no("Y"))
        self.assertFalse(power_schedule.parse_yes_no("N"))
        for entered in ("yes", "no", "1", "2", "maybe"):
            with self.subTest(entered=entered):
                with self.assertRaises(ValueError):
                    power_schedule.parse_yes_no(entered)

    def test_existing_normalized_config_times_remain_compatible(self):
        self.assertEqual(power_schedule.normalize_time("23:00"), "23:00")
        self.assertEqual(power_schedule.normalize_time("08:00"), "08:00")
        self.assertEqual(power_schedule.display_time("23:00"), "2300")
        self.assertEqual(power_schedule.display_time("0800"), "0800")

    def test_unchanged_existing_schedule_matches_compact_user_input(self):
        current = {
            "enabled": True,
            "sleep_time": "23:00",
            "wake_time": "08:00",
            "user": "trainui",
            "home": "/home/trainui",
        }
        desired = {
            **current,
            "sleep_time": "2300",
            "wake_time": "0800",
        }
        self.assertTrue(power_schedule.configs_match(current, desired))

    def test_unchanged_interactive_schedule_skips_sudo_and_systemd_rewrite(self):
        current = {
            "enabled": True,
            "sleep_time": "23:00",
            "wake_time": "08:00",
            "user": "trainui",
            "home": "/home/trainui",
        }
        with (
            mock.patch.object(power_schedule, "read_config", return_value=current),
            mock.patch.object(
                power_schedule,
                "resolve_identity",
                return_value=("trainui", "/home/trainui"),
            ),
            mock.patch("builtins.input", side_effect=("Y", "2300", "0800")),
            mock.patch.object(power_schedule, "elevate_with_config") as elevate,
            mock.patch.object(power_schedule, "apply_config") as apply,
        ):
            self.assertEqual(power_schedule.main([]), 0)
        elevate.assert_not_called()
        apply.assert_not_called()

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
