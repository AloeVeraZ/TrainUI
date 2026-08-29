<div align="center">

# TrainUI XL

### An always-on New York City train departure board built around a Raspberry Pi Zero W

Live arrivals · Service alerts · NYC weather · System health

[![Raspberry Pi](https://img.shields.io/badge/Hardware-Pi_Zero_W-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/software/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![MTA](https://img.shields.io/badge/Data-MTA_Realtime-2563eb?style=flat-square)](https://www.mta.info/developers)

<strong>Quick navigation:</strong><br>
[Features](#what-trainui-supports) · [Hardware](#main-project-hardware) · [Install](#one-command-installation) · [Troubleshooting](#troubleshooting)

</div>

---

TrainUI XL turns a Raspberry Pi and HDMI screen into an always-on NYC departure board. During setup, you choose a train and then any station served by it. Nothing is preselected.

Once installed, TrainUI boots directly into a fullscreen kiosk, rotates the display 270°, and continually updates arrivals, service alerts, weather, time, and Raspberry Pi health information. The public MTA feeds used by the project do not require an API key.

## What TrainUI supports

The installer includes:

- Numbered trains: 1, 2, 3, 4, 5, 6, and 7.
- Lettered trains: A, B, C, D, E, F, G, J, L, M, N, Q, R, W, and Z.
- 42 St Shuttle, Franklin Av Shuttle, and Rockaway Park Shuttle.
- Staten Island Railway.
- Every route/station combination included in the bundled official MTA catalog.

Express identifiers such as `6X`, `7X`, and `FX` are handled automatically with the corresponding 6, 7, or F selection. LIRR and Metro-North are intentionally not included because TrainUI is focused on New York City subway and Staten Island Railway service.

The selected train and station control:

- Station name and borough/service subtitle.
- Official route badge colors.
- Both directional MTA stop IDs and direction labels.
- The correct MTA realtime arrival feed.
- Route- and station-specific service alerts.

Long station names and direction labels automatically shrink to fit. The departure cards keep the same dimensions regardless of the selected station.

## Main project hardware

The main build uses simple, inexpensive hardware.

| Component | Main project choice | Why it was selected |
|---|---|---|
| Computer | Original Raspberry Pi Zero W—not the newer Zero 2 W | It is small, inexpensive, Wi-Fi capable, and powerful enough for this focused display. |
| Operating system | Current, non-legacy Raspberry Pi OS (32-bit) with Desktop | This is the officially tested software target for the original Pi Zero W. |
| Display | [HAMTYSAN 10.1-inch HDMI monitor, Amazon ASIN B0FMF3RTPC](https://www.amazon.com/dp/B0FMF3RTPC) | It was inexpensive, driver-free, non-touch, and straightforward to integrate. |
| Enclosure | Custom three-part 3D-printed case | Holds the display, Pi, and cables together in one unit. |

### Display used by the main build

The linked HAMTYSAN display is a 10.1-inch, 1024×600 IPS LCD with a 16:9 aspect ratio and HDMI input. It is a normal non-touch monitor and does not require a special display driver. Those details matter to the design: TrainUI is intended to behave like a passive station sign, not a tablet or interactive touchscreen.

Other HDMI displays may work, but the main enclosure and future CAD files are being designed around this exact screen. A different panel may require changes to mounting holes, clearances, cable routing, screen rotation, or the printed enclosure.

### Raspberry Pi used by the main build

The reference build uses the original Raspberry Pi Zero W because it is cheap, small, and still fast enough for this display. The interface stays lightweight so it can run continuously on that board.

Newer Raspberry Pis may work too, but the supported build is the original Zero W with current Raspberry Pi OS (32-bit), not the Zero 2 W or a 64-bit-only setup.

## Enclosure and CAD

The physical enclosure is 3D printed in three separate parts. The pieces are designed to be assembled using heat-set threaded inserts and fasteners through matching holes instead of relying on glue or permanent snap fits. This makes the case easier to assemble, reopen, and revise while the hardware design is still being developed.

The [`CAD`](CAD/) folder is reserved for the printable and editable enclosure files. The CAD models are still being designed and will be added there when the three-part enclosure is finished. Until those files are published, the software can be installed and tested independently of the final printed case.

## Before installation

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install the current, non-legacy **Raspberry Pi OS (32-bit) with Desktop** image.

Configure these items in Raspberry Pi Imager:

- Connect the Pi to Wi-Fi or plan to use Ethernet with internet access.
- Enable SSH.
- Create any username and password. The user must have `sudo` access.
- Choose any hostname.
- Set whatever locale, keyboard, and timezone are appropriate for the installation.

The hostname, username, password, Wi-Fi name, IP address, locale, timezone, and storage brand do not need to match the reference build. SSH and internet access are the important requirements. The Pi Zero W only supports 2.4 GHz Wi-Fi, so its saved network must offer a compatible 2.4 GHz connection.

Attach the HDMI display before the first TrainUI boot. The main installation rotates the active output 270°.

## One-command installation

From another computer, connect to the Pi over SSH:

```bash
ssh YOUR_USERNAME@YOUR_PI_HOSTNAME.local
```

An IP address can be used instead when `.local` hostname discovery is unavailable:

```bash
ssh YOUR_USERNAME@192.168.1.123
```

Run the installer as the normal Raspberry Pi user:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI/installer/install.sh | bash
```

Do not place `sudo` before this command. The installer requests elevated access only for the system changes that require it.

The installer displays a numbered train menu followed by a numbered list of stations served by the chosen train. A first installation requires a real selection from an interactive SSH terminal; it does not silently choose a train or station.

After setup, the Pi reboots and launches TrainUI automatically.

## Changing the train or station later

SSH into the Pi and rerun the same installer command whenever the display needs to use another route or station:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI/installer/install.sh | bash
```

The installer shows the current selection and asks whether to keep it. Answer `n` to return to the train and station menus. The new selection is saved and used after the installer finishes and reboots.

Rerunning the installer also updates TrainUI and its Python environment. A clean checkout updates in place. If `~/TrainUI` contains local edits, local commits, or a damaged checkout, the installer preserves it as a timestamped `~/TrainUI.backup.*` folder before installing a clean copy.

The selected route and station are stored in:

```text
~/.config/trainui/config.json
```

That file lives outside the Git checkout, so a normal update or clean reinstall preserves the chosen configuration.

## What the installer configures

The installer:

1. Installs the required desktop, display, Python, font, and networking packages.
2. Clones or refreshes TrainUI in `~/TrainUI`.
3. Prompts for the train and station and saves that selection persistently.
4. Creates an isolated Python environment and installs the required libraries.
5. Validates the Python source and imports.
6. Creates `~/TrainUI/Train UI XL/run_trainui.sh` to rotate the display and launch TrainUI.
7. Enables automatic startup for current Wayland/labwc and older X11 Raspberry Pi OS desktops.
8. Applies network-agnostic Wi-Fi reliability settings without rewriting saved SSIDs or passwords.
9. Prevents desktop, console, and system sleep or blanking.
10. Enables graphical auto-login and reboots the Pi.

## Data and on-screen information

Arrival times come from the MTA's public GTFS-Realtime subway feeds and refresh every 30 seconds. Service alerts come from the MTA alert feed and are filtered for the selected route or station. The train/station catalog is generated from the official MTA static subway GTFS and Subway Stations datasets.

The weather panel is independent of the selected station and continues to show New York City conditions through Open-Meteo. The clock and date come from the Raspberry Pi. The system-health panel continues to show CPU temperature, RAM, storage, load, uptime, IP address, network connection, and transfer speeds.

No MTA or weather API key is required.

## Always-on reliability

TrainUI is configured as a dedicated kiosk:

- Wi-Fi power saving is disabled globally when NetworkManager is present and at the interface level when supported.
- A lightweight timer checks wireless connectivity every 30 seconds.
- The watchdog discovers interfaces automatically and reuses the connection already saved by Raspberry Pi OS.
- The installer never embeds or rewrites an SSID or Wi-Fi password.
- Ethernet-only systems are left alone.
- Desktop blanking, console blanking, X11 DPMS, suspend, and hibernation are disabled.
- The launcher keeps the active Wayland or X11 output awake while TrainUI runs.
- TrainUI keeps retrying when MTA, weather, or internet service is temporarily unavailable.

No software can compensate for incorrect credentials, a router outage, weak signal, lost power, or an incompatible Wi-Fi band.

## Useful commands

View the runtime log:

```bash
tail -f "$HOME/TrainUI/Train UI XL/trainui.log"
```

Restart the interface without rebooting:

```bash
pkill -f timertest.py || true
"$HOME/TrainUI/Train UI XL/run_trainui.sh" &
```

Check the connectivity timer:

```bash
systemctl status trainui-connectivity.timer
sudo journalctl -u trainui-connectivity.service --since today
```

Run the route/station selector directly:

```bash
python3 "$HOME/TrainUI/Train UI XL/installer/configure.py" \
    --config "$HOME/.config/trainui/config.json"
sudo reboot
```

Rerunning the complete `curl` installer is the recommended method because it changes the selection and updates the project in one operation.

## Troubleshooting

### SSH does not connect

Confirm that SSH was enabled in Raspberry Pi Imager and that the Pi is connected to the network. Try the Pi's IP address if its `.local` hostname is unavailable.

### TrainUI does not appear after reboot

Confirm that the Pi reaches the graphical desktop, then inspect:

```bash
tail -n 100 "$HOME/TrainUI/Train UI XL/trainui.log"
```

### The installer says no interactive terminal is available

The first installation must be run directly inside an interactive SSH session so the train and station menus can accept input. Do not run the command from a detached job, unattended provisioning service, or another script that removes the terminal.

### Arrivals or alerts are unavailable

Check internet access and the runtime log. Some routes only operate during certain hours, and some stations may only receive a selected service during a limited service pattern. TrainUI continues retrying automatically.

### Wi-Fi repeatedly disconnects

Check the signal and saved Raspberry Pi OS connection:

```bash
nmcli device wifi list
systemctl status trainui-connectivity.timer
```

For the original Pi Zero W, verify that the network offers 2.4 GHz Wi-Fi.

### The screen is rotated incorrectly

The main enclosure expects 270° rotation. The generated launcher contains `wlr-randr --transform 270` for Wayland and `xrandr --rotate left` for X11. A differently mounted display may require changing those values in `~/TrainUI/Train UI XL/run_trainui.sh`; rerunning the installer regenerates that file.

### The display still turns itself off

TrainUI disables Raspberry Pi OS software blanking and sleep. If the monitor has its own hardware sleep timer, eco mode, or auto-off setting, disable that through the monitor's controls.

## Development and validation

The repository includes automated checks for every catalog entry and a live-feed validator covering all eight MTA subway/SIR realtime endpoints.

```bash
python3 -m unittest discover -s tests -v
python3 tests/validate_live_feeds.py
python3 timertest.py --smoke-test
```

The generated route catalog can be refreshed from current official MTA data with:

```bash
python3 installer/build_subway_catalog.py
```

## Project layout

```text
TrainUI/
├── CAD/                           # Reserved for the three-part enclosure CAD
├── installer/
│   ├── systemd/
│   │   ├── trainui-connectivity.service
│   │   └── trainui-connectivity.timer
│   ├── build_subway_catalog.py    # Rebuild catalog from official MTA data
│   ├── configure.py               # Interactive train/station selector
│   ├── connectivity-watchdog.sh
│   ├── install.sh                 # Complete Raspberry Pi setup
│   └── subway_catalog.json        # Generated subway/SIR route and station catalog
├── tests/
│   ├── test_catalog.py
│   └── validate_live_feeds.py
├── requirements.txt
├── timertest.py
└── README.md
```

---

<div align="center">
Built as a low-cost, glanceable NYC transit display for the original Raspberry Pi Zero W.
</div>
