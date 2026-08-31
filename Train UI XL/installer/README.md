<div align="center">

# Train UI XL Installer

### One command for setup, updates, and train selection

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/software/)
[![Setup](https://img.shields.io/badge/Setup-Interactive-0a7f5a?style=flat-square)](#run-the-installer)
[![Project](https://img.shields.io/badge/Project-Train_UI_XL-2563eb?style=flat-square)](../)

<strong>Quick navigation:</strong><br>
[Run It](#run-the-installer) | [What It Does](#what-it-does) | [Files](#installer-files) | [Troubleshooting](#troubleshooting)

</div>

---

## Overview

I made this installer so the Raspberry Pi setup would not be a long list of commands. It installs Train UI XL, opens the train and station menu, sets up automatic startup, and reboots the Pi when it is done.

Run the same command again whenever you want to update Train UI or change the train and station.
On a rerun, installed Raspberry Pi packages and an unchanged Python environment are skipped instead of downloaded again.

## Before you start

- Use Raspberry Pi OS (32-bit) with Desktop.
- Enable SSH in Raspberry Pi Imager.
- Connect the Pi to the internet.
- Run the command as your normal user, not with `sudo`.
- Use a normal SSH or local terminal so the setup menu can accept input.

The original Raspberry Pi Zero W needs a 2.4 GHz Wi-Fi network.

## Run the installer

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/installer/install.sh | bash
```

Choose a train and station when the menus open. The choice is saved in:

```text
~/.config/trainui/config.json
```

## What it does

- Installs the Raspberry Pi, desktop, networking, and Python packages.
- Downloads or updates the repository in `~/TrainUI`.
- Saves the selected train and station.
- Builds the Python environment for Train UI XL.
- Creates the rotated fullscreen launcher.
- Starts Train UI automatically with Wayland or X11.
- Adds a Wi-Fi connectivity watchdog.
- Disables Raspberry Pi OS screen blanking and sleep.
- Checks the Python code before rebooting.

If the Git checkout has local changes or damage, the installer saves it as `~/TrainUI.backup.*` before downloading a clean copy. The train and station configuration is stored outside the repository and is not removed.

## Installer files

| File | What it is for |
| --- | --- |
| `install.sh` | Installs, updates, configures, validates, and reboots |
| `configure.py` | Train and station menu |
| `subway_catalog.json` | Subway and SIR route/station catalog |
| `build_subway_catalog.py` | Rebuilds the catalog from MTA data |
| `connectivity-watchdog.sh` | Checks and restores the saved network connection |
| `systemd/` | Timer and service files for the watchdog |

## Troubleshooting

View the Train UI log:

```bash
tail -n 100 "$HOME/TrainUI/Train UI XL/trainui.log"
```

Check the Wi-Fi watchdog:

```bash
systemctl status trainui-connectivity.timer
sudo journalctl -u trainui-connectivity.service --since today
```

If the installer says there is no interactive terminal, reconnect with SSH and run the command directly in that window.

The full hardware setup is in the [Train UI XL README](../README.md).
