<div align="center">

# 🚇 TrainUI

### A fullscreen, always-on NYC D train departure board for Raspberry Pi

Live arrivals · Service alerts · Local weather · System status

[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-OS-C51A4A?logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/software/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MTA](https://img.shields.io/badge/Data-MTA%20GTFS--Realtime-0039A6)](https://new.mta.info/developers)

</div>

TrainUI turns a Raspberry Pi and display into a dedicated departure board for **Bay 50 St** in Brooklyn. It starts automatically, rotates the display 270°, stays fullscreen, and uses live public data—no API keys required.

## Before you install

Set these options while writing Raspberry Pi OS with [Raspberry Pi Imager](https://www.raspberrypi.com/software/):

- Connect the Pi to **Wi-Fi or Ethernet with internet access**.
- **Enable SSH**.
- Create a username and password. The username can be anything, but it must have `sudo` access.
- Choose any hostname you like, such as `trainui.local`.
- Attach the display before the first TrainUI boot.

> [!IMPORTANT]
> The hostname, username, Wi-Fi network name, and IP address do **not** need to match the project. You only need the hostname or IP address to SSH into your own Pi.

**Recommended:** Raspberry Pi OS (64-bit) with Desktop. Raspberry Pi OS Lite is also supported; the installer will add a desktop environment, so installation takes longer.

## One-command installation

SSH into the Pi from another computer:

```bash
ssh YOUR_USERNAME@YOUR_PI_HOSTNAME.local
```

Then run:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/installer/install.sh | bash
```

Do **not** add `sudo` before the command. The installer asks for your password when elevated access is needed, completes the entire setup, and reboots the Pi.

After reboot, TrainUI launches automatically in fullscreen and applies a 270° display rotation.

## What the installer does

The installer:

1. Installs the desktop, display, Python, font, and networking dependencies.
2. Clones this repository into `~/TrainUI`.
3. Creates an isolated Python environment and installs [`requirements.txt`](requirements.txt).
4. Validates the Python source and required imports.
5. Creates `~/TrainUI/run_trainui.sh` to rotate the active display and launch the app.
6. Registers desktop autostart for both current Wayland/labwc and older X11 Raspberry Pi OS releases.
7. Disables Wi-Fi power saving and enables automatic reconnection checks.
8. Enables desktop auto-login and prevents desktop, console, and system sleep blanking.
9. Reboots the Pi.

Running the install command again updates an existing installation. A clean checkout is updated in place. If the app folder contains local edits, local commits, or a damaged checkout, the installer preserves the old folder as a timestamped `~/TrainUI.backup.*` directory and installs a fresh copy automatically.

## Always-on reliability

TrainUI is configured as a dedicated kiosk during installation:

- Wi-Fi power saving is disabled globally and on every detected wireless interface.
- Saved NetworkManager Wi-Fi profiles are set to reconnect indefinitely.
- A lightweight systemd timer checks the interface every 30 seconds and reconnects it only when it has dropped.
- Raspberry Pi desktop blanking and console blanking are disabled.
- X11 screensaver/DPMS, system login idle actions, suspend, and hibernation are disabled.
- The launcher keeps the active Wayland or X11 display awake while TrainUI runs.

The watchdog reuses the Wi-Fi credentials already saved by Raspberry Pi OS; the repository and watchdog contain no SSID or password. No software can guarantee connectivity when the router, internet service, power, or Wi-Fi signal is unavailable, but TrainUI will automatically recover when the saved network becomes available again.

## Data and defaults

| Feature | Default |
|---|---|
| Station | Bay 50 St, Brooklyn |
| Train | D train |
| Northbound stop | `B23N` |
| Southbound stop | `B23S` |
| Weather location | `40.587, -73.984` |
| Train refresh | Every 30 seconds |
| Rotation | 270° |
| API keys | None |

Arrival and alert data comes from the MTA's public GTFS-Realtime feeds. Weather comes from Open-Meteo.

## Useful commands

View the live runtime log:

```bash
tail -f ~/TrainUI/trainui.log
```

Check the automatic Wi-Fi recovery timer:

```bash
systemctl status trainui-connectivity.timer
sudo journalctl -u trainui-connectivity.service --since today
```

Restart the interface without rebooting:

```bash
pkill -f timertest.py || true
~/TrainUI/run_trainui.sh &
```

Update or reinstall TrainUI by rerunning the one-command installer. It refreshes the repository and Python environment, then reboots. If you edited files directly on the Pi, your previous folder is retained as `~/TrainUI.backup.*` while the current GitHub version is installed cleanly.

## Customizing the station

The station name, stop IDs, coordinates, feed URLs, refresh intervals, colors, and layout constants are grouped near the top of [`timertest.py`](timertest.py). Changing stations may also require selecting the correct MTA feed URL for that subway line.

After editing the file on the Pi, reboot to reload it:

```bash
sudo reboot
```

## Troubleshooting

**The SSH connection fails**

Confirm the Pi is powered on, connected to the same network, and that SSH was enabled in Raspberry Pi Imager. Try the Pi's IP address if `.local` hostname discovery is unavailable:

```bash
ssh YOUR_USERNAME@192.168.1.123
```

**TrainUI does not appear after reboot**

Inspect the log:

```bash
tail -n 100 ~/TrainUI/trainui.log
```

Also confirm the Pi reaches the graphical desktop and has internet access.

**The screen is rotated the wrong way**

The supplied display setup expects 270°. Edit `--transform 270` and `--rotate left` in `~/TrainUI/run_trainui.sh` if your screen is mounted differently. That runner is regenerated whenever the installer runs.

**Arrival data is unavailable**

Check internet access and the runtime log. TrainUI starts even if the MTA endpoint is temporarily unavailable and continues retrying from the app.

**Wi-Fi repeatedly drops**

Check signal strength and the watchdog status:

```bash
nmcli device wifi list
systemctl status trainui-connectivity.timer
```

The Pi Zero W supports 2.4 GHz Wi-Fi, so confirm that the configured network offers a compatible 2.4 GHz signal. The watchdog can reconnect a saved network, but it cannot fix weak signal strength, router outages, or incorrect credentials.

**The display still powers itself off**

TrainUI disables Raspberry Pi OS blanking, DPMS, and system sleep and periodically wakes a disabled software output. If the screen's own hardware menu has an independent sleep timer, eco mode, or auto-off option, disable that setting with the monitor's physical controls as well.

## Project layout

```text
TrainUI/
├── installer/
│   ├── systemd/
│   │   ├── trainui-connectivity.service
│   │   └── trainui-connectivity.timer
│   ├── connectivity-watchdog.sh
│   └── install.sh       # Complete Raspberry Pi setup
├── requirements.txt     # Python packages
├── timertest.py         # TrainUI application
└── README.md
```

---

<div align="center">
Built for a glanceable, dedicated Raspberry Pi transit display.
</div>
