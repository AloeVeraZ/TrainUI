#!/usr/bin/env python3
"""TrainUI Wi-Fi failover and local setup portal.

The installer places this file at /usr/local/sbin/trainui-wifi-setup and runs
it as a system service. NetworkManager gets the first chance to connect a
saved client profile. After 30 seconds offline, the service creates a
protected TrainUI access point and serves a small credential form at
http://10.42.0.1.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs

try:
    import fcntl
except ImportError:  # pragma: no cover - allows Windows development tests
    fcntl = None


CONFIG_PATH = Path(os.environ.get("TRAINUI_NETWORK_CONFIG", "/etc/trainui/network.json"))
LOCK_PATH = Path(os.environ.get("TRAINUI_NETWORK_LOCK", "/run/trainui-network.lock"))
HOTSPOT_PROFILE = "TrainUI-Setup"
HOTSPOT_SSID = "TrainUI"
HOTSPOT_PASSWORD = "TRAINUI1"
HOTSPOT_ADDRESS = "10.42.0.1"
DEFAULT_CONFIG = {
    "schema_version": 1,
    "preferred_uuid": "",
    "last_message": "",
    "last_error": "",
}


class NetworkError(RuntimeError):
    """A safe, user-displayable networking error."""


def _split_terse(line: str) -> list[str]:
    """Split escaped ``nmcli --terse`` output."""

    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for character in line.rstrip("\n"):
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields


def _validate_ssid(value: object) -> str:
    ssid = str(value or "").strip()
    if not ssid:
        raise NetworkError("Wi-Fi name is required")
    if "\x00" in ssid or "\n" in ssid or "\r" in ssid:
        raise NetworkError("Wi-Fi name contains unsupported characters")
    if len(ssid.encode("utf-8")) > 32:
        raise NetworkError("Wi-Fi names may contain at most 32 bytes")
    return ssid


def _validate_password(value: object) -> str:
    password = str(value or "")
    if "\x00" in password or "\n" in password or "\r" in password:
        raise NetworkError("Wi-Fi password contains unsupported characters")
    if not password:
        return ""
    if len(password) == 64 and all(character in "0123456789abcdefABCDEF" for character in password):
        return password
    if not 8 <= len(password) <= 63:
        raise NetworkError("Wi-Fi password must be blank for an open network or contain 8-63 characters")
    return password


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            for key in config:
                if key in saved:
                    config[key] = saved[key]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return config


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_name(f"{CONFIG_PATH.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, CONFIG_PATH)


@contextmanager
def network_file_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _require_root() -> None:
    if getattr(os, "geteuid", lambda: 0)() != 0:
        raise NetworkError("This network operation must run as root")


class NetworkManager:
    """Constrained NetworkManager operations used by the monitor and portal."""

    def __init__(self, runner: Callable | None = None, sleep: Callable = time.sleep) -> None:
        self._runner = runner or subprocess.run
        self._sleep = sleep
        self._operation_lock = threading.RLock()
        self._connect_busy = False

    def run(self, command: list[str], *, timeout: int = 15, check: bool = True):
        environment = dict(os.environ)
        environment["LC_ALL"] = "C"
        try:
            result = self._runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise NetworkError(f"Could not run {command[0]}: {error}") from error
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout or "command failed").strip()
            raise NetworkError(detail[:500])
        return result

    def nmcli(self, *arguments: str, timeout: int = 15, check: bool = True):
        return self.run(
            ["nmcli", "--terse", "--escape", "yes", *arguments],
            timeout=timeout,
            check=check,
        )

    def _devices(self) -> list[tuple[str, str]]:
        output = self.nmcli("--fields", "DEVICE,TYPE", "device", "status").stdout
        devices = []
        for line in output.splitlines():
            fields = _split_terse(line)
            if len(fields) >= 2:
                devices.append((fields[0], fields[1]))
        return devices

    def wifi_interface(self) -> str:
        for interface, kind in self._devices():
            if kind == "wifi":
                return interface
        raise NetworkError("No NetworkManager-controlled Wi-Fi interface was found")

    def _device_details(self, interface: str) -> dict:
        output = self.nmcli(
            "--fields",
            "GENERAL.STATE,GENERAL.CONNECTION,GENERAL.CON-UUID",
            "device",
            "show",
            interface,
        ).stdout
        details = {"state": "", "connection": "", "uuid": ""}
        mapping = {
            "GENERAL.STATE": "state",
            "GENERAL.CONNECTION": "connection",
            "GENERAL.CON-UUID": "uuid",
        }
        for line in output.splitlines():
            fields = _split_terse(line)
            if len(fields) >= 2 and fields[0] in mapping:
                details[mapping[fields[0]]] = fields[1]
        return details

    def _connection_mode(self, uuid: str) -> str:
        if not uuid or uuid == "--":
            return ""
        result = self.nmcli(
            "--get-values",
            "802-11-wireless.mode",
            "connection",
            "show",
            "uuid",
            uuid,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    def _ethernet_connected(self) -> bool:
        try:
            devices = self._devices()
        except NetworkError:
            return False
        for interface, kind in devices:
            if kind == "ethernet" and self._device_details(interface)["state"].startswith("100"):
                return True
        return False

    def status(self) -> dict:
        with self._operation_lock:
            config = load_config()
            try:
                interface = self.wifi_interface()
                details = self._device_details(interface)
                connection_mode = self._connection_mode(details["uuid"])
                if connection_mode == "ap" or details["connection"] == HOTSPOT_PROFILE:
                    mode = "hotspot"
                elif details["state"].startswith("100"):
                    mode = "client"
                elif self._ethernet_connected():
                    mode = "ethernet"
                else:
                    mode = "disconnected"
                wifi = {
                    "available": True,
                    "interface": interface,
                    "mode": mode,
                    "connection": "" if details["connection"] == "--" else details["connection"],
                    "uuid": "" if details["uuid"] == "--" else details["uuid"],
                }
            except NetworkError as error:
                mode = "ethernet" if self._ethernet_connected() else "unavailable"
                wifi = {
                    "available": False,
                    "interface": "",
                    "mode": mode,
                    "connection": "",
                    "uuid": "",
                    "error": str(error),
                }
            return {
                "wifi": wifi,
                "hotspot_ssid": HOTSPOT_SSID,
                "hotspot_password": HOTSPOT_PASSWORD,
                "hotspot_url": f"http://{HOTSPOT_ADDRESS}",
                "last_message": config.get("last_message", ""),
                "last_error": config.get("last_error", ""),
            }

    def initialize(self) -> dict:
        _require_root()
        config = load_config()
        try:
            interface = self.wifi_interface()
            details = self._device_details(interface)
            mode = self._connection_mode(details["uuid"])
            if details["state"].startswith("100") and mode != "ap" and details["uuid"] != "--":
                config["preferred_uuid"] = details["uuid"]
                config["last_message"] = "Saved the current Raspberry Pi Imager Wi-Fi as preferred."
                config["last_error"] = ""
        except NetworkError as error:
            config["last_error"] = f"Initial Wi-Fi capture: {error}"
        save_config(config)
        return self.status()

    def _profile_name(self, ssid: str) -> str:
        digest = hashlib.sha256(ssid.encode("utf-8")).hexdigest()[:10]
        return f"TrainUI-WiFi-{digest}"

    def _delete_profile(self, profile: str) -> None:
        self.nmcli("connection", "delete", "id", profile, check=False)

    @contextmanager
    def _password_file(self, setting: str, secret: str):
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="trainui-secret-",
            dir="/run",
            delete=False,
        )
        try:
            os.chmod(handle.name, 0o600)
            handle.write(f"{setting}:{secret}\n")
            handle.flush()
            handle.close()
            yield handle.name
        finally:
            try:
                os.unlink(handle.name)
            except FileNotFoundError:
                pass

    def start_hotspot(self) -> None:
        _require_root()
        with self._operation_lock, network_file_lock():
            interface = self.wifi_interface()
            config = load_config()
            self._start_hotspot_locked(interface, config)

    def _start_hotspot_locked(self, interface: str, config: dict) -> None:
        """Create the AP while the caller owns both network-operation locks."""

        self._delete_profile(HOTSPOT_PROFILE)
        self.nmcli(
            "connection",
            "add",
            "type",
            "wifi",
            "ifname",
            interface,
            "con-name",
            HOTSPOT_PROFILE,
            "ssid",
            HOTSPOT_SSID,
        )
        try:
            self.nmcli(
                "connection",
                "modify",
                "id",
                HOTSPOT_PROFILE,
                "connection.autoconnect",
                "no",
                "connection.autoconnect-priority",
                "-999",
                "802-11-wireless.mode",
                "ap",
                "802-11-wireless.band",
                "bg",
                "ipv4.method",
                "shared",
                "ipv4.addresses",
                f"{HOTSPOT_ADDRESS}/24",
                "ipv6.method",
                "disabled",
                "802-11-wireless-security.key-mgmt",
                "wpa-psk",
            )
            with self._password_file(
                "802-11-wireless-security.psk", HOTSPOT_PASSWORD
            ) as secret_file:
                self.nmcli(
                    "--wait",
                    "25",
                    "connection",
                    "up",
                    "id",
                    HOTSPOT_PROFILE,
                    "ifname",
                    interface,
                    "passwd-file",
                    secret_file,
                    timeout=30,
                )
        except NetworkError:
            self._delete_profile(HOTSPOT_PROFILE)
            raise
        config["last_message"] = (
            f"Setup hotspot {HOTSPOT_SSID} is active at http://{HOTSPOT_ADDRESS}."
        )
        config["last_error"] = ""
        save_config(config)

    def connect(self, ssid_value: object, password_value: object) -> None:
        _require_root()
        ssid = _validate_ssid(ssid_value)
        password = _validate_password(password_value)
        profile = self._profile_name(ssid)
        with self._operation_lock, network_file_lock():
            interface = self.wifi_interface()
            config = load_config()
            self._delete_profile(profile)
            self.nmcli(
                "connection",
                "add",
                "type",
                "wifi",
                "ifname",
                interface,
                "con-name",
                profile,
                "ssid",
                ssid,
            )
            failure: NetworkError | None = None
            try:
                self.nmcli(
                    "connection",
                    "modify",
                    "id",
                    profile,
                    "connection.autoconnect",
                    "yes",
                    "connection.autoconnect-priority",
                    "100",
                    "connection.autoconnect-retries",
                    "0",
                    "ipv4.method",
                    "auto",
                    "ipv6.method",
                    "auto",
                )
                secret_setting = ""
                if password:
                    self.nmcli(
                        "connection",
                        "modify",
                        "id",
                        profile,
                        "802-11-wireless-security.key-mgmt",
                        "wpa-psk",
                    )
                    secret_setting = "802-11-wireless-security.psk"
                self.nmcli("connection", "down", "id", HOTSPOT_PROFILE, check=False)
                if secret_setting:
                    with self._password_file(secret_setting, password) as secret_file:
                        self.nmcli(
                            "--wait",
                            "35",
                            "connection",
                            "up",
                            "id",
                            profile,
                            "ifname",
                            interface,
                            "passwd-file",
                            secret_file,
                            timeout=40,
                        )
                else:
                    self.nmcli(
                        "--wait",
                        "35",
                        "connection",
                        "up",
                        "id",
                        profile,
                        "ifname",
                        interface,
                        timeout=40,
                    )
            except NetworkError as error:
                self._delete_profile(profile)
                config["last_message"] = ""
                config["last_error"] = f"Could not connect to {ssid}: {error}"
                save_config(config)
                failure = error
            if failure is None:
                details = self._device_details(interface)
                config["preferred_uuid"] = "" if details["uuid"] == "--" else details["uuid"]
                config["last_message"] = f"Connected to {ssid}."
                config["last_error"] = ""
                save_config(config)
            else:
                # Restore the portal before releasing the operation lock. This
                # prevents the monitor from racing the recovery and recreating
                # the hotspot a second time after a long failed attempt.
                try:
                    self._start_hotspot_locked(interface, config)
                except NetworkError:
                    pass
                config["last_message"] = ""
                config["last_error"] = f"Could not connect to {ssid}: {failure}"
                save_config(config)
        if failure is not None:
            raise failure

    def retry_saved_connection(self) -> None:
        """Try the preferred profile, then let NetworkManager choose any saved one."""

        interface = self.wifi_interface()
        self.nmcli("radio", "wifi", "on", check=False)
        preferred = str(load_config().get("preferred_uuid", "")).strip()
        if preferred:
            result = self.nmcli(
                "--wait",
                "5",
                "connection",
                "up",
                "uuid",
                preferred,
                "ifname",
                interface,
                timeout=8,
                check=False,
            )
            if result.returncode == 0:
                return
        self.nmcli(
            "--wait",
            "5",
            "device",
            "connect",
            interface,
            timeout=8,
            check=False,
        )

    def queue_connection(self, ssid: str, password: str) -> bool:
        with self._operation_lock:
            if self._connect_busy:
                return False
            self._connect_busy = True

        def worker() -> None:
            try:
                # Give the browser enough time to receive the confirmation page
                # before the hotspot is intentionally taken down.
                self._sleep(1.25)
                self.connect(ssid, password)
            except NetworkError:
                pass
            finally:
                with self._operation_lock:
                    self._connect_busy = False

        threading.Thread(target=worker, name="trainui-wifi-connect", daemon=True).start()
        return True

    def watch(
        self,
        timeout_seconds: int = 30,
        mode_callback: Callable[[str], None] | None = None,
    ) -> None:
        _require_root()
        deadline = time.monotonic() + timeout_seconds
        next_connection_attempt = 0.0
        while True:
            mode = self.status()["wifi"]["mode"]
            if mode_callback is not None:
                mode_callback(mode)
            if mode in {"client", "ethernet", "hotspot"}:
                deadline = time.monotonic() + timeout_seconds
            else:
                now = time.monotonic()
                if now >= deadline:
                    try:
                        self.start_hotspot()
                    except NetworkError as error:
                        config = load_config()
                        config["last_message"] = ""
                        config["last_error"] = f"Automatic setup hotspot failed: {error}"
                        save_config(config)
                        deadline = time.monotonic() + timeout_seconds
                elif now >= next_connection_attempt:
                    try:
                        self.retry_saved_connection()
                    except NetworkError as error:
                        config = load_config()
                        config["last_error"] = f"Saved Wi-Fi retry: {error}"
                        save_config(config)
                    next_connection_attempt = time.monotonic() + 5
            self._sleep(2)


def render_setup_page(error: str = "") -> str:
    error_markup = f"<p class=error>{html.escape(error)}</p>" if error else ""
    return f"""<!doctype html>
