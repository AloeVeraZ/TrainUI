<div align="center">

# Train UI XL Trackside Installer

### One command for setup and updates

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/software/)
[![Project](https://img.shields.io/badge/Project-Train_UI_XL-2563eb?style=flat-square)](../)

</div>

---

## Before you start

- Use Raspberry Pi OS 32-bit with Desktop.
- Enable SSH and add 2.4 GHz Wi-Fi in Raspberry Pi Imager.
- Run this as your normal user, not with `sudo`.

## Run it

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/Train%20UI%20XL%20Trackside/installer/install.sh | bash
```

Choose a train and station, then answer `Y` or `N` for daily display sleep. Enter time as four digits in 24-hour `HHMM` format: `2300` is 11:00 PM, `0800` is 8:00 AM, and `2400` is midnight. Run the same command again to update TrainUI or change the station and schedule. Normal reruns skip unchanged system setup and do not reboot; they download only the small XL runtime files, not the CAD models or documentation photos.

Your selection stays in `~/.config/trainui-trackside/config.json`. If an old checkout is damaged or changed, the installer saves it as `~/TrainUI-Trackside.backup.*` before replacing it.

## Wi-Fi setup

Raspberry Pi Imager Wi-Fi stays preferred. After 30 seconds without Wi-Fi or Ethernet, join **TrainUI Trackside** with password **TRAINUI1**, then open `http://10.42.0.1`.

## Quick checks

```bash
tail -n 100 "$HOME/TrainUI-Trackside/Train UI XL/Train UI XL Trackside/trainui-trackside.log"
systemctl status trainui-trackside-wifi-setup.service
sudo journalctl -u trainui-trackside-wifi-setup.service --since today
```

Change or disable the daily schedule later with one command:

```bash
trainui-trackside-schedule
```

During scheduled sleep, only the display powers down. TrainUI and the logged-in desktop stay running, so the display wakes straight back into TrainUI without a login screen.

If the setup menu cannot use the terminal, reconnect with SSH and run the command directly. Hardware and assembly instructions are in the [Train UI XL README](../README.md).
