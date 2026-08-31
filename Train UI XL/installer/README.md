<div align="center">

# Train UI XL Installer

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
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/installer/install.sh | bash
```

Choose a train and station. The installer downloads Train UI, installs missing packages, sets up automatic startup, and reboots the Pi. Run the same command again to update or change the selection.

Your selection stays in `~/.config/trainui/config.json`. If an old checkout is damaged or changed, the installer saves it as `~/TrainUI.backup.*` before replacing it.

## Wi-Fi setup

Raspberry Pi Imager Wi-Fi stays preferred. After 30 seconds without Wi-Fi or Ethernet, join **TrainUI** with password **TRAINUI1**, then open `http://10.42.0.1`.

## Quick checks

```bash
tail -n 100 "$HOME/TrainUI/Train UI XL/trainui.log"
systemctl status trainui-wifi-setup.service
sudo journalctl -u trainui-wifi-setup.service --since today
```

If the setup menu cannot use the terminal, reconnect with SSH and run the command directly. Hardware and assembly instructions are in the [Train UI XL README](../README.md).
