<div align="center">

# TrainUI Raspberry Pi Installer

### Interactive deployment, route selection, kiosk startup, and connectivity monitoring

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/software/)
[![Service](https://img.shields.io/badge/Services-systemd-6f42c1?style=flat-square)](#installer-files)
[![Configuration](https://img.shields.io/badge/Setup-Interactive-0a7f5a?style=flat-square)](#installation)
[![Parent](https://img.shields.io/badge/Project-TrainUI-0039a6?style=flat-square)](../)

The TrainUI installer turns Raspberry Pi OS with Desktop into an always-on NYC
departure board. It installs dependencies, asks which route and station to
display, creates the launcher, configures kiosk auto-start and display power
settings, installs the connectivity watchdog, validates the application, and
reboots the Pi.

<strong>Quick navigation:</strong><br>
[Requirements](#requirements) | [Installation](#installation) | [Installer Files](#installer-files) | [Updates](#updates-and-reconfiguration) | [Back to TrainUI](../)

</div>

---

## Requirements

- Raspberry Pi OS (32-bit) with Desktop on the original Raspberry Pi Zero W.
- SSH and internet access.
- A normal user account with `sudo` permission.
- An interactive terminal for the initial route and station selection.
- The HDMI display attached before the first TrainUI boot.

The Pi Zero W requires a compatible 2.4 GHz Wi-Fi network. The installer does
not replace the SSID or password already saved by Raspberry Pi OS. It preserves
that connection as preferred and gives saved networks 30 seconds to connect
before enabling the local Wi-Fi setup fallback.

## Installation

Run the installer as the normal Raspberry Pi user. Do not put `sudo` before the
command:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI/installer/install.sh | bash
```

Choose a train and then a station from the interactive menus. The selection is
saved outside the Git checkout at:

```text
~/.config/trainui/config.json
```

After validation, the installer reboots the Pi and TrainUI launches with the
graphical desktop.

If normal Wi-Fi and Ethernet are unavailable after 30 seconds, join the
protected **TrainUI** network with password **TRAINUI1**, open
`http://10.42.0.1`, and enter the replacement Wi-Fi name and password. The
fallback shuts down after a successful connection. If the details are wrong,
it returns so the form can be tried again.

## Installer Files

| File or folder | Purpose |
| --- | --- |
| `install.sh` | Complete package installation, source update, environment creation, auto-start setup, validation, and reboot |
| `configure.py` | Interactive route and station selector |
| `subway_catalog.json` | Generated catalog of supported subway/SIR routes and stations |
| `build_subway_catalog.py` | Rebuilds the catalog from official MTA static data |
| `wifi_setup.py` | Preserves preferred Wi-Fi, retries saved profiles, creates the fallback hotspot, and serves the credential page |
| `connectivity-watchdog.sh` | Legacy reconnect fallback for systems not managed by NetworkManager |
| `systemd/` | Automatic Wi-Fi setup service plus legacy watchdog units |

## Updates and Reconfiguration

Rerun the same installation command to update TrainUI or change the displayed
route and station. The installer shows the current selection; answer `n` to
choose a different one.

A clean `~/TrainUI` checkout updates in place. If the checkout contains local
changes, local commits, or damage, the installer preserves it in a timestamped
`~/TrainUI.backup.*` folder before deploying a fresh copy. The configuration in
`~/.config/trainui/config.json` remains intact.

The installer creates `~/TrainUI/run_trainui.sh` and writes runtime output to
`~/TrainUI/trainui.log`.

## Validation and Troubleshooting

View recent runtime output with:

```bash
tail -n 100 ~/TrainUI/trainui.log
```

Check the automatic Wi-Fi setup service with:

```bash
systemctl status trainui-wifi-setup.service
sudo journalctl -u trainui-wifi-setup.service --since today
```

The first installation must run in an interactive SSH or local terminal. If the
installer reports that no interactive terminal is available, reconnect normally
over SSH and run the command directly rather than through a detached job.

For display rotation, feed validation, and complete troubleshooting, see the
[main TrainUI guide](../README.md#troubleshooting).

---

<div align="center">

Installer documentation for **[TrainUI](../)**

</div>
