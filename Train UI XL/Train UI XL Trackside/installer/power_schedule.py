#!/usr/bin/env python3
"""Configure TrainUI's repeating display sleep and wake timers."""

from __future__ import annotations

import argparse
from datetime import datetime
import getpass
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import pwd
except ImportError:  # Allows the parser tests to run on the Windows dev host.
    pwd = None


CONFIG_PATH = Path("/etc/trainui-trackside/power-schedule.json")
ENV_PATH = Path("/etc/trainui-trackside/power-schedule.env")
SYSTEMD_DIR = Path("/etc/systemd/system")
TIMER_NAMES = ("trainui-trackside-sleep.timer", "trainui-trackside-wake.timer")


def parse_time(value: str) -> str:
    """Validate user-entered HHMM and return the stored HH:MM form."""
    cleaned = value.strip()
    if len(cleaned) != 4 or not cleaned.isdigit():
        raise ValueError("Use exactly four digits: for example, 2300 or 0800.")
    hour_text, minute_text = cleaned[:2], cleaned[2:]

    hour = int(hour_text)
    minute = int(minute_text)
    if hour == 24 and minute == 0:
        hour = 0
    elif not 0 <= hour <= 23:
        raise ValueError("The hour must be from 00 through 23 (or 24 only in 2400).")
    if not 0 <= minute <= 59:
        raise ValueError("The minutes must be from 00 through 59.")
    return f"{hour:02d}:{minute:02d}"


def normalize_time(value: str) -> str:
    """Accept stored HH:MM values while keeping terminal input HHMM-only."""
    cleaned = value.strip()
    if len(cleaned) == 5 and cleaned[2] == ":":
        compact = cleaned.replace(":", "", 1)
        return parse_time(compact)
    return parse_time(cleaned)


def display_time(value: str) -> str:
    return normalize_time(value).replace(":", "")


def parse_yes_no(value: str) -> bool:
    cleaned = value.strip().lower()
    if cleaned == "y":
        return True
    if cleaned == "n":
        return False
    raise ValueError("Enter Y for yes or N for no.")


def timer_override(clock_time: str) -> str:
    return (
        "[Timer]\n"
        "OnCalendar=\n"
        f"OnCalendar=*-*-* {clock_time}:00\n"
    )


def schedule_is_sleeping(now: str, sleep_time: str, wake_time: str) -> bool:
    """Return whether HH:MM falls inside the daily sleep interval."""
    current = normalize_time(now)
    sleep = normalize_time(sleep_time)
    wake = normalize_time(wake_time)
    if sleep == wake:
        raise ValueError("Sleep and wake times must be different.")
    if sleep < wake:
        return sleep <= current < wake
    return current >= sleep or current < wake