<html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>TrainUI Wi-Fi Setup</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#030914;color:#f5f8ff;font:17px system-ui,sans-serif}}
main{{max-width:560px;margin:0 auto;padding:42px 20px}}.card{{background:#071321;border:1px solid #203555;border-radius:18px;padding:26px}}
h1{{font-size:30px;margin:0 0 8px}}p{{color:#a9bbd8;line-height:1.5}}label{{display:block;font-weight:750;margin:20px 0 8px}}
input{{width:100%;padding:13px;border:2px solid #526b91;border-radius:9px;background:#fff;color:#111;font:inherit}}
button{{width:100%;margin-top:25px;padding:14px;border:0;border-radius:9px;background:#f5f8ff;color:#071321;font:800 18px system-ui}}
.small{{font-size:14px}}.error{{padding:12px;border-radius:9px;background:#4a1720;color:#ffdbe1;font-weight:700}}
</style></head><body><main><section class=card><h1>Connect TrainUI</h1>
<p>Enter the Wi-Fi name and password TrainUI should use. Leave the password blank only for an open network.</p>
{error_markup}
<form method=post action=/connect autocomplete=on>
<label for=ssid>Wi-Fi name (SSID)</label><input id=ssid name=ssid maxlength=32 required autofocus>
<label for=password>Wi-Fi password</label><input id=password name=password type=password maxlength=64>
<button type=submit>Save and connect</button></form>
<p class=small>The TrainUI network will close while the Pi tries these details. Rejoin your normal Wi-Fi afterward.</p>
</section></main></body></html>"""


def render_connecting_page(ssid: str) -> str:
    safe_ssid = html.escape(ssid)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Connecting</title>
<style>body{{background:#030914;color:#f5f8ff;font:18px system-ui;margin:0}}main{{max-width:560px;margin:60px auto;padding:24px}}
div{{background:#071321;border:1px solid #203555;border-radius:18px;padding:28px}}p{{color:#a9bbd8;line-height:1.5}}</style>
</head><body><main><div><h1>Wi-Fi saved</h1><p>TrainUI is connecting to <strong>{safe_ssid}</strong> now.</p>
<p>Reconnect this phone or computer to that Wi-Fi. If the details do not work, the <strong>{HOTSPOT_SSID}</strong> setup network will return so you can try again.</p>
</div></main></body></html>"""


class PortalHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], manager: NetworkManager):
        self.manager = manager
        super().__init__(address, PortalHandler)


class PortalHandler(BaseHTTPRequestHandler):
    server: PortalHTTPServer

    def _send_html(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        error = str(load_config().get("last_error", ""))
        self._send_html(render_setup_page(error))

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path.split("?", 1)[0] != "/connect":
            self._send_html(render_setup_page("That setup action was not found."), 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > 8192:
            self._send_html(render_setup_page("The submitted form was empty or too large."), 400)
            return
        try:
            form = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
            ssid = _validate_ssid(form.get("ssid", [""])[0])
            password = _validate_password(form.get("password", [""])[0])
        except (UnicodeDecodeError, NetworkError) as error:
            self._send_html(render_setup_page(str(error)), 400)
            return
        if not self.server.manager.queue_connection(ssid, password):
            self._send_html(render_setup_page("Another Wi-Fi connection attempt is already running."), 409)
            return
        self._send_html(render_connecting_page(ssid), 202)

    def log_message(self, format_string: str, *args: object) -> None:
        # Avoid writing request paths or submitted values to the system journal.
        sys.stderr.write(f"[TrainUI Wi-Fi] request from {self.client_address[0]}\n")


class PortalController:
    def __init__(self, manager: NetworkManager, port: int = 80) -> None:
        self.manager = manager
        self.port = port
        self.server: PortalHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def sync(self, mode: str) -> None:
        if mode == "hotspot" and self.server is None:
            try:
                self.server = PortalHTTPServer((HOTSPOT_ADDRESS, self.port), self.manager)
            except OSError as error:
                config = load_config()
                config["last_error"] = f"Could not open the setup webpage: {error}"
                save_config(config)
                self.server = None
                return
            self.thread = threading.Thread(
                target=self.server.serve_forever,
                name="trainui-wifi-portal",
                daemon=True,
            )
            self.thread.start()
        elif mode != "hotspot" and self.server is not None:
            self.stop()

    def stop(self) -> None:
        if self.server is None:
            return
        self.server.shutdown()
        self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)
        self.server = None
        self.thread = None


def read_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        raise NetworkError(f"Invalid request data: {error}") from error
    if not isinstance(payload, dict):
        raise NetworkError("Request data must be a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TrainUI Wi-Fi setup service")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("init")
    subparsers.add_parser("connect")
    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("--timeout", type=int, default=30)
    watch_parser.add_argument("--port", type=int, default=80)
    args = parser.parse_args(argv)
    manager = NetworkManager()
    try:
        if args.command == "status":
            result = manager.status()
        elif args.command == "init":
            result = manager.initialize()
        elif args.command == "connect":
            payload = read_payload()
            manager.connect(payload.get("ssid"), payload.get("password"))
            result = manager.status()
        else:
            if not 5 <= args.timeout <= 300:
                raise NetworkError("Failover timeout must be 5-300 seconds")
            if not 1 <= args.port <= 65535:
                raise NetworkError("Portal port must be 1-65535")
            portal = PortalController(manager, args.port)
            try:
                manager.watch(args.timeout, portal.sync)
            finally:
                portal.stop()
            return 0
        print(json.dumps({"ok": True, **result}))
        return 0
    except NetworkError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