def atomic_write(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def systemd_environment_value(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def read_config(path: Path = CONFIG_PATH) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def configs_match(current: dict[str, object] | None, desired: dict[str, object]) -> bool:
    if current is None:
        return False
    try:
        return (
            bool(current["enabled"]) == bool(desired["enabled"])
            and normalize_time(str(current["sleep_time"]))
            == normalize_time(str(desired["sleep_time"]))
            and normalize_time(str(current["wake_time"]))
            == normalize_time(str(desired["wake_time"]))
            and str(current["user"]) == str(desired["user"])
            and str(current["home"]) == str(desired["home"])
        )
    except (KeyError, TypeError, ValueError):
        return False


def run_systemctl(*arguments: str) -> None:
    subprocess.run(["systemctl", *arguments], check=True)


def apply_config(
    config: dict[str, object],
    *,
    config_path: Path = CONFIG_PATH,
    env_path: Path = ENV_PATH,
    systemd_dir: Path = SYSTEMD_DIR,
    use_systemctl: bool = True,
) -> None:
    enabled = bool(config["enabled"])
    sleep_time = normalize_time(str(config["sleep_time"]))
    wake_time = normalize_time(str(config["wake_time"]))
    if sleep_time == wake_time:
        raise ValueError("Sleep and wake times must be different.")

    owner = str(config["user"])
    home = str(config["home"])
    normalized = {
        "enabled": enabled,
        "sleep_time": sleep_time,
        "wake_time": wake_time,
        "user": owner,
        "home": home,
    }
    atomic_write(config_path, json.dumps(normalized, indent=2) + "\n")
    atomic_write(
        env_path,
        f"TRAINUI_USER={systemd_environment_value(owner)}\n"
        f"TRAINUI_HOME={systemd_environment_value(home)}\n",
    )

    schedule_values = {
        "trainui-trackside-sleep.timer": sleep_time,
        "trainui-trackside-wake.timer": wake_time,
    }
    for timer_name, clock_time in schedule_values.items():
        override_path = systemd_dir / f"{timer_name}.d" / "schedule.conf"
        atomic_write(override_path, timer_override(clock_time))

    if not use_systemctl:
        return

    run_systemctl("daemon-reload")
    run_systemctl("enable", "trainui-trackside-schedule-sync.service")
    if enabled:
        for timer_name in TIMER_NAMES:
            run_systemctl("enable", timer_name)
            run_systemctl("restart", timer_name)
        run_systemctl("start", "trainui-trackside-schedule-sync.service")
    else:
        run_systemctl("disable", "--now", *TIMER_NAMES)
        # Disabling the schedule should never leave the display asleep.
        run_systemctl("start", "trainui-trackside-wake.service")


def prompt_yes_no(prompt: str) -> bool:
    while True:
        try:
            return parse_yes_no(input(prompt))
        except ValueError as error:
            print(error)


def prompt_time(prompt: str, default: str | None = None) -> str:
    while True:
        suffix = f" [{display_time(default)}]" if default else ""
        entered = input(f"{prompt}{suffix}: ").strip()
        if not entered and default:
            return default
        try:
            return parse_time(entered)
        except ValueError as error:
            print(error)


def resolve_identity(owner: str | None, home: str | None) -> tuple[str, str]:
    resolved_owner = owner or os.environ.get("SUDO_USER") or getpass.getuser()
    if home:
        resolved_home = home
    else:
        try:
            if pwd is None:
                raise KeyError(resolved_owner)
            resolved_home = pwd.getpwnam(resolved_owner).pw_dir
        except KeyError:
            resolved_home = os.path.expanduser("~")
    return resolved_owner, resolved_home


def elevate_if_needed(arguments: list[str]) -> None:
    if os.geteuid() == 0:
        return
    owner = getpass.getuser()
    home = os.path.expanduser("~")
    os.execvp(
        "sudo",
        [
            "sudo",
            sys.executable,
            str(Path(__file__).resolve()),
            "--owner",
            owner,
            "--home",
            home,
            *arguments,
        ],
    )


def elevate_with_config(config: dict[str, object]) -> None:
    if os.geteuid() == 0:
        return
    print("Administrator access is needed to save the schedule.")
    print("Type your password and press Enter. Nothing is shown while you type.", flush=True)
    os.execvp(
        "sudo",
        [
            "sudo",
            sys.executable,
            str(Path(__file__).resolve()),
            "--set-enabled",
            "yes" if bool(config["enabled"]) else "no",
            "--sleep-time",
            str(config["sleep_time"]),
            "--wake-time",
            str(config["wake_time"]),
            "--owner",
            str(config["user"]),
            "--home",
            str(config["home"]),
        ],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Set TrainUI's repeating daily display sleep and wake times."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--initial", action="store_true", help=argparse.SUPPRESS)
    mode.add_argument("--apply-existing", action="store_true", help=argparse.SUPPRESS)
    mode.add_argument("--disable", action="store_true", help=argparse.SUPPRESS)
    mode.add_argument("--sync-state", action="store_true", help=argparse.SUPPRESS)
    mode.add_argument("--set-enabled", choices=("yes", "no"), help=argparse.SUPPRESS)
    parser.add_argument("--sleep-time", help=argparse.SUPPRESS)
    parser.add_argument("--wake-time", help=argparse.SUPPRESS)
    parser.add_argument("--owner", help=argparse.SUPPRESS)
    parser.add_argument("--home", help=argparse.SUPPRESS)
    return parser


def main(arguments: list[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if arguments is None else arguments)
    args = build_parser().parse_args(raw_arguments)
    owner, home = resolve_identity(args.owner, args.home)
    current = read_config()

    if args.sync_state:
        if current is None or not bool(current.get("enabled")):
            return 0
        action = "trainui-trackside-sleep.service" if schedule_is_sleeping(
            datetime.now().strftime("%H:%M"),
            str(current["sleep_time"]),
            str(current["wake_time"]),
        ) else "trainui-trackside-wake.service"
        run_systemctl("start", action)
        return 0

    if args.set_enabled is not None:
        elevate_if_needed(raw_arguments)
        if args.sleep_time is None or args.wake_time is None:
            print("The internal schedule update is missing a time.", file=sys.stderr)
            return 2
        config = {
            "enabled": args.set_enabled == "yes",
            "sleep_time": normalize_time(args.sleep_time),
            "wake_time": normalize_time(args.wake_time),
            "user": owner,
            "home": home,
        }
        apply_config(config)
        if bool(config["enabled"]):
            print(
                f"Daily sleep is set for {display_time(str(config['sleep_time']))}; "
                f"wake is set for {display_time(str(config['wake_time']))}."
            )
        else:
            print("Daily TrainUI sleep is disabled. The display will stay on.")
        print("Run trainui-trackside-schedule at any time to change this setting.")
        return 0

    if args.apply_existing:
        elevate_if_needed(raw_arguments)
        if current is None:
            print("No TrainUI sleep schedule has been configured yet.", file=sys.stderr)
            return 1
        current["user"] = owner
        current["home"] = home
        apply_config(current)
        return 0

    if args.disable:
        elevate_if_needed(raw_arguments)
        config = {
            "enabled": False,
            "sleep_time": "23:00",
            "wake_time": "08:00",
            "user": owner,
            "home": home,
        }
        apply_config(config)
        print("Daily TrainUI sleep is disabled. The display will stay on.")
        return 0

    print("\nTrainUI daily display sleep")
    print("This repeats every day using the Pi's local time and the 24-hour clock.")
    print("Enter exactly four digits, with hours first and then minutes:")
    print("2300 = 11:00 PM, 0800 = 8:00 AM, and 2400 = midnight.\n")

    enabled = prompt_yes_no("Enable automatic daily sleep and wake? [Y/N]: ")
    previous_sleep = str(current.get("sleep_time", "23:00")) if current else None
    previous_wake = str(current.get("wake_time", "08:00")) if current else None
    if enabled:
        sleep_time = prompt_time("Sleep time", previous_sleep)
        while True:
            wake_time = prompt_time("Wake time", previous_wake)
            if wake_time != sleep_time:
                break
            print("Sleep and wake times must be different.")
    else:
        sleep_time = normalize_time(previous_sleep or "23:00")
        wake_time = normalize_time(previous_wake or "08:00")

    config = {
        "enabled": enabled,
        "sleep_time": sleep_time,
        "wake_time": wake_time,
        "user": owner,
        "home": home,
    }
    if configs_match(current, config):
        print("The daily display setting is unchanged; nothing needs to be reinstalled.")
        print("Run trainui-trackside-schedule at any time to change this setting.")
        return 0
    elevate_with_config(config)
    apply_config(config)
    if enabled:
        print(
            f"Daily sleep is set for {display_time(sleep_time)}; "
            f"wake is set for {display_time(wake_time)}."
        )
        print("The Pi remains powered so it can wake the display automatically.")
    else:
        print("Daily TrainUI sleep is disabled. The display will stay on.")
    print("Run trainui-trackside-schedule at any time to change this setting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
